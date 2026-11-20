"""Ajustes, tiempo de uso, estadísticas, destacados, comandos, agentes y repaso."""
import random
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..agents import commands as cmd_agent
from ..agents import explorer, llm, preferences
from ..cache import get_cache
from ..config import get_settings
from ..db import get_session
from ..models import (AgentRun, Category, Creator, DailyDigest, FeedCommand, Highlight, Interaction, Item,
                      ItemState, Source, UsageDay)
from ..schemas import CommandIn, ExtendIn, HeartbeatIn, HighlightsOut, RunAgentIn, item_out
from ..seed import DEFAULT_SETTINGS
from ..services import (add_usage, creator_names, get_settings_map, local_today, run_agent, set_setting,
                        states_for, usage_status)

router = APIRouter(prefix="/api", tags=["me"])


# ------------------------------------------------------------- ajustes -----

@router.get("/settings")
async def read_settings(db: AsyncSession = Depends(get_session)):
    return await get_settings_map(db)


@router.patch("/settings")
async def patch_settings(body: dict, db: AsyncSession = Depends(get_session)):
    unknown = [k for k in body if k not in DEFAULT_SETTINGS]
    if unknown:
        raise HTTPException(422, f"Ajustes desconocidos: {', '.join(unknown)}")
    for k, v in body.items():
        default = DEFAULT_SETTINGS[k]
        if isinstance(default, bool) and not isinstance(v, bool):
            raise HTTPException(422, f"{k} debe ser verdadero/falso")
        if isinstance(default, int) and not isinstance(default, bool):
            if not isinstance(v, (int, float)) or v < 0 or v > 1440:
                raise HTTPException(422, f"{k} debe ser un número de 0 a 1440")
            v = int(v)
        await set_setting(db, k, v)
    await db.commit()
    return await get_settings_map(db)


# ---------------------------------------------------------- tiempo de uso --

@router.post("/usage/heartbeat")
async def heartbeat(body: HeartbeatIn, db: AsyncSession = Depends(get_session)):
    await add_usage(db, body.seconds, body.category, body.items_viewed)
    await db.commit()
    return await usage_status(db)


@router.get("/usage/today")
async def usage_today(db: AsyncSession = Depends(get_session)):
    return await usage_status(db)


@router.post("/usage/extend")
async def usage_extend(body: ExtendIn, db: AsyncSession = Depends(get_session)):
    """«Dame 10 minutos más». Queda registrado para que lo veas en tus estadísticas."""
    today = local_today()
    day = await db.get(UsageDay, today)
    if day is None:
        day = UsageDay(day=today, seconds=0.0, items_viewed=0, by_category={}, extra_minutes=0)
        db.add(day)
    day.extra_minutes = (day.extra_minutes or 0) + body.minutes
    await db.commit()
    return await usage_status(db)


@router.get("/stats")
async def stats(days: int = Query(7, ge=1, le=90), db: AsyncSession = Depends(get_session)):
    today = local_today()
    start = today - timedelta(days=days - 1)
    rows = {u.day: u for u in (await db.execute(select(UsageDay).where(UsageDay.day >= start))).scalars()}
    series = []
    by_cat: dict[str, float] = {}
    for n in range(days):
        d = start + timedelta(days=n)
        u = rows.get(d)
        series.append({"day": d.isoformat(), "minutes": round((u.seconds if u else 0) / 60, 1),
                       "items": u.items_viewed if u else 0, "extra_minutes": u.extra_minutes if u else 0})
        for k, v in ((u.by_category or {}) if u else {}).items():
            by_cat[k] = by_cat.get(k, 0) + v
    # Racha: días seguidos (hasta hoy o ayer) con al menos 5 minutos de aprendizaje.
    all_days = {u.day: u.seconds for u in (await db.execute(select(UsageDay))).scalars()}
    streak, d = 0, today if all_days.get(today, 0) >= 300 else today - timedelta(days=1)
    while all_days.get(d, 0) >= 300:
        streak += 1
        d -= timedelta(days=1)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    counts = dict((await db.execute(
        select(Interaction.kind, func.count()).where(Interaction.created_at >= since).group_by(Interaction.kind)
    )).all())
    cats = {c.slug: c for c in (await db.execute(select(Category))).scalars()}
    total_min = sum(s["minutes"] for s in series)
    return {
        "days": series,
        "total_minutes": round(total_min, 1),
        "avg_minutes": round(total_min / days, 1),
        "by_category": [
            {"slug": k, "name": cats[k].name if k in cats else k, "emoji": cats[k].emoji if k in cats else "",
             "color": cats[k].color if k in cats else "#888", "minutes": round(v / 60, 1)}
            for k, v in sorted(by_cat.items(), key=lambda kv: -kv[1])
        ],
        "streak_days": streak,
        "events": counts,
        "notes": (await db.execute(select(func.count()).select_from(ItemState).where(ItemState.note != ""))).scalar(),
        "saved": (await db.execute(select(func.count()).select_from(ItemState).where(ItemState.saved))).scalar(),
    }


# ------------------------------------------------------------ destacados ---

@router.get("/highlights", response_model=HighlightsOut)
async def highlights(day: date | None = None, db: AsyncSession = Depends(get_session)):
    day = day or local_today()
    hl = (await db.execute(select(Highlight).where(Highlight.day == day).order_by(Highlight.rank))).scalars().all()
    if not hl and day == local_today():
        await run_agent("curator")
        hl = (await db.execute(select(Highlight).where(Highlight.day == day).order_by(Highlight.rank))).scalars().all()
    digest = await db.get(DailyDigest, day)
    ids = [h.item_id for h in hl]
    states = await states_for(db, ids)
    names = await creator_names(db)

    class _S:
        def __init__(self, reason):
            self.total, self.parts, self.reasons = 0.0, {}, [reason]

    items = [item_out(h.item, states.get(h.item_id), names.get(h.item.creator_id), _S(h.reason)) for h in hl]
    return HighlightsOut(day=day, headline=digest.headline if digest else "", summary=digest.summary if digest else "",
                         generator=digest.generator if digest else "", items=items)


@router.post("/highlights/rebuild")
async def rebuild_highlights():
    return await run_agent("curator")


# -------------------------------------------------------------- comandos ---

@router.post("/commands")
async def create_command(body: CommandIn, db: AsyncSession = Depends(get_session)):
    parsed, parser = await cmd_agent.parse_command(body.text)
    for c in (await db.execute(select(FeedCommand).where(FeedCommand.active))).scalars():
        c.active = False
    found = 0
    if body.search_online and get_settings().youtube_api_enabled:
        async with explorer.http_client() as client:
            cat = parsed["categories"][0] if parsed["categories"] else None
            sub = parsed["subtopics"][0] if parsed["subtopics"] else None
            found = await explorer.search_and_ingest(client, db, parsed["search_query"], cat, sub,
                                                     days=parsed.get("max_age_days") or 365)
        if found:
            from ..agents import analyst
            await db.flush()
            await analyst.run(db, claude_max=found)
    now = datetime.now(timezone.utc)
    cmd = FeedCommand(text=body.text, parsed=parsed, parser=parser, active=True,
                      expires_at=now + timedelta(minutes=parsed.get("duration_minutes") or 90))
    db.add(cmd)
    await db.commit()
    await get_cache().delete_prefix("feed:")
    return {"id": cmd.id, "text": cmd.text, "parsed": parsed, "parser": parser, "found_online": found,
            "expires_at": cmd.expires_at}


@router.get("/commands")
async def list_commands(db: AsyncSession = Depends(get_session)):
    rows = (await db.execute(select(FeedCommand).order_by(FeedCommand.created_at.desc()).limit(30))).scalars()
    return [{"id": c.id, "text": c.text, "parsed": c.parsed, "parser": c.parser, "active": c.active,
             "created_at": c.created_at, "expires_at": c.expires_at} for c in rows]


@router.delete("/commands/active")
async def clear_command(db: AsyncSession = Depends(get_session)):
    for c in (await db.execute(select(FeedCommand).where(FeedCommand.active))).scalars():
        c.active = False
    await db.commit()
    await get_cache().delete_prefix("feed:")
    return {"ok": True}


@router.post("/commands/{command_id}/reactivate")
async def reactivate_command(command_id: int, db: AsyncSession = Depends(get_session)):
    cmd = await db.get(FeedCommand, command_id)
    if not cmd:
        raise HTTPException(404, "No existe")
    for c in (await db.execute(select(FeedCommand).where(FeedCommand.active))).scalars():
        c.active = False
    cmd.active = True
    cmd.expires_at = datetime.now(timezone.utc) + timedelta(minutes=(cmd.parsed or {}).get("duration_minutes") or 90)
    await db.commit()
    await get_cache().delete_prefix("feed:")
    return {"ok": True}


# ---------------------------------------------------------------- repaso ---

@router.get("/review")
async def review(n: int = Query(5, ge=1, le=20), db: AsyncSession = Depends(get_session)):
    """Repaso: tarjetas con las ideas clave de lo que guardaste o anotaste."""
    rows = (await db.execute(
        select(ItemState).where((ItemState.saved) | (ItemState.note != "") | (ItemState.liked))
        .order_by(ItemState.updated_at.desc()).limit(200)
    )).scalars().all()
    rows = [r for r in rows if r.item and (r.item.key_points or r.note or r.item.summary)]
    random.shuffle(rows)
    out = []
    for st in rows[:n]:
        it = st.item
        out.append({"item_id": it.id, "title": it.title, "category": it.category_slug,
                    "points": list(it.key_points or []) or ([it.summary] if it.summary else []),
                    "note": st.note, "thumbnail_url": it.thumbnail_url})
    return out


# --------------------------------------------------------------- agentes ---

@router.post("/agents/run")
async def agents_run(body: RunAgentIn, background: BackgroundTasks):
    names = ["explorer", "curator"] if body.agent == "all" else [body.agent]

    async def go():
        for n in names:
            await run_agent(n, force=body.force)

    background.add_task(go)
    return {"started": names}


@router.get("/agents/runs")
async def agents_runs(db: AsyncSession = Depends(get_session)):
    rows = (await db.execute(select(AgentRun).order_by(AgentRun.started_at.desc()).limit(30))).scalars()
    return [{"id": r.id, "agent": r.agent, "started_at": r.started_at, "finished_at": r.finished_at, "ok": r.ok,
             "stats": r.stats, "error": r.error} for r in rows]


@router.get("/status")
async def status(db: AsyncSession = Depends(get_session)):
    s = get_settings()
    count = lambda m, *w: select(func.count()).select_from(m).where(*w)  # noqa: E731
    items = dict((await db.execute(select(Item.format, func.count()).where(Item.status == "active").group_by(Item.format))).all())
    return {
        "version": "1.0.0",
        "claude": {"enabled": llm.available(), "model": s.claude_model if llm.available() else None},
        "youtube_api": s.youtube_api_enabled,
        "redis": bool(s.redis_url),
        "database": "sqlite" if s.is_sqlite else "postgres",
        "items": items,
        "items_total": sum(items.values()),
        "pending_analysis": (await db.execute(count(Item, Item.analysis == "pending"))).scalar(),
        "creators": dict((await db.execute(select(Creator.status, func.count()).group_by(Creator.status))).all()),
        "sources": (await db.execute(count(Source, Source.enabled))).scalar(),
        "auth": bool(s.app_token),
    }
