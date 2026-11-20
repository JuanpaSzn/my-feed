"""Lógica compartida entre rutas y planificador."""
import logging
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .agents import analyst, curator, explorer, preferences
from .cache import get_cache
from .config import get_settings
from .db import SessionLocal
from .models import AgentRun, AppSetting, Creator, ItemState, UsageDay
from .seed import DEFAULT_SETTINGS

log = logging.getLogger("myfeed.services")


def local_today() -> date:
    try:
        return datetime.now(ZoneInfo(get_settings().timezone)).date()
    except Exception:
        return date.today()


async def get_settings_map(session: AsyncSession) -> dict:
    rows = (await session.execute(select(AppSetting))).scalars().all()
    out = dict(DEFAULT_SETTINGS)
    out.update({r.key: r.value for r in rows if r.key in DEFAULT_SETTINGS})
    return out


async def set_setting(session: AsyncSession, key: str, value) -> None:
    row = await session.get(AppSetting, key)
    if row:
        row.value = value
    else:
        session.add(AppSetting(key=key, value=value))


async def usage_status(session: AsyncSession, settings: dict | None = None) -> dict:
    settings = settings or await get_settings_map(session)
    day = await session.get(UsageDay, local_today())
    seconds = day.seconds if day else 0.0
    limit_min = int(settings.get("daily_limit_minutes") or 0)
    extra = day.extra_minutes if day else 0
    limit_s = (limit_min + extra) * 60 if limit_min else 0
    return {
        "day": local_today().isoformat(),
        "seconds": round(seconds),
        "limit_seconds": limit_s,
        "remaining_seconds": max(0, round(limit_s - seconds)) if limit_s else None,
        "exceeded": bool(limit_s and seconds >= limit_s),
        "break_every_minutes": int(settings.get("break_every_minutes") or 0),
        "extra_minutes": extra,
    }


async def add_usage(session: AsyncSession, seconds: float, category: str | None, items_viewed: int) -> None:
    today = local_today()
    day = await session.get(UsageDay, today)
    if day is None:
        day = UsageDay(day=today, seconds=0.0, items_viewed=0, by_category={}, extra_minutes=0)
        session.add(day)
    day.seconds = (day.seconds or 0) + seconds
    day.items_viewed = (day.items_viewed or 0) + items_viewed
    if category:
        bc = dict(day.by_category or {})
        bc[category] = round(bc.get(category, 0) + seconds, 1)
        day.by_category = bc


async def run_agent(name: str, force: bool = False) -> dict:
    """Ejecuta un agente con bloqueo (nunca dos a la vez) y deja registro."""
    cache = get_cache()
    lock = f"lock:agent:{name}"
    if not await cache.set_nx(lock, "1", 900):
        return {"skipped": "ya en ejecución"}
    async with SessionLocal() as session:
        run = AgentRun(agent=name)
        session.add(run)
        await session.commit()
        try:
            if name == "explorer":
                stats = await explorer.run(session, force=force)
                stats["analyst"] = await analyst.run(session)
            elif name == "analyst":
                stats = await analyst.run(session)
            elif name == "curator":
                aff = await preferences.affinity_map(session)
                hl = await curator.build_highlights(session, aff, local_today())
                stats = {"highlights": len(hl)}
            elif name == "maintenance":
                stats = {"decayed": await preferences.decay(session)}
                await session.commit()
            else:
                stats = {}
            run.ok, run.stats = True, stats
        except Exception as exc:  # registrar y seguir: un agente roto no tumba la app
            log.exception("Agente %s falló", name)
            await session.rollback()
            run = await session.get(AgentRun, run.id)
            run.ok, run.error = False, str(exc)[:1000]
            stats = {"error": str(exc)[:300]}
        run.finished_at = datetime.now(timezone.utc)
        await session.commit()
    await cache.delete(lock)
    await cache.delete_prefix("feed:")
    return stats


async def creator_names(session: AsyncSession) -> dict[int, str]:
    return {i: n for i, n in (await session.execute(select(Creator.id, Creator.name))).all()}


async def states_for(session: AsyncSession, ids: list[int]) -> dict[int, ItemState]:
    if not ids:
        return {}
    return {s.item_id: s for s in (await session.execute(select(ItemState).where(ItemState.item_id.in_(ids)))).scalars()}
