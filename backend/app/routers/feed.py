"""Feed, ítems, interacciones, guardados, historial, búsqueda y enlaces añadidos a mano."""
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..agents import analyst, explorer, preferences, recommender
from ..cache import get_cache, get_json, set_json
from ..db import get_session
from ..models import Creator, Item, ItemState, utcnow
from ..schemas import AddLinkIn, EventIn, FeedOut, ItemOut, NoteIn, item_out
from ..services import creator_names, get_settings_map, states_for, usage_status
from ..text import normalize

router = APIRouter(prefix="/api", tags=["feed"])
FEED_TTL = 3600
BATCH = 40


async def _hydrate(session: AsyncSession, ids: list[int], scores: dict[int, dict] | None = None) -> list[ItemOut]:
    if not ids:
        return []
    items = {i.id: i for i in (await session.execute(select(Item).where(Item.id.in_(ids)))).scalars()}
    states = await states_for(session, ids)
    names = await creator_names(session)

    class _S:  # adaptador ligero para item_out
        def __init__(self, d):
            self.total, self.parts, self.reasons = d["total"], d["parts"], d["reasons"]

    out = []
    for i in ids:
        it = items.get(i)
        if not it:
            continue
        sc = _S(scores[i]) if scores and i in scores else None
        out.append(item_out(it, states.get(i), names.get(it.creator_id) if it.creator_id else None, sc))
    return out


@router.get("/feed", response_model=FeedOut)
async def get_feed(
    session_id: str | None = Query(None, alias="session"),
    offset: int = Query(0, ge=0),
    limit: int = Query(8, ge=1, le=30),
    format: str = Query("all", pattern="^(all|short|long|article)$"),
    category: str | None = None,
    db: AsyncSession = Depends(get_session),
):
    """Feed paginado. La primera página calcula un lote y lo guarda en caché;
    las siguientes solo lo leen, así el scroll no recalcula nada."""
    cmd = await recommender.active_command(db)
    cmd_dict = dict(cmd.parsed, id=cmd.id) if cmd else None
    sid = session_id or secrets.token_urlsafe(8)
    key = f"feed:{sid}:{format}:{category or ''}:{cmd.id if cmd else 0}"
    data = await get_json(key) or {"ids": [], "scores": {}}
    ids: list[int] = data["ids"]
    if offset + limit > len(ids):
        aff = await preferences.affinity_map(db)
        fresh = await recommender.build_feed(db, aff, BATCH, format, category, set(ids), cmd_dict)
        for s in fresh:
            ids.append(s.item.id)
            data["scores"][str(s.item.id)] = {"total": s.total, "parts": s.parts, "reasons": s.reasons}
        data["ids"] = ids
        data["exhausted"] = len(fresh) == 0
        await set_json(key, data, FEED_TTL)
    page = ids[offset : offset + limit]
    scores = {int(k): v for k, v in data["scores"].items()}
    settings = await get_settings_map(db)
    return FeedOut(
        session=sid, offset=offset, items=await _hydrate(db, page, scores),
        has_more=offset + limit < len(ids) or not data.get("exhausted", False),
        command=cmd_dict, usage=await usage_status(db, settings),
    )


@router.get("/items/{item_id}", response_model=ItemOut)
async def get_item(item_id: int, db: AsyncSession = Depends(get_session)):
    out = await _hydrate(db, [item_id])
    if not out:
        raise HTTPException(404, "No existe")
    return out[0]


@router.post("/items/{item_id}/events", response_model=ItemOut)
async def post_event(item_id: int, ev: EventIn, db: AsyncSession = Depends(get_session)):
    it = await db.get(Item, item_id)
    if not it:
        raise HTTPException(404, "No existe")
    await preferences.record(db, it, ev.kind, ev.value)
    if ev.kind == "hide":
        await get_cache().delete_prefix("feed:")
    await db.commit()
    return (await _hydrate(db, [item_id]))[0]


@router.post("/items/{item_id}/broken")
async def report_broken(item_id: int, db: AsyncSession = Depends(get_session)):
    """La app avisa cuando un reproductor no puede cargar el vídeo (borrado, privado...)."""
    it = await db.get(Item, item_id)
    if not it:
        raise HTTPException(404, "No existe")
    it.status = "broken"
    await db.commit()
    return {"ok": True}


@router.put("/items/{item_id}/note", response_model=ItemOut)
async def put_note(item_id: int, body: NoteIn, db: AsyncSession = Depends(get_session)):
    it = await db.get(Item, item_id)
    if not it:
        raise HTTPException(404, "No existe")
    st = await preferences.get_state(db, item_id)
    had_note = bool(st.note)
    st.note = body.note.strip()
    if body.collection is not None:
        st.collection = body.collection.strip()
        if st.collection and not st.saved:
            st.saved, st.saved_at = True, utcnow()
    st.updated_at = utcnow()
    if st.note and not had_note:
        await preferences.record(db, it, "note")
    await db.commit()
    return (await _hydrate(db, [item_id]))[0]


@router.get("/saved", response_model=list[ItemOut])
async def saved(collection: str | None = None, limit: int = Query(100, le=500), offset: int = 0,
                db: AsyncSession = Depends(get_session)):
    q = select(ItemState.item_id).where(ItemState.saved)
    if collection:
        q = q.where(ItemState.collection == collection)
    ids = (await db.execute(q.order_by(ItemState.saved_at.desc()).offset(offset).limit(limit))).scalars().all()
    return await _hydrate(db, list(ids))


@router.get("/collections")
async def collections(db: AsyncSession = Depends(get_session)):
    rows = (await db.execute(
        select(ItemState.collection, func.count()).where(ItemState.saved).group_by(ItemState.collection)
    )).all()
    return [{"name": n or "Ver después", "key": n, "count": c} for n, c in rows]


@router.get("/liked", response_model=list[ItemOut])
async def liked(limit: int = Query(100, le=500), offset: int = 0, db: AsyncSession = Depends(get_session)):
    ids = (await db.execute(
        select(ItemState.item_id).where(ItemState.liked).order_by(ItemState.updated_at.desc()).offset(offset).limit(limit)
    )).scalars().all()
    return await _hydrate(db, list(ids))


@router.get("/history", response_model=list[ItemOut])
async def history(limit: int = Query(60, le=300), offset: int = 0, db: AsyncSession = Depends(get_session)):
    ids = (await db.execute(
        select(ItemState.item_id).where(ItemState.seen_count > 0)
        .order_by(ItemState.last_seen_at.desc()).offset(offset).limit(limit)
    )).scalars().all()
    return await _hydrate(db, list(ids))


@router.delete("/history")
async def clear_history(db: AsyncSession = Depends(get_session)):
    """Vuelve a permitir en el feed lo ya visto (no borra likes ni guardados)."""
    rows = (await db.execute(select(ItemState).where(ItemState.seen_count > 0))).scalars().all()
    for st in rows:
        st.seen_count, st.last_seen_at = 0, None
    await db.commit()
    await get_cache().delete_prefix("feed:")
    return {"cleared": len(rows)}


@router.get("/notes", response_model=list[ItemOut])
async def notes(db: AsyncSession = Depends(get_session)):
    ids = (await db.execute(
        select(ItemState.item_id).where(ItemState.note != "").order_by(ItemState.updated_at.desc()).limit(300)
    )).scalars().all()
    return await _hydrate(db, list(ids))


@router.get("/search", response_model=list[ItemOut])
async def search(q: str = Query(min_length=2, max_length=120), category: str | None = None,
                 format: str = Query("all", pattern="^(all|short|long|article)$"),
                 limit: int = Query(40, le=100), db: AsyncSession = Depends(get_session)):
    """Búsqueda en todo lo descubierto: título, autor, resumen y etiquetas."""
    terms = [t for t in normalize(q).split() if len(t) > 1][:6]
    if not terms:
        return []
    query = select(Item).where(Item.status == "active")
    for t in terms:
        like = f"%{t}%"
        query = query.where(or_(func.lower(Item.title).like(like), func.lower(Item.author_name).like(like),
                                func.lower(Item.summary).like(like), func.lower(Item.description).like(like)))
    if category:
        query = query.where(Item.category_slug == category)
    if format != "all":
        query = query.where(Item.format == format)
    items = (await db.execute(query.limit(300))).scalars().all()

    def rank(it: Item) -> float:
        t = normalize(it.title)
        return sum(2 for x in terms if x in t) + it.quality

    items = sorted(items, key=rank, reverse=True)[:limit]
    return await _hydrate(db, [i.id for i in items])


@router.post("/items", response_model=ItemOut, status_code=201)
async def add_link(body: AddLinkIn, db: AsyncSession = Depends(get_session)):
    """Añade un vídeo de TikTok, Instagram, YouTube, Vimeo o un artículo pegando su enlace."""
    info = explorer.parse_link(body.url)
    if not info or info["kind"] != "item":
        raise HTTPException(422, "No reconozco ese enlace como un vídeo o artículo")
    async with explorer.http_client() as client:
        info = await explorer.resolve_link(client, info)
    if not info.get("external_id"):
        raise HTTPException(422, "No pude resolver ese enlace corto; prueba con el enlace completo")
    existing = (await db.execute(select(Item).where(Item.platform == info["platform"],
                                                    Item.external_id == info["external_id"]))).scalars().first()
    if existing:
        return (await _hydrate(db, [existing.id]))[0]
    creator = None
    if info["platform"] == "youtube" and info.get("author_url"):
        m = info["author_url"].rstrip("/").rsplit("/", 1)[-1]
        creator = (await db.execute(select(Creator).where(Creator.handle == m.lstrip("@")))).scalars().first()
    title = info.get("title") or {"tiktok": "Vídeo de TikTok", "instagram": "Reel de Instagram"}.get(info["platform"], body.url)
    it = Item(platform=info["platform"], external_id=info["external_id"], url=info["url"],
              embed_url=info.get("embed_url", ""), title=title[:500], description=info.get("description", "")[:2000],
              author_name=info.get("author_name", "")[:200], thumbnail_url=info.get("thumbnail_url", "")[:1000],
              format=info.get("format", "long"), origin="user", category_slug=body.category,
              creator_id=creator.id if creator else None)
    analyst.apply_heuristic(it, body.category, 0.75)
    it.quality = max(it.quality, 0.65)  # lo eliges tú: confianza alta
    db.add(it)
    await db.flush()
    await preferences.record(db, it, "save")
    await db.commit()
    await get_cache().delete_prefix("feed:")
    return (await _hydrate(db, [it.id]))[0]
