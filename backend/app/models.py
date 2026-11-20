"""Modelo de datos. La app es personal (un solo perfil), así que no hay tabla de usuarios."""
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Category(Base):
    __tablename__ = "categories"
    slug: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    emoji: Mapped[str] = mapped_column(String(8), default="")
    color: Mapped[str] = mapped_column(String(9), default="#888888")
    description: Mapped[str] = mapped_column(Text, default="")
    weight: Mapped[float] = mapped_column(Float, default=1.0)  # 0 = apagada, 2 = el doble
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    recency_half_life_days: Mapped[float] = mapped_column(Float, default=30.0)

    subtopics: Mapped[list["Subtopic"]] = relationship(
        back_populates="category", order_by="Subtopic.position", lazy="selectin"
    )


class Subtopic(Base):
    __tablename__ = "subtopics"
    slug: Mapped[str] = mapped_column(String(60), primary_key=True)
    category_slug: Mapped[str] = mapped_column(ForeignKey("categories.slug", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    search_queries: Mapped[list] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    category: Mapped[Category] = relationship(back_populates="subtopics")


class Creator(Base):
    __tablename__ = "creators"
    __table_args__ = (UniqueConstraint("platform", "external_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(20))  # youtube, tiktok, instagram, web
    external_id: Mapped[str] = mapped_column(String(120))  # p.ej. channel id
    name: Mapped[str] = mapped_column(String(160))
    handle: Mapped[str] = mapped_column(String(160), default="")
    url: Mapped[str] = mapped_column(String(500), default="")
    avatar_url: Mapped[str] = mapped_column(String(500), default="")
    category_slug: Mapped[str | None] = mapped_column(ForeignKey("categories.slug"), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="es")
    # approved: entra al feed · suggested: propuesto por la IA · rejected/muted: fuera
    status: Mapped[str] = mapped_column(String(20), default="approved", index=True)
    origin: Mapped[str] = mapped_column(String(20), default="seed")  # seed, ai, user
    reason: Mapped[str] = mapped_column(Text, default="")
    credibility: Mapped[float] = mapped_column(Float, default=0.7)
    etag: Mapped[str] = mapped_column(String(200), default="")
    last_modified: Mapped[str] = mapped_column(String(100), default="")
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetch_errors: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Source(Base):
    """Fuentes no-creador: RSS de medios, blogs, revistas científicas."""

    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), default="rss")
    name: Mapped[str] = mapped_column(String(160))
    url: Mapped[str] = mapped_column(String(500), unique=True)
    category_slug: Mapped[str | None] = mapped_column(ForeignKey("categories.slug"), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="es")
    credibility: Mapped[float] = mapped_column(Float, default=0.75)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    etag: Mapped[str] = mapped_column(String(200), default="")
    last_modified: Mapped[str] = mapped_column(String(100), default="")
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetch_errors: Mapped[int] = mapped_column(Integer, default=0)


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        UniqueConstraint("platform", "external_id"),
        Index("ix_items_status_cat", "status", "category_slug"),
        Index("ix_items_published", "published_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(20))  # youtube, tiktok, instagram, vimeo, article
    external_id: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(String(1000))
    embed_url: Mapped[str] = mapped_column(String(1000), default="")
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")
    author_name: Mapped[str] = mapped_column(String(200), default="")
    creator_id: Mapped[int | None] = mapped_column(
        ForeignKey("creators.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"), nullable=True
    )
    thumbnail_url: Mapped[str] = mapped_column(String(1000), default="")
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    format: Mapped[str] = mapped_column(String(10), default="long")  # short, long, article
    language: Mapped[str] = mapped_column(String(8), default="es")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    origin: Mapped[str] = mapped_column(String(20), default="seed")  # seed, rss, search, user

    # Resultado del agente analista
    category_slug: Mapped[str | None] = mapped_column(ForeignKey("categories.slug"), nullable=True)
    subtopic_slug: Mapped[str | None] = mapped_column(String(60), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    key_points: Mapped[list] = mapped_column(JSON, default=list)
    quality: Mapped[float] = mapped_column(Float, default=0.5)
    credibility: Mapped[float] = mapped_column(Float, default=0.6)
    is_news: Mapped[bool] = mapped_column(Boolean, default=False)
    clickbait: Mapped[bool] = mapped_column(Boolean, default=False)
    analysis: Mapped[str] = mapped_column(String(20), default="pending")  # pending, heuristic, claude
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, broken, hidden


class ItemState(Base):
    """Relación del usuario con un ítem: like, guardado, visto, nota."""

    __tablename__ = "item_state"
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), primary_key=True)
    liked: Mapped[bool] = mapped_column(Boolean, default=False)
    saved: Mapped[bool] = mapped_column(Boolean, default=False)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    collection: Mapped[str] = mapped_column(String(80), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    seen_count: Mapped[int] = mapped_column(Integer, default=0)
    watch_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    saved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    item: Mapped[Item] = relationship(lazy="joined")


class Interaction(Base):
    __tablename__ = "interactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    value: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Affinity(Base):
    """Preferencias aprendidas: cat:<slug>, sub:<slug>, creator:<id>, tag:<texto>."""

    __tablename__ = "affinities"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    events: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FeedCommand(Base):
    __tablename__ = "feed_commands"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    parsed: Mapped[dict] = mapped_column(JSON, default=dict)
    parser: Mapped[str] = mapped_column(String(20), default="heuristic")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON)


class UsageDay(Base):
    __tablename__ = "usage_days"
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    seconds: Mapped[float] = mapped_column(Float, default=0.0)
    items_viewed: Mapped[int] = mapped_column(Integer, default=0)
    by_category: Mapped[dict] = mapped_column(JSON, default=dict)
    extra_minutes: Mapped[int] = mapped_column(Integer, default=0)  # "dame 10 minutos más"


class Highlight(Base):
    __tablename__ = "highlights"
    __table_args__ = (UniqueConstraint("day", "item_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"))
    rank: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text, default="")

    item: Mapped[Item] = relationship(lazy="joined")


class DailyDigest(Base):
    __tablename__ = "daily_digests"
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    headline: Mapped[str] = mapped_column(String(300), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    generator: Mapped[str] = mapped_column(String(20), default="heuristic")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgentRun(Base):
    """Registro de ejecuciones de los agentes, visible en la app (transparencia)."""

    __tablename__ = "agent_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent: Mapped[str] = mapped_column(String(30))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
