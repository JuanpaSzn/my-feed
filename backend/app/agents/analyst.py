"""AGENTE ANALISTA: entiende de qué trata cada ítem, lo clasifica y evalúa su calidad.

Dos niveles:
1. Heurístico (siempre, instantáneo y gratis): vocabulario de la taxonomía,
   señales de cebo de clics, señales educativas, credibilidad de la fuente.
2. Claude (opcional): análisis por lotes con salida estructurada, resumen en
   español y puntos clave. Solo para ítems recientes y con tope diario.
"""
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Creator, Item, Source
from ..taxonomy import CATEGORIES, CLICKBAIT_MARKERS, EDUCATIONAL_MARKERS, POLITICS_MARKERS
from ..text import contains_term, normalize
from . import llm

log = logging.getLogger("myfeed.analyst")

_SUBTOPICS = [
    (cat["slug"], sub[0], [normalize(k) for k in sub[2]]) for cat in CATEGORIES for sub in cat["subtopics"]
]
CATEGORY_SLUGS = [c["slug"] for c in CATEGORIES]
NEWS_WORDS = ["anuncia", "lanza", "presenta", "nuevo", "nueva", "announces", "launches", "released", "unveils",
              "breaking", "ultima hora", "acaba de", "just", "today", "hoy", "esta semana", "this week"]


class HeuristicResult(BaseModel):
    category: str | None
    subtopic: str | None
    tags: list[str]
    quality: float
    clickbait: bool
    is_news: bool
    political: bool
    summary: str


def _caps_ratio(title: str) -> float:
    letters = [c for c in title if c.isalpha()]
    if len(letters) < 8:
        return 0.0
    return sum(1 for c in letters if c.isupper()) / len(letters)


def first_sentence(text: str, limit: int = 220) -> str:
    text = (text or "").strip().replace("\n", " ")
    if not text:
        return ""
    m = re.search(r"(.{40,}?[.!?])(\s|$)", text)
    s = m.group(1) if m else text
    return s[:limit].rstrip() + ("…" if len(s) > limit else "")


def heuristic_analyze(
    title: str,
    description: str = "",
    prior_category: str | None = None,
    duration_sec: int | None = None,
    credibility: float = 0.6,
) -> HeuristicResult:
    nt = normalize(title)
    nd = normalize(description)[:2000]
    cat_scores: dict[str, float] = {}
    sub_scores: dict[str, tuple[str, float, list[str]]] = {}
    for cat, sub, kws in _SUBTOPICS:
        found: dict[str, float] = {}
        for kw in kws:
            if contains_term(nt, kw):
                found[kw] = 2.0
            elif nd and contains_term(nd, kw):
                found[kw] = 0.7
        # "futbol sala" no debe contar además como "futbol".
        hits = [k for k in found if not any(k != o and k in o for o in found)]
        score = sum(found[k] for k in hits)
        if score:
            cat_scores[cat] = cat_scores.get(cat, 0.0) + score
            sub_scores[sub] = (cat, score, hits)
    if prior_category:
        cat_scores[prior_category] = cat_scores.get(prior_category, 0.0) + 2.5

    category = max(cat_scores, key=cat_scores.get) if cat_scores else None
    subtopic, tags = None, []
    if category:
        subs = [(s, v) for s, v in sub_scores.items() if v[0] == category]
        if subs:
            best = max(subs, key=lambda x: x[1][1])
            subtopic = best[0]
            tags = list(dict.fromkeys(h for _, v in subs for h in v[2]))[:6]

    full = f"{nt} {nd}"
    clickbait = any(m in title.lower() or m in nt for m in CLICKBAIT_MARKERS) or _caps_ratio(title) > 0.6
    educational = sum(1 for m in EDUCATIONAL_MARKERS if m in f" {nt} ")
    political = sum(1 for m in POLITICS_MARKERS if contains_term(full, m)) >= 2

    q = 0.5
    q += min(educational, 2) * 0.1
    if clickbait:
        q -= 0.25
    if len(nd) > 250:
        q += 0.06
    elif len(nd) < 30:
        q -= 0.04
    if duration_sec is not None:
        if duration_sec < 20:
            q -= 0.12
        elif 240 <= duration_sec <= 3600:
            q += 0.05
    if political:
        q -= 0.3
    if not category:
        q -= 0.15
    q = 0.7 * q + 0.3 * credibility
    q = round(max(0.05, min(0.97, q)), 3)

    is_news = any(contains_term(nt, w) for w in NEWS_WORDS)
    return HeuristicResult(
        category=category,
        subtopic=subtopic,
        tags=tags,
        quality=q,
        clickbait=clickbait,
        is_news=is_news,
        political=political,
        summary=first_sentence(description),
    )


def apply_heuristic(item: Item, prior_category: str | None, credibility: float) -> None:
    r = heuristic_analyze(item.title, item.description, prior_category, item.duration_sec, credibility)
    item.category_slug = item.category_slug or r.category
    if item.category_slug == r.category or not item.subtopic_slug:
        item.subtopic_slug = item.subtopic_slug or r.subtopic
    item.tags = item.tags or r.tags
    item.quality = r.quality
    item.clickbait = r.clickbait
    item.is_news = r.is_news
    item.credibility = credibility
    if not item.summary:
        item.summary = r.summary
    item.analysis = "heuristic"
    if r.political and item.category_slug == "ciencia":
        item.status = "hidden"  # "noticias importantes, sin centrarnos en política"


# ---------------------------------------------------------------- Claude ----

SubtopicSlug = str


class ItemAnalysis(BaseModel):
    id: int
    category: Literal["deporte", "ciberseguridad", "ia", "programacion", "mente", "ciencia", "ninguna"]
    subtopic: SubtopicSlug = Field(description="slug del subtema dentro de la categoría")
    quality: float = Field(description="0-1: cuánto aporta y enseña, no cuán viral es")
    clickbait: bool
    is_news: bool
    political: bool = Field(description="true si se centra en política partidista")
    summary_es: str = Field(description="1-2 frases en español, qué aprenderás")
    key_points: list[str] = Field(description="hasta 3 ideas clave en español, frases cortas")
    tags: list[str] = Field(description="hasta 5 etiquetas en minúsculas")


class BatchAnalysis(BaseModel):
    items: list[ItemAnalysis]


def _system_prompt() -> str:
    lines = [
        "Eres el agente analista de MyFeed, una red social personal de vídeos para aprender.",
        "El usuario quiere sustituir el doomscrolling por contenido de sus intereses.",
        "Para cada ítem decides categoría, subtema y calidad. La calidad mide cuánto aporta,",
        "su rigor y si enseña algo; no su viralidad. Penaliza el cebo de clics, el sensacionalismo",
        "y el contenido vacío. Si un ítem no encaja en ninguna categoría usa 'ninguna'.",
        "La categoría ciencia incluye noticias internacionales importantes, pero no política partidista.",
        "Escribe summary_es y key_points en español neutro aunque el ítem esté en inglés.",
        "",
        "Taxonomía (categoría: subtemas):",
    ]
    for c in CATEGORIES:
        subs = ", ".join(f"{s[0]} ({s[1]})" for s in c["subtopics"])
        lines.append(f"- {c['slug']} — {c['name']}: {subs}")
    return "\n".join(lines)


SYSTEM_PROMPT = _system_prompt()
_VALID_SUBS = {sub: cat for cat, sub, _ in _SUBTOPICS}


def _item_block(it: Item, creator_name: str) -> str:
    desc = (it.description or "")[:600].replace("\n", " ")
    dur = f"{it.duration_sec}s" if it.duration_sec else "?"
    return f"<item id=\"{it.id}\" formato=\"{it.format}\" duracion=\"{dur}\" autor=\"{creator_name}\">\n{it.title}\n{desc}\n</item>"


async def claude_analyze(items: list[Item], names: dict[int, str]) -> int:
    if not items or not llm.available() or not await llm.budget_left(len(items)):
        return 0
    user = "Analiza estos ítems:\n\n" + "\n\n".join(_item_block(i, names.get(i.id, i.author_name)) for i in items)
    result = await llm.parse(SYSTEM_PROMPT, user, BatchAnalysis, max_tokens=6000)
    if not result:
        return 0
    by_id = {i.id: i for i in items}
    done = 0
    for a in result.items:
        it = by_id.get(a.id)
        if not it:
            continue
        if a.category == "ninguna":
            it.status = "hidden"
        else:
            it.category_slug = a.category
            it.subtopic_slug = a.subtopic if _VALID_SUBS.get(a.subtopic) == a.category else it.subtopic_slug
        if a.political:
            it.status = "hidden"
        q = max(0.0, min(1.0, a.quality))
        it.quality = round(0.75 * q + 0.25 * (it.credibility or 0.6), 3)
        it.clickbait = a.clickbait
        it.is_news = a.is_news
        it.summary = a.summary_es[:500]
        it.key_points = [p[:160] for p in a.key_points[:3]]
        it.tags = [t.lower()[:40] for t in a.tags[:5]] or it.tags
        it.analysis = "claude"
        done += 1
    return done


async def run(session: AsyncSession, claude_batch: int = 12, claude_max: int = 60) -> dict:
    """Analiza todo lo pendiente con la heurística y refina lo reciente con Claude."""
    pending = (
        await session.execute(select(Item).where(Item.analysis == "pending").limit(2000))
    ).scalars().all()
    creators = {c.id: c for c in (await session.execute(select(Creator))).scalars().all()}
    sources = {s.id: s for s in (await session.execute(select(Source))).scalars().all()}
    for it in pending:
        cr = creators.get(it.creator_id) if it.creator_id else None
        src = sources.get(it.source_id) if it.source_id else None
        prior = (cr.category_slug if cr else None) or (src.category_slug if src else None)
        cred = cr.credibility if cr else (src.credibility if src else 0.6)
        apply_heuristic(it, prior, cred)
    await session.commit()

    refined = 0
    if llm.available():
        since = datetime.now(timezone.utc) - timedelta(days=7)
        recent = (
            await session.execute(
                select(Item)
                .where(Item.analysis == "heuristic", Item.status == "active", Item.discovered_at >= since,
                       Item.platform != "myfeed")
                .order_by(Item.discovered_at.desc())
                .limit(claude_max)
            )
        ).scalars().all()
        names = {i.id: (creators[i.creator_id].name if i.creator_id in creators else i.author_name) for i in recent}
        for start in range(0, len(recent), claude_batch):
            n = await claude_analyze(list(recent[start : start + claude_batch]), names)
            if n == 0:
                break  # sin presupuesto o sin respuesta: no insistir
            refined += n
            await session.commit()
    return {"heuristic": len(pending), "claude": refined}
