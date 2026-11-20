"""Categorías, subtemas, creadores (incluidas las sugerencias de la IA) y preferencias aprendidas."""
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..agents import explorer, preferences
from ..cache import get_cache
from ..db import get_session
from ..models import Category, Creator, Item, Subtopic
from ..schemas import CategoryPatch, CreatorIn, CreatorPatch, SubtopicPatch

router = APIRouter(prefix="/api", tags=["library"])


def _cat_out(c: Category, counts: dict[str, int]) -> dict:
    return {
        "slug": c.slug, "name": c.name, "emoji": c.emoji, "color": c.color, "description": c.description,
        "weight": c.weight, "enabled": c.enabled, "items": counts.get(c.slug, 0),
        "subtopics": [{"slug": s.slug, "name": s.name, "enabled": s.enabled} for s in c.subtopics],
    }


@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_session)):
    counts = dict((await db.execute(
        select(Item.category_slug, func.count()).where(Item.status == "active").group_by(Item.category_slug)
    )).all())
    cats = (await db.execute(select(Category).order_by(Category.position))).scalars().all()
    return [_cat_out(c, counts) for c in cats]


@router.patch("/categories/{slug}")
async def patch_category(slug: str, body: CategoryPatch, db: AsyncSession = Depends(get_session)):
    c = await db.get(Category, slug)
    if not c:
        raise HTTPException(404, "Categoría desconocida")
    if body.weight is not None:
        c.weight = body.weight
    if body.enabled is not None:
        c.enabled = body.enabled
    await db.commit()
    await get_cache().delete_prefix("feed:")
    return _cat_out(c, {})


@router.patch("/subtopics/{slug}")
async def patch_subtopic(slug: str, body: SubtopicPatch, db: AsyncSession = Depends(get_session)):
    s = await db.get(Subtopic, slug)
    if not s:
        raise HTTPException(404, "Subtema desconocido")
    s.enabled = body.enabled
    await db.commit()
    return {"slug": s.slug, "enabled": s.enabled}


def _creator_out(c: Creator, counts: dict[int, int]) -> dict:
    return {
        "id": c.id, "platform": c.platform, "external_id": c.external_id, "name": c.name, "handle": c.handle,
        "url": c.url, "avatar_url": c.avatar_url, "category": c.category_slug, "language": c.language,
        "status": c.status, "origin": c.origin, "reason": c.reason, "credibility": c.credibility,
        "items": counts.get(c.id, 0), "last_fetched_at": c.last_fetched_at,
    }


@router.get("/creators")
async def list_creators(status: str | None = None, db: AsyncSession = Depends(get_session)):
    q = select(Creator).order_by(Creator.name)
    if status:
        q = q.where(Creator.status == status)
    counts = dict((await db.execute(
        select(Item.creator_id, func.count()).where(Item.creator_id.is_not(None)).group_by(Item.creator_id)
    )).all())
    return [_creator_out(c, counts) for c in (await db.execute(q)).scalars()]


_CHANNEL_RE = re.compile(r"(UC[A-Za-z0-9_-]{22})")


@router.post("/creators", status_code=201)
async def add_creator(body: CreatorIn, db: AsyncSession = Depends(get_session)):
    """Sigue a un creador. Para YouTube basta la URL del canal o su channel id.
    Con un @handle se intenta resolver el id leyendo la página pública del canal."""
    raw = body.url.strip()
    m = _CHANNEL_RE.search(raw)
    info = {"platform": "youtube", "external_id": m.group(1), "url": f"https://www.youtube.com/channel/{m.group(1)}"} if m else None
    if not info:
        parsed = explorer.parse_link(raw if "/" in raw or "." in raw else f"https://www.youtube.com/@{raw.lstrip('@')}")
        if not parsed or parsed.get("kind") != "creator":
            raise HTTPException(422, "No reconozco ese creador. Pega la URL del canal o su @usuario")
        info = parsed
        if info["platform"] == "youtube" and not info.get("external_id"):
            async with explorer.http_client() as client:
                try:
                    r = await client.get(f"https://www.youtube.com/@{info['handle']}")
                    mm = re.search(r'"(?:channelId|externalId)":"(UC[A-Za-z0-9_-]{22})"', r.text)
                    if mm:
                        info["external_id"] = mm.group(1)
                except Exception:
                    pass
            if not info.get("external_id"):
                raise HTTPException(422, "No pude encontrar el canal. Prueba con la URL /channel/UC...")
        if info["platform"] in ("tiktok", "instagram"):
            info["external_id"] = info["handle"]
    existing = (await db.execute(select(Creator).where(Creator.platform == info["platform"],
                                                       Creator.external_id == info["external_id"]))).scalars().first()
    if existing:
        existing.status = "approved"
        await db.commit()
        return _creator_out(existing, {})
    c = Creator(platform=info["platform"], external_id=info["external_id"], name=info.get("handle") or info["external_id"],
                handle=info.get("handle", ""), url=info.get("url", ""), category_slug=body.category,
                status="approved", origin="user", credibility=0.75)
    db.add(c)
    await db.flush()
    if c.platform == "youtube":
        async with explorer.http_client() as client:
            rows = await explorer.fetch_creator(client, c)
        if rows:
            c.name = rows[0].get("author_name") or c.name
            await explorer.upsert_items(db, rows, creator_id=c.id, language=c.language, credibility=c.credibility, origin="rss")
            from ..agents import analyst
            await db.flush()
            await analyst.run(db, claude_max=15)
    await db.commit()
    await get_cache().delete_prefix("feed:")
    return _creator_out(c, {})


@router.patch("/creators/{creator_id}")
async def patch_creator(creator_id: int, body: CreatorPatch, db: AsyncSession = Depends(get_session)):
    c = await db.get(Creator, creator_id)
    if not c:
        raise HTTPException(404, "Creador desconocido")
    if body.status:
        c.status = body.status
    if body.category is not None:
        c.category_slug = body.category or None
    if body.credibility is not None:
        c.credibility = body.credibility
    await db.commit()
    await get_cache().delete_prefix("feed:")
    return _creator_out(c, {})


@router.get("/preferences")
async def get_preferences(db: AsyncSession = Depends(get_session)):
    aff = await preferences.affinity_map(db)
    labels: dict[str, str] = {}
    for c in (await db.execute(select(Category))).scalars():
        labels[f"cat:{c.slug}"] = f"{c.emoji} {c.name}"
        for s in c.subtopics:
            labels[f"sub:{s.slug}"] = s.name
    for i, n in (await db.execute(select(Creator.id, Creator.name))).all():
        labels[f"creator:{i}"] = n
    return preferences.describe(aff, labels)


@router.delete("/preferences")
async def reset_preferences(db: AsyncSession = Depends(get_session)):
    await preferences.reset(db)
    await db.commit()
    await get_cache().delete_prefix("feed:")
    return {"ok": True}


@router.delete("/preferences/{key:path}")
async def forget_preference(key: str, db: AsyncSession = Depends(get_session)):
    from ..models import Affinity

    a = await db.get(Affinity, key)
    if a:
        await db.delete(a)
        await db.commit()
        await get_cache().delete_prefix("feed:")
    return {"ok": True}
