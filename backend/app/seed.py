"""Carga inicial idempotente: se puede ejecutar en cada arranque sin pisar tus cambios."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .agents.analyst import apply_heuristic
from .models import AppSetting, Category, Creator, Item, Source, Subtopic
from .seed_data import CREATORS, KNOWLEDGE_CARDS, SEED_VIDEOS, SOURCES, SUGGESTED_CREATORS
from .taxonomy import CATEGORIES

DEFAULT_SETTINGS = {
    "daily_limit_minutes": 45,       # límite diario de uso (0 = sin límite)
    "break_every_minutes": 20,       # recordatorio de pausa consciente
    "autoplay": True,
    "muted_start": False,
    "show_reasons": True,            # «¿Por qué veo esto?» siempre visible
    "exploration": True,             # huecos de exploración en el feed
    "language": "any",               # any, es, en
    "purpose_prompt": True,          # pregunta «¿qué quieres aprender hoy?» al abrir
    "quiet_hours": {"enabled": False, "start": "23:30", "end": "06:00"},
    "onboarded": False,
}


async def seed(session: AsyncSession) -> dict:
    stats = {"categories": 0, "creators": 0, "sources": 0, "items": 0}
    existing_cats = {c.slug for c in (await session.execute(select(Category))).scalars()}
    existing_subs = {s.slug for s in (await session.execute(select(Subtopic))).scalars()}
    for pos, c in enumerate(CATEGORIES):
        if c["slug"] not in existing_cats:
            session.add(Category(slug=c["slug"], name=c["name"], emoji=c["emoji"], color=c["color"],
                                 description=c["description"], position=pos, recency_half_life_days=c["half_life"]))
            stats["categories"] += 1
        for spos, (slug, name, kws, queries) in enumerate(c["subtopics"]):
            if slug not in existing_subs:
                session.add(Subtopic(slug=slug, category_slug=c["slug"], name=name, keywords=kws,
                                     search_queries=queries, position=spos))
    await session.flush()

    known = {(c.platform, c.external_id) for c in (await session.execute(select(Creator))).scalars()}
    for ch, name, cat, lang, cred in CREATORS:
        if ("youtube", ch) not in known:
            session.add(Creator(platform="youtube", external_id=ch, name=name, category_slug=cat, language=lang,
                                credibility=cred, status="approved", origin="seed",
                                url=f"https://www.youtube.com/channel/{ch}"))
            stats["creators"] += 1
    for ch, name, cat, lang, cred, reason in SUGGESTED_CREATORS:
        if ("youtube", ch) not in known:
            session.add(Creator(platform="youtube", external_id=ch, name=name, category_slug=cat, language=lang,
                                credibility=cred, status="suggested", origin="ai", reason=reason,
                                url=f"https://www.youtube.com/channel/{ch}"))
            stats["creators"] += 1

    known_src = {s.url for s in (await session.execute(select(Source))).scalars()}
    for kind, name, url, cat, lang, cred in SOURCES:
        if url not in known_src:
            session.add(Source(kind=kind, name=name, url=url, category_slug=cat, language=lang, credibility=cred))
            stats["sources"] += 1
    await session.flush()

    creators_by_name = {c.name: c for c in (await session.execute(select(Creator))).scalars()}
    known_items = {(p, e) for p, e in (await session.execute(select(Item.platform, Item.external_id))).all()}
    now = datetime.now(timezone.utc)
    for n, (vid, title, author, cat, sub, fmt, dur) in enumerate(SEED_VIDEOS):
        if ("youtube", vid) in known_items:
            continue
        cr = creators_by_name.get(author)
        it = Item(platform="youtube", external_id=vid, url=f"https://www.youtube.com/watch?v={vid}",
                  embed_url=f"https://www.youtube-nocookie.com/embed/{vid}", title=title, author_name=author,
                  creator_id=cr.id if cr else None, thumbnail_url=f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                  duration_sec=dur, format=fmt, language="en", category_slug=cat, subtopic_slug=sub,
                  origin="seed", discovered_at=now - timedelta(minutes=n), published_at=None)
        apply_heuristic(it, cat, cr.credibility if cr else 0.85)
        it.quality = max(it.quality, 0.72)  # clásicos elegidos a mano
        session.add(it)
        stats["items"] += 1
    for n, (cid, cat, sub, title, body, points) in enumerate(KNOWLEDGE_CARDS):
        if ("myfeed", cid) in known_items:
            continue
        session.add(Item(platform="myfeed", external_id=cid, url="", title=title, description=body, summary=body,
                         key_points=points, author_name="Microlección MyFeed", format="short", language="es",
                         category_slug=cat, subtopic_slug=sub, quality=0.7, credibility=0.85, analysis="heuristic",
                         origin="seed", duration_sec=45, discovered_at=now - timedelta(hours=1, minutes=n)))
        stats["items"] += 1

    for key, value in DEFAULT_SETTINGS.items():
        if await session.get(AppSetting, key) is None:
            session.add(AppSetting(key=key, value=value))
    await session.commit()
    return stats
