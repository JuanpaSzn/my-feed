"""MOTOR DE RECOMENDACIONES.

No ordena por viralidad: las visitas ni siquiera se usan. Cada ítem recibe
cinco notas (0-1) y después un reordenamiento por diversidad:

| Criterio     | Qué evalúa                                   |
| ------------ | -------------------------------------------- |
| Relevancia   | peso de la categoría + lo aprendido de ti    |
| Calidad      | nota del agente analista                     |
| Actualidad   | decaimiento por categoría (IA caduca rápido, |
|              | la filosofía casi nunca)                     |
| Credibilidad | fiabilidad del creador o la fuente           |
| Diversidad   | castigo a repetir creador/tema seguidos,     |
|              | cuotas por categoría y huecos de exploración |
"""
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Category, Creator, FeedCommand, Item, ItemState, Subtopic
from ..text import contains_term, normalize

WEIGHTS = {"relevance": 0.34, "quality": 0.26, "recency": 0.16, "credibility": 0.14, "novelty": 0.10}


@dataclass
class Context:
    cat_weight: dict[str, float]
    half_life: dict[str, float]
    affinity: dict[str, float]
    creator_names: dict[int, str] = field(default_factory=dict)
    cat_names: dict[str, str] = field(default_factory=dict)
    sub_names: dict[str, str] = field(default_factory=dict)
    recent_creators: set[int] = field(default_factory=set)
    command: dict | None = None
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Scored:
    item: Item
    total: float
    parts: dict[str, float]
    match: float = 0.0
    reasons: list[str] = field(default_factory=list)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def command_match(item: Item, cmd: dict) -> float:
    """0-1: cuánto encaja un ítem con un comando escrito ("muéstrame...")."""
    score = 0.0
    cats = cmd.get("categories") or []
    subs = cmd.get("subtopics") or []
    kws = cmd.get("keywords") or []
    if cats and item.category_slug in cats:
        score += 0.35
    if subs and item.subtopic_slug in subs:
        score += 0.25
    if kws:
        text = normalize(f"{item.title} {' '.join(item.tags or [])} {item.summary} {item.description[:500]}")
        hits = sum(1 for k in kws if contains_term(text, normalize(k)))
        score += 0.6 * min(1.0, hits / max(1, min(len(kws), 3)))
    fmt = cmd.get("format")
    if fmt and fmt != "all" and item.format != fmt:
        score *= 0.3
    max_age = cmd.get("max_age_days")
    if max_age:
        when = _aware(item.published_at) or _aware(item.discovered_at)
        if when and when < datetime.now(timezone.utc) - timedelta(days=max_age):
            score *= 0.35
    return min(1.0, score)


def score_item(it: Item, ctx: Context) -> Scored:
    reasons: list[str] = []
    cat = it.category_slug or ""
    w = ctx.cat_weight.get(cat, 0.5)
    aff = ctx.affinity
    a = (
        aff.get(f"cat:{cat}", 0) * 0.6
        + aff.get(f"sub:{it.subtopic_slug}", 0) * 1.0
        + (aff.get(f"creator:{it.creator_id}", 0) * 0.9 if it.creator_id else 0)
    )
    tags = [aff.get(f"tag:{t}", 0) for t in (it.tags or [])[:4]]
    if tags:
        a += (sum(tags) / len(tags)) * 0.5
    learned = math.tanh(a / 2)
    relevance = max(0.0, min(1.0, 0.3 + 0.35 * (w / 2) + 0.35 * learned + (0.08 if w >= 1.5 else 0)))
    if learned > 0.25:
        reasons.append(f"Sueles disfrutar {ctx.sub_names.get(it.subtopic_slug or '', ctx.cat_names.get(cat, 'este tema'))}")
    elif w >= 1.5:
        reasons.append(f"Le diste prioridad a {ctx.cat_names.get(cat, cat)}")

    match = 0.0
    if ctx.command:
        match = command_match(it, ctx.command)
        relevance = 0.35 * relevance + 0.65 * match
        if match >= 0.35:
            reasons.insert(0, f"Coincide con lo que pediste: «{ctx.command.get('label', 'tu búsqueda')}»")

    quality = it.quality if it.quality is not None else 0.5
    if quality >= 0.75:
        reasons.append("Muy buena nota de calidad")

    if it.origin == "seed" and it.published_at is None:
        # Clásicos y microlecciones: atemporales, ni nuevos ni viejos.
        recency = 0.5
        if it.platform == "myfeed":
            reasons.append("Microlección de MyFeed: 1 minuto")
        else:
            reasons.append("Un clásico que vale la pena")
    else:
        when = _aware(it.published_at) or _aware(it.discovered_at) or ctx.now
        age = max(0.0, (ctx.now - when).total_seconds() / 86400)
        hl = ctx.half_life.get(cat, 30.0) * (0.6 if it.is_news else 1.0)
        floor = 0.12 if it.is_news else 0.25
        recency = max(floor, 0.5 ** (age / max(hl, 1)))
        if age <= 2:
            reasons.append("Es de las últimas 48 horas")

    credibility = it.credibility if it.credibility is not None else 0.6
    if credibility >= 0.9:
        reasons.append("Fuente muy fiable")

    novelty = 0.4 if (it.creator_id and it.creator_id in ctx.recent_creators) else 1.0
    parts = {
        "relevance": round(relevance, 3),
        "quality": round(quality, 3),
        "recency": round(recency, 3),
        "credibility": round(credibility, 3),
        "novelty": round(novelty, 3),
    }
    total = sum(WEIGHTS[k] * v for k, v in parts.items())
    if it.clickbait:
        total -= 0.08
    return Scored(item=it, total=round(total, 4), parts=parts, match=match, reasons=reasons[:3])


def diversify(scored: list[Scored], ctx: Context, limit: int, rng: random.Random | None = None,
              exploration_every: int = 8) -> list[Scored]:
    """Reordenamiento voraz: evita repetir creador/tema y respeta las cuotas por categoría."""
    rng = rng or random.Random()
    pool = sorted(scored, key=lambda s: -s.total)[: max(limit * 6, 120)]
    total_w = sum(v for v in ctx.cat_weight.values() if v > 0) or 1.0
    target = {k: v / total_w for k, v in ctx.cat_weight.items() if v > 0}
    picked: list[Scored] = []
    counts: dict[str, int] = {}
    cards_since = 99

    while pool and len(picked) < limit:
        slot = len(picked) + 1
        # Hueco de exploración: algo bueno de un tema que aún no domina tus gustos.
        if exploration_every and slot % exploration_every == 0 and not ctx.command:
            cands = [s for s in pool[:60] if ctx.affinity.get(f"cat:{s.item.category_slug}", 0) < 0.3
                     and s.item.quality >= 0.5]
            if cands:
                choice = rng.choice(cands[:12])
                choice.reasons = ["Explorando: algo distinto que podría gustarte"] + choice.reasons[:1]
                choice.parts["exploration"] = 1.0
                pool.remove(choice)
                picked.append(choice)
                counts[choice.item.category_slug or ""] = counts.get(choice.item.category_slug or "", 0) + 1
                continue

        best, best_val = None, -1e9
        last = picked[-5:]
        for s in pool[:150]:
            it = s.item
            val = s.total
            if it.creator_id:
                val -= 0.22 * sum(1 for p in last[-4:] if p.item.creator_id == it.creator_id)
            elif it.author_name:
                val -= 0.15 * sum(1 for p in last[-3:] if p.item.author_name == it.author_name)
            if last and last[-1].item.category_slug == it.category_slug:
                val -= 0.08
                if len(last) >= 2 and last[-2].item.category_slug == it.category_slug:
                    val -= 0.14
            val -= 0.05 * sum(1 for p in last if p.item.subtopic_slug and p.item.subtopic_slug == it.subtopic_slug)
            if it.format == "article" and last and last[-1].item.format == "article":
                val -= 0.12
            if it.platform == "myfeed" and cards_since < 6:
                val -= 0.3
            if not ctx.command:
                share = counts.get(it.category_slug or "", 0) / max(1, len(picked))
                val += 0.2 * (target.get(it.category_slug or "", 0) - share)
            if val > best_val:
                best, best_val = s, val
        if best is None:
            break
        pool.remove(best)
        picked.append(best)
        counts[best.item.category_slug or ""] = counts.get(best.item.category_slug or "", 0) + 1
        cards_since = 0 if best.item.platform == "myfeed" else cards_since + 1
    return picked


# ------------------------------------------------------------- BD ----------

async def load_context(session: AsyncSession, affinity: dict[str, float], command: dict | None) -> Context:
    cats = (await session.execute(select(Category))).scalars().all()
    subs = (await session.execute(select(Subtopic))).scalars().all()
    creators = (await session.execute(select(Creator.id, Creator.name))).all()
    since = datetime.now(timezone.utc) - timedelta(days=3)
    recent = (await session.execute(
        select(Item.creator_id).join(ItemState, ItemState.item_id == Item.id)
        .where(ItemState.last_seen_at >= since, Item.creator_id.is_not(None))
    )).scalars().all()
    return Context(
        cat_weight={c.slug: (c.weight if c.enabled else 0.0) for c in cats},
        half_life={c.slug: c.recency_half_life_days for c in cats},
        affinity=affinity,
        creator_names={i: n for i, n in creators},
        cat_names={c.slug: c.name for c in cats},
        sub_names={s.slug: s.name for s in subs},
        recent_creators=set(recent),
        command=command,
    )


async def active_command(session: AsyncSession) -> FeedCommand | None:
    now = datetime.now(timezone.utc)
    cmd = (await session.execute(
        select(FeedCommand).where(FeedCommand.active).order_by(FeedCommand.created_at.desc()).limit(1)
    )).scalars().first()
    if cmd and cmd.expires_at and _aware(cmd.expires_at) < now:
        cmd.active = False
        await session.commit()
        return None
    return cmd


async def candidates(session: AsyncSession, ctx: Context, fmt: str = "all", category: str | None = None,
                     exclude_ids: set[int] | None = None, pool_size: int = 1500) -> list[Item]:
    enabled = [k for k, v in ctx.cat_weight.items() if v > 0]
    blocked = select(Creator.id).where(Creator.status.in_(["rejected", "muted", "error"]))
    q = select(Item).where(Item.status == "active", or_(Item.creator_id.is_(None), Item.creator_id.not_in(blocked)))
    if category:
        q = q.where(Item.category_slug == category)
    elif ctx.command and ctx.command.get("categories"):
        q = q.where(Item.category_slug.in_(ctx.command["categories"]))
    else:
        q = q.where(Item.category_slug.in_(enabled))
    if fmt in ("short", "long", "article"):
        q = q.where(Item.format == fmt)
    elif ctx.command and ctx.command.get("format") in ("short", "long", "article"):
        q = q.where(Item.format == ctx.command["format"])
    # Excluir lo ya visto, guardado u oculto.
    seen = select(ItemState.item_id).where(
        or_(ItemState.hidden, ItemState.saved, ItemState.seen_count > 0)
    )
    q = q.where(Item.id.not_in(seen))
    if exclude_ids:
        q = q.where(Item.id.not_in(list(exclude_ids)))
    q = q.order_by(Item.discovered_at.desc()).limit(pool_size)
    return list((await session.execute(q)).scalars().all())


async def rewatch_candidates(session: AsyncSession, ctx: Context, exclude_ids: set[int], limit: int) -> list[Item]:
    """Cuando no queda nada nuevo: lo visto hace tiempo que valió la pena (repaso espaciado)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=10)
    q = (
        select(Item).join(ItemState, ItemState.item_id == Item.id)
        .where(Item.status == "active", ItemState.hidden.is_(False), ItemState.last_seen_at < cutoff,
               Item.category_slug.in_([k for k, v in ctx.cat_weight.items() if v > 0]))
        .order_by(ItemState.last_seen_at.asc()).limit(limit * 3)
    )
    if exclude_ids:
        q = q.where(Item.id.not_in(list(exclude_ids)))
    return list((await session.execute(q)).scalars().all())


async def build_feed(session: AsyncSession, affinity: dict[str, float], limit: int = 30, fmt: str = "all",
                     category: str | None = None, exclude_ids: set[int] | None = None,
                     command: dict | None = None, seed: int | None = None) -> list[Scored]:
    ctx = await load_context(session, affinity, command)
    items = await candidates(session, ctx, fmt, category, exclude_ids)
    scored = [score_item(i, ctx) for i in items]
    if command:
        strong = [s for s in scored if s.match >= 0.3]
        # Si el comando encuentra suficiente, el feed se centra en ello; si no, mezcla.
        scored = strong if len(strong) >= min(limit, 6) else strong + [s for s in scored if s.match < 0.3]
    picked = diversify(scored, ctx, limit, random.Random(seed))
    if len(picked) < limit // 2 and not category:
        extra = await rewatch_candidates(session, ctx, (exclude_ids or set()) | {p.item.id for p in picked},
                                         limit - len(picked))
        for s in diversify([score_item(i, ctx) for i in extra], ctx, limit - len(picked), random.Random(seed)):
            s.reasons = ["Repaso: lo viste hace tiempo y vale la pena"]
            picked.append(s)
    return picked
