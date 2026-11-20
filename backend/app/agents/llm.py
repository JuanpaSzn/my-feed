"""Cliente de Claude compartido por los agentes.

Si no hay ANTHROPIC_API_KEY, `available()` devuelve False y cada agente usa su
versión heurística. Todas las llamadas devuelven None ante cualquier fallo,
para que el feed nunca dependa de la IA.
"""
import logging
from datetime import date
from typing import TypeVar

from pydantic import BaseModel

from ..cache import get_cache
from ..config import get_settings

log = logging.getLogger("myfeed.llm")
T = TypeVar("T", bound=BaseModel)

_client = None


def available() -> bool:
    return get_settings().claude_enabled


def _get_client():
    global _client
    if _client is None:
        import anthropic

        s = get_settings()
        _client = anthropic.AsyncAnthropic(api_key=s.anthropic_api_key, timeout=90.0, max_retries=2)
    return _client


async def budget_left(units: int = 1) -> bool:
    """Tope diario de ítems analizados, para que la factura nunca sorprenda."""
    key = f"llm:budget:{date.today().isoformat()}"
    cache = get_cache()
    used = int(await cache.get(key) or 0)
    if used + units > get_settings().claude_daily_item_limit:
        return False
    await cache.set(key, str(used + units), ttl=2 * 86400)
    return True


async def parse(system: str, user: str, schema: type[T], max_tokens: int = 4000) -> T | None:
    """Una llamada con salida estructurada validada por Pydantic.

    El prompt de sistema es estable y va marcado para caché, de modo que las
    llamadas repetidas del analista pagan solo la parte variable.
    """
    if not available():
        return None
    import anthropic

    s = get_settings()
    try:
        resp = await _get_client().messages.parse(
            model=s.claude_model,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
            output_config={"effort": s.claude_effort},
            output_format=schema,
        )
    except anthropic.RateLimitError as exc:
        log.warning("Claude: límite de peticiones (%s)", exc)
        return None
    except anthropic.APIStatusError as exc:
        log.warning("Claude: error %s %s", exc.status_code, getattr(exc, "message", exc))
        return None
    except anthropic.APIConnectionError as exc:
        log.warning("Claude: sin conexión (%s)", exc)
        return None
    except Exception as exc:  # validación u otros: el agente usa la heurística
        log.warning("Claude: respuesta no utilizable (%s)", exc)
        return None
    if resp.stop_reason == "refusal":
        log.info("Claude declinó la petición; se usa la heurística")
        return None
    return resp.parsed_output
