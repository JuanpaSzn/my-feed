"""Configuración central. Todo se lee de variables de entorno (o .env).

Ninguna clave es obligatoria: sin claves la app funciona con datos semilla,
RSS públicos y análisis heurístico.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Infraestructura
    database_url: str = "sqlite+aiosqlite:///./myfeed.db"
    redis_url: str = ""  # vacío = caché en memoria
    app_token: str = ""  # si se define, la API exige la cabecera X-App-Token
    cors_origins: str = "*"
    timezone: str = "America/Bogota"

    # Claves opcionales
    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-5-5"
    claude_effort: str = "low"
    claude_daily_item_limit: int = 300  # máximo de ítems analizados por Claude al día
    youtube_api_key: str = ""
    youtube_daily_search_limit: int = 20  # cada búsqueda cuesta 100 unidades de cuota

    # Planificador
    scheduler_enabled: bool = True
    discovery_interval_minutes: int = 90
    creator_refresh_hours: int = 6
    highlights_hour: int = 6  # hora local para generar los destacados del día
    network_concurrency: int = 4
    http_timeout_seconds: float = 12.0

    # Datos
    seed_on_start: bool = True
    keep_unseen_days: int = 120

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def claude_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def youtube_api_enabled(self) -> bool:
        return bool(self.youtube_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
