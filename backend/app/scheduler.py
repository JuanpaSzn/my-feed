"""Planificador mínimo dentro del propio proceso (sin Celery ni workers extra).

- Cada `discovery_interval_minutes`: explorador + analista.
- Una vez al día (a `highlights_hour` hora local): destacados, decaimiento de
  preferencias y limpieza de lo viejo que nunca viste.

Duerme casi todo el tiempo: consumo de CPU prácticamente nulo.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select

from .cache import get_cache
from .config import get_settings
from .db import SessionLocal
from .models import Highlight, Item, ItemState
from .services import local_today, run_agent

log = logging.getLogger("myfeed.scheduler")


async def cleanup() -> int:
    """Borra ítems antiguos que nunca viste ni guardaste, para que la BD no crezca sin control."""
    s = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=s.keep_unseen_days)
    async with SessionLocal() as session:
        touched = select(ItemState.item_id)
        highlighted = select(Highlight.item_id)
        res = await session.execute(
            delete(Item).where(Item.discovered_at < cutoff, Item.origin.in_(["rss", "search"]),
                               Item.id.not_in(touched), Item.id.not_in(highlighted))
        )
        await session.commit()
        return res.rowcount or 0


async def daily_jobs() -> None:
    cache = get_cache()
    key = f"daily:{local_today().isoformat()}"
    if not await cache.set_nx(key, "1", 26 * 3600):
        return
    await run_agent("curator")
    await run_agent("maintenance")
    removed = await cleanup()
    log.info("Tareas diarias hechas (limpieza: %s ítems)", removed)


async def loop(stop: asyncio.Event) -> None:
    s = get_settings()
    await asyncio.sleep(5)  # deja arrancar la API primero
    last_discovery = 0.0
    while not stop.is_set():
        now = asyncio.get_running_loop().time()
        try:
            if now - last_discovery >= s.discovery_interval_minutes * 60 or last_discovery == 0:
                log.info("Explorador: inicio")
                stats = await run_agent("explorer")
                log.info("Explorador: %s", stats)
                last_discovery = now
            try:
                hour = datetime.now(ZoneInfo(s.timezone)).hour
            except Exception:
                hour = datetime.now().hour
            if hour >= s.highlights_hour:
                await daily_jobs()
        except Exception:
            log.exception("Error en el planificador")
        try:
            await asyncio.wait_for(stop.wait(), timeout=300)
        except asyncio.TimeoutError:
            pass


def start() -> tuple[asyncio.Task, asyncio.Event]:
    stop = asyncio.Event()
    task = asyncio.create_task(loop(stop))
    return task, stop


async def has_items() -> bool:
    async with SessionLocal() as session:
        return (await session.execute(select(Item.id).limit(1))).first() is not None
