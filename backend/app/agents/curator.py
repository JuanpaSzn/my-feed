"""CURADOR: la selección diaria de destacados y el resumen «Lo importante hoy».

Complementa la actualización continua del feed: una vez al día elige lo
verdaderamente importante, intentando cubrir todas tus categorías activas.
"""
from datetime import date, datetime, timedelta, timezone

from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Category, DailyDigest, Highlight, Item, ItemState
from . import llm
from .recommender import load_context, score_item


class Digest(BaseModel):
    headline: str = Field(description="titular de una línea, en español")
    bullets: list[str] = Field(description="3-5 frases cortas: qué pasó y por qué importa")


async def build_highlights(session: AsyncSession, affinity: dict[str, float], day: date | None = None,
                           size: int = 8) -> list[Highlight]:
    day = day or date.today()
    ctx = await load_context(session, affinity, None)
    enabled = [k for k, v in ctx.cat_weight.items() if v > 0]
    hidden = select(ItemState.item_id).where(ItemState.hidden)
    items: list[Item] = []
    for days in (2, 7, 30):
        since = datetime.now(timezone.utc) - timedelta(days=days)
        items = list((await session.execute(
            select(Item).where(Item.status == "active", Item.category_slug.in_(enabled), Item.platform != "myfeed",
                               Item.discovered_at >= since, Item.id.not_in(hidden))
        )).scalars())
        if len(items) >= size * 2:
            break
    if len(items) < size:  # instalación nueva sin red: usa todo lo disponible
        items = list((await session.execute(
            select(Item).where(Item.status == "active", Item.category_slug.in_(enabled), Item.id.not_in(hidden))
        )).scalars())
    scored = sorted((score_item(i, ctx) for i in items), key=lambda s: -(s.total + 0.15 * s.item.quality))
    # Round-robin por categoría para que el resumen cubra todos tus intereses.
    by_cat: dict[str, list] = {}
    for s in scored:
        by_cat.setdefault(s.item.category_slug or "", []).append(s)
    order = sorted(by_cat, key=lambda c: -ctx.cat_weight.get(c, 0))
    picked, used_creators = [], set()
    while len(picked) < size and any(by_cat.values()):
        for c in order:
            lst = by_cat[c]
            while lst and lst[0].item.creator_id and lst[0].item.creator_id in used_creators:
                lst.pop(0)
            if lst and len(picked) < size:
                s = lst.pop(0)
                picked.append(s)
                if s.item.creator_id:
                    used_creators.add(s.item.creator_id)
    await session.execute(delete(Highlight).where(Highlight.day == day))
    out = []
    for rank, s in enumerate(picked, 1):
        reason = s.reasons[0] if s.reasons else f"Lo mejor de {ctx.cat_names.get(s.item.category_slug or '', '')} hoy"
        h = Highlight(day=day, item_id=s.item.id, rank=rank, reason=reason)
        session.add(h)
        out.append(h)
    await session.flush()
    await build_digest(session, day, [s.item for s in picked], ctx.cat_names)
    await session.commit()
    return out


async def build_digest(session: AsyncSession, day: date, items: list[Item], cat_names: dict[str, str]) -> DailyDigest:
    digest = await session.get(DailyDigest, day) or DailyDigest(day=day)
    if not items:
        digest.headline, digest.summary, digest.generator = "Hoy no hay novedades", "", "heuristic"
        session.add(digest)
        return digest
    res = None
    if llm.available() and await llm.budget_left(1):
        lines = "\n".join(f"- [{cat_names.get(i.category_slug or '', '')}] {i.title}: {i.summary or i.description[:200]}" for i in items)
        res = await llm.parse(
            "Eres el editor de MyFeed. Resume en español, con tono cercano y sin exagerar, lo importante del día "
            "para alguien que quiere aprender. No inventes datos que no estén en la lista.",
            f"Destacados de hoy:\n{lines}", Digest, max_tokens=1500,
        )
    if res:
        digest.headline = res.headline[:300]
        digest.summary = "\n".join(f"• {b}" for b in res.bullets[:5])
        digest.generator = "claude"
    else:
        cats = list(dict.fromkeys(cat_names.get(i.category_slug or "", "") for i in items if i.category_slug))
        digest.headline = f"{len(items)} destacados en {', '.join(cats[:3])}" + (" y más" if len(cats) > 3 else "")
        digest.summary = "\n".join(f"• {i.title}" for i in items[:5])
        digest.generator = "heuristic"
    digest.created_at = datetime.now(timezone.utc)
    session.add(digest)
    return digest


async def category_names(session: AsyncSession) -> dict[str, str]:
    return {c.slug: c.name for c in (await session.execute(select(Category))).scalars()}
