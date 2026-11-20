"""Utilidades de texto compartidas por el analista y el parser de comandos."""
import html
import re
import unicodedata

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_URL_RE = re.compile(r"https?://\S+")

STOPWORDS = set(
    """
    a al algo algun alguna algunos ante antes aqui asi aun bajo bien cada como con contra cual cuales cuando de del desde
    donde dos el ella ellas ellos en entre era eres es esa ese eso esta estas este esto estos fue ha hay la las le les lo
    los mas me mi mis mucho muy muestrame muestra muestrenme ensename ensenarme ense quiero quisiera ver videos video
    sobre para pero por que quien se sea ser si sin sobre su sus tambien te tengo tu tus un una uno unos y ya yo
    interesantes interesante importantes importante mejores mejor cosas contenido contenidos dame pon ponme busca buscame
    encuentra encuentrame algo semana hoy esta este mes dias ultimos ultimas recientes nuevos nuevas novedades
    the of and or to in on for with about show me want some best latest new is are what how i my videos video
    conocer saber aprender mostrar mostrarme ensenar enseñame
    """.split()
)


def normalize(text: str) -> str:
    """minúsculas, sin tildes, sin HTML ni URLs, espacios simples."""
    if not text:
        return ""
    text = html.unescape(_TAG_RE.sub(" ", text))
    text = _URL_RE.sub(" ", text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return _WS_RE.sub(" ", text.lower()).strip()


def clean_description(text: str, limit: int = 1200) -> str:
    """Descripción legible: sin HTML, sin enlaces repetidos, recortada."""
    if not text:
        return ""
    text = html.unescape(_TAG_RE.sub(" ", text))
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line or (_URL_RE.fullmatch(line)):
            continue
        lines.append(line)
    out = "\n".join(lines)
    return out[:limit].rstrip() + ("…" if len(out) > limit else "")


def contains_term(norm_text: str, term: str) -> bool:
    """Coincidencia por palabra completa (o frase) sobre texto normalizado."""
    if " " in term or len(term) > 6:
        return term in norm_text
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", norm_text) is not None


def keywords_from(text: str, max_words: int = 8) -> list[str]:
    words = re.findall(r"[a-z0-9][a-z0-9+#.\-]{1,}", normalize(text))
    out: list[str] = []
    for w in words:
        w = w.strip(".-")
        if len(w) < 3 or w in STOPWORDS or w in out:
            continue
        out.append(w)
    return out[:max_words]
