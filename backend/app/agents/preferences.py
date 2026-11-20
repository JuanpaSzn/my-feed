"""APRENDIZAJE DE PREFERENCIAS: aprende de likes, guardados, descartes y tiempo de visionado.

Cada interacción ajusta afinidades sobre cuatro ejes: categoría, subtema,
creador y etiquetas. Las afinidades decaen con el tiempo (los gustos cambian) y
están acotadas, así que nada domina el feed para siempre. Todo es editable o
reiniciable desde la app.
"""
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Affinity, Interaction, Item, ItemState, utcnow

# Señal de cada evento. Ver un vídeo largo entero dice mucho; saltarlo en 2 s, también.
EVENT_SIGNAL = {
    "like": 1.0,
    "unlike": -0.8,
    "save": 1.5,
    "unsave": -0.6,
    "complete": 0.7,
    "share": 1.0,
    "open_source": 0.4,
    "note": 1.2,
    "skip": -0.35,
    "hide": -2.0,
    "less_like_this": -1.2,
    "more_like_this": 1.2,
}
LEARNING_RATE = 0.18
CLAMP = 3.0
AXIS_WEIGHT = {"cat": 0.6, "sub": 1.0, "creator": 0.9, "tag": 0.5}


def keys_for(item: Item) -> list[tuple[str, float]]:
    keys: list[tuple[str, float]] = []
    if item.category_slug:
        keys.append((f"cat:{item.category_slug}", AXIS_WEIGHT["cat"]))
    if item.subtopic_slug:
        keys.append((f"sub:{item.subtopic_slug}", AXIS_WEIGHT["sub"]))
    if item.creator_id:
        keys.append((f"creator:{item.creator_id}", AXIS_WEIGHT["creator"]))
    for t in (item.tags or [])[:4]:
        keys.append((f"tag:{t}", AXIS_WEIGHT["tag"]))
    return keys


def watch_signal(watch_seconds: float, duration: int | None) -> tuple[str | None, float]:
    """Convierte el tiempo de visionado en evento implícito."""
    if watch_seconds <= 0:
        return None, 0.0
    if duration and duration > 0:
        ratio = watch_seconds / duration
        if ratio >= 0.85:
            return "complete", EVENT_SIGNAL["complete"]
        if watch_seconds < 3 and ratio < 0.1:
            return "skip", EVENT_SIGNAL["skip"]
        return "watch", min(0.5, ratio * 0.6)
    if watch_seconds < 3:
        return "skip", EVENT_SIGNAL["skip"]
    return "watch", min(0.5, watch_seconds / 120)


async def learn(session: AsyncSession, item: Item, signal: float) -> None:
    if not signal:
        return
    keys = keys_for(item)
    existing = {
        a.key: a for a in (await session.execute(select(Affinity).where(Affinity.key.in_([k for k, _ in keys])))).scalars()
    }
    now = utcnow()
    for key, w in keys:
        a = existing.get(key)
        if a is None:
            a = Affinity(key=key, score=0.0, events=0)
            session.add(a)
        # Actualización con rendimiento decreciente cerca de los extremos.
        delta = LEARNING_RATE * signal * w * (1 - abs(a.score) / (CLAMP * 1.2))
        a.score = max(-CLAMP, min(CLAMP, a.score + delta))
        a.events += 1
        a.updated_at = now


async def get_state(session: AsyncSession, item_id: int) -> ItemState:
    st = await session.get(ItemState, item_id)
    if st is None:
        st = ItemState(item_id=item_id, seen_count=0, watch_seconds=0.0)
        session.add(st)
    return st


async def record(session: AsyncSession, item: Item, kind: str, value: float = 0.0) -> ItemState:
    """Registra una interacción explícita, actualiza el estado y aprende."""
    st = await get_state(session, item.id)
    now = utcnow()
    signal = EVENT_SIGNAL.get(kind, 0.0)
    if kind == "like":
        if st.liked:
            signal = 0.0
        st.liked = True
    elif kind == "unlike":
        if not st.liked:
            signal = 0.0
        st.liked = False
    elif kind == "save":
        if st.saved:
            signal = 0.0
        st.saved, st.saved_at = True, now
    elif kind == "unsave":
        if not st.saved:
            signal = 0.0
        st.saved = False
    elif kind == "hide":
        st.hidden = True
    elif kind == "view":
        st.seen_count = (st.seen_count or 0) + 1
        st.first_seen_at = st.first_seen_at or now
        st.last_seen_at = now
        if value:
            st.watch_seconds = (st.watch_seconds or 0) + value
            implicit, signal = watch_signal(value, item.duration_sec)
            if implicit:
                kind = implicit if implicit != "watch" else "view"
    st.updated_at = now
    session.add(Interaction(item_id=item.id, kind=kind, value=value))
    await learn(session, item, signal)
    return st


async def decay(session: AsyncSession, factor: float = 0.985) -> int:
    """Se ejecuta a diario: las preferencias antiguas pierden peso poco a poco."""
    rows = (await session.execute(select(Affinity))).scalars().all()
    for a in rows:
        a.score *= factor
    await session.execute(delete(Affinity).where(Affinity.score.between(-0.01, 0.01), Affinity.events < 2))
    return len(rows)


async def affinity_map(session: AsyncSession) -> dict[str, float]:
    return {a.key: a.score for a in (await session.execute(select(Affinity))).scalars()}


async def reset(session: AsyncSession) -> None:
    await session.execute(delete(Affinity))


def describe(aff: dict[str, float], labels: dict[str, str], top: int = 8) -> dict:
    """Resumen legible de lo aprendido (para la pantalla de preferencias)."""
    pos = sorted(((k, v) for k, v in aff.items() if v > 0.05), key=lambda kv: -kv[1])[:top]
    neg = sorted(((k, v) for k, v in aff.items() if v < -0.05), key=lambda kv: kv[1])[:top]

    def fmt(kv):
        k, v = kv
        return {"key": k, "label": labels.get(k, k.split(":", 1)[1]), "score": round(v, 2)}

    return {"likes": [fmt(x) for x in pos], "dislikes": [fmt(x) for x in neg],
            "updated_at": datetime.now(timezone.utc).isoformat()}
