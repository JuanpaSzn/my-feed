"""Comandos escritos: «Muéstrame los últimos avances en agentes autónomos».

Convierte una frase en un filtro temporal del feed (categorías, subtemas,
palabras clave, formato, antigüedad). Con Claude se entiende mejor el matiz;
sin Claude, un parser por vocabulario funciona sorprendentemente bien en español.
"""
import re
from typing import Literal

from pydantic import BaseModel, Field

from ..taxonomy import CATEGORIES, TIME_WORDS
from ..text import contains_term, keywords_from, normalize
from . import llm

_CAT_ALIASES = {
    "deporte": ["deporte", "deportes", "futbol", "futsal", "fútbol", "gym", "gimnasio", "entrenar", "entrenamiento",
                "rendimiento", "velocidad", "aceleracion", "nutricion", "musculo", "lesiones"],
    "ciberseguridad": ["ciberseguridad", "seguridad informatica", "hacking", "hacker", "pentesting", "ciber",
                       "cybersecurity", "vulnerabilidades", "exploits", "ctf"],
    "ia": ["ia", "inteligencia artificial", "ai", "llm", "agentes", "agentes autonomos", "machine learning", "modelos"],
    "programacion": ["programacion", "programar", "codigo", "python", "desarrollo", "software", "tecnologia",
                     "open source", "hardware", "videojuegos", "emulacion", "frameworks"],
    "mente": ["psicologia", "filosofia", "introspeccion", "autoconocimiento", "emociones", "inteligencia emocional",
              "estoicismo", "reflexiones", "mente", "habitos"],
    "ciencia": ["ciencia", "cientificos", "descubrimientos", "espacio", "nasa", "inventos", "fisica", "biologia",
                "astronomia", "mundo", "innovacion"],
}
_SUBS = {sub[0]: (cat["slug"], [normalize(k) for k in sub[2]] + [normalize(sub[1])]) for cat in CATEGORIES for sub in cat["subtopics"]}
_FORMAT_WORDS = {
    "short": ["cortos", "corto", "shorts", "reels", "rapidos", "breves", "tiktoks"],
    "long": ["largos", "largo", "documentales", "documental", "charlas", "conferencias", "podcast", "a fondo", "en profundidad"],
    "article": ["articulos", "articulo", "noticias", "leer", "lecturas", "blogs", "papers"],
}


class ParsedCommand(BaseModel):
    label: str = Field(description="título corto en español para mostrar, máx 40 caracteres")
    categories: list[Literal["deporte", "ciberseguridad", "ia", "programacion", "mente", "ciencia"]]
    subtopics: list[str] = Field(description="slugs de subtemas de la taxonomía, puede estar vacío")
    keywords: list[str] = Field(description="2-6 palabras clave en español o inglés para buscar")
    search_query: str = Field(description="consulta concisa para buscar vídeos en YouTube")
    format: Literal["all", "short", "long", "article"]
    max_age_days: int | None = Field(description="null si la antigüedad no importa")
    duration_minutes: int = Field(description="cuánto debe durar el modo enfoque, 30-240")


def _label(text: str) -> str:
    t = re.sub(r"^(muestrame|muéstrame|quiero|ensename|enséñame|dame|ponme|busca|búscame|quisiera)\s+", "", text.strip(), flags=re.I)
    t = t.rstrip(".!?¿¡")
    return (t[:1].upper() + t[1:])[:40] if t else "Tu búsqueda"


def heuristic_parse(text: str) -> dict:
    nt = normalize(text)
    cats: list[str] = []
    for slug, aliases in _CAT_ALIASES.items():
        if any(contains_term(nt, normalize(a)) for a in aliases):
            cats.append(slug)
    explicit = list(cats)
    subs: list[str] = []
    for sub, (cat, kws) in _SUBS.items():
        if explicit and cat not in explicit:
            continue  # si nombras la categoría, los subtemas de otras no cuentan
        hits = sum(1 for k in kws if len(k) > 3 and contains_term(nt, k))
        if hits:
            subs.append(sub)
            if cat not in cats:
                cats.append(cat)
    fmt = "all"
    for f, words in _FORMAT_WORDS.items():
        if any(contains_term(nt, w) for w in words):
            fmt = f
            break
    age = None
    for phrase, days in sorted(TIME_WORDS.items(), key=lambda kv: -len(kv[0])):
        if contains_term(nt, phrase):
            age = days
            break
    format_words = {w for ws in _FORMAT_WORDS.values() for w in ws}
    kws = [k for k in keywords_from(text, 8) if k not in format_words and k not in TIME_WORDS]
    return {
        "label": _label(text),
        "categories": cats[:3],
        "subtopics": subs[:4],
        "keywords": kws[:6],
        "search_query": " ".join(kws[:5]) or text[:80],
        "format": fmt,
        "max_age_days": age,
        "duration_minutes": 90,
    }


SYSTEM = (
    "Eres el intérprete de comandos de MyFeed, un feed personal de vídeos para aprender. "
    "El usuario escribe lo que quiere ver y tú lo traduces a un filtro. Usa solo estas categorías y subtemas:\n"
    + "\n".join(f"- {c['slug']}: " + ", ".join(s[0] for s in c["subtopics"]) for c in CATEGORIES)
    + "\nSi pide algo de actualidad ('últimos', 'esta semana'), pon max_age_days. "
    "Las palabras clave deben servir para encontrar el contenido en títulos (incluye sinónimos en inglés si ayuda)."
)


async def parse_command(text: str) -> tuple[dict, str]:
    """Devuelve (filtro, parser usado)."""
    text = text.strip()[:400]
    if llm.available() and await llm.budget_left(1):
        res = await llm.parse(SYSTEM, text, ParsedCommand, max_tokens=1500)
        if res:
            d = res.model_dump()
            d["subtopics"] = [s for s in d["subtopics"] if s in _SUBS]
            d["duration_minutes"] = max(15, min(240, d["duration_minutes"] or 90))
            d["label"] = d["label"][:40] or _label(text)
            return d, "claude"
    return heuristic_parse(text), "heuristic"
