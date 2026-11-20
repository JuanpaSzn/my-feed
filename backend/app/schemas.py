from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from .models import Item, ItemState


class CreatorRef(BaseModel):
    id: int
    name: str


class ItemStateOut(BaseModel):
    liked: bool = False
    saved: bool = False
    hidden: bool = False
    note: str = ""
    collection: str = ""
    seen_count: int = 0


class ScoreOut(BaseModel):
    total: float
    parts: dict[str, float]
    reasons: list[str]


class ItemOut(BaseModel):
    id: int
    platform: str
    external_id: str
    url: str
    embed_url: str
    title: str
    description: str
    summary: str
    key_points: list[str]
    author_name: str
    creator: CreatorRef | None
    thumbnail_url: str
    duration_sec: int | None
    format: str
    language: str
    category: str | None
    subtopic: str | None
    tags: list[str]
    published_at: datetime | None
    discovered_at: datetime | None
    quality: float
    credibility: float
    is_news: bool
    analysis: str
    state: ItemStateOut
    score: ScoreOut | None = None


def item_out(it: Item, st: ItemState | None = None, creator_name: str | None = None, score=None) -> ItemOut:
    return ItemOut(
        id=it.id, platform=it.platform, external_id=it.external_id, url=it.url, embed_url=it.embed_url or "",
        title=it.title, description=(it.description or "")[:700], summary=it.summary or "",
        key_points=list(it.key_points or []), author_name=it.author_name or (creator_name or ""),
        creator=CreatorRef(id=it.creator_id, name=creator_name or it.author_name or "") if it.creator_id else None,
        thumbnail_url=it.thumbnail_url or "", duration_sec=it.duration_sec, format=it.format, language=it.language,
        category=it.category_slug, subtopic=it.subtopic_slug, tags=list(it.tags or []), published_at=it.published_at,
        discovered_at=it.discovered_at, quality=round(it.quality or 0, 3), credibility=round(it.credibility or 0, 3),
        is_news=bool(it.is_news), analysis=it.analysis,
        state=ItemStateOut(liked=st.liked, saved=st.saved, hidden=st.hidden, note=st.note or "",
                           collection=st.collection or "", seen_count=st.seen_count or 0) if st else ItemStateOut(),
        score=ScoreOut(total=score.total, parts=score.parts, reasons=score.reasons) if score else None,
    )


class FeedOut(BaseModel):
    session: str
    offset: int
    items: list[ItemOut]
    has_more: bool
    command: dict | None = None
    usage: dict | None = None


EventKind = Literal["like", "unlike", "save", "unsave", "hide", "view", "share", "open_source",
                    "less_like_this", "more_like_this"]


class EventIn(BaseModel):
    kind: EventKind
    value: float = Field(0.0, ge=0, le=86400, description="segundos vistos (para view)")


class NoteIn(BaseModel):
    note: str = Field("", max_length=4000)
    collection: str | None = Field(None, max_length=80)


class AddLinkIn(BaseModel):
    url: str = Field(min_length=4, max_length=1000)
    category: str | None = None


class CategoryPatch(BaseModel):
    weight: float | None = Field(None, ge=0, le=3)
    enabled: bool | None = None


class SubtopicPatch(BaseModel):
    enabled: bool


class CreatorIn(BaseModel):
    url: str = Field(min_length=2, max_length=500, description="URL del canal, @handle o channel id")
    category: str | None = None


class CreatorPatch(BaseModel):
    status: Literal["approved", "rejected", "muted", "suggested"] | None = None
    category: str | None = None
    credibility: float | None = Field(None, ge=0, le=1)


class CommandIn(BaseModel):
    text: str = Field(min_length=2, max_length=400)
    search_online: bool = True


class HeartbeatIn(BaseModel):
    seconds: float = Field(ge=0, le=600)
    category: str | None = None
    items_viewed: int = Field(0, ge=0, le=200)


class ExtendIn(BaseModel):
    minutes: int = Field(10, ge=1, le=60)


class RunAgentIn(BaseModel):
    agent: Literal["explorer", "analyst", "curator", "all"] = "all"
    force: bool = False


class HighlightsOut(BaseModel):
    day: date
    headline: str
    summary: str
    generator: str
    items: list[ItemOut]
