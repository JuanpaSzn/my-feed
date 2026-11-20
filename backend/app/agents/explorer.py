"""AGENTE EXPLORADOR: busca contenido en fuentes autorizadas.

Fuentes (todas oficiales, sin scraping ni descargas de vídeo):
- RSS público de cada canal de YouTube aprobado (no necesita clave).
- RSS de medios, blogs y revistas científicas.
- YouTube Data API v3 (opcional, con clave): duraciones y búsquedas por subtema.
- oEmbed de YouTube, TikTok y Vimeo para los enlaces que añades a mano.

Es eficiente a propósito: GET condicionales (ETag / Last-Modified), concurrencia
limitada, refresco de cada fuente solo cuando toca y tope de cuota diaria.
"""
import asyncio
import calendar
import logging
import re
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, quote, urlparse

import feedparser
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..cache import get_cache
from ..config import get_settings
from ..models import AppSetting, Creator, Item, Source, utcnow
from ..taxonomy import CATEGORIES
from ..text import clean_description, normalize

log = logging.getLogger("myfeed.explorer")
UA = "MyFeed/1.0 (+personal learning feed)"

YT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def http_client() -> httpx.AsyncClient:
    s = get_settings()
    return httpx.AsyncClient(
        timeout=s.http_timeout_seconds,
        headers={"User-Agent": UA},
        follow_redirects=True,
        limits=httpx.Limits(max_connections=s.network_concurrency, max_keepalive_connections=2),
    )


def _dt(struct) -> datetime | None:
    if not struct:
        return None
    return datetime.fromtimestamp(calendar.timegm(struct), tz=timezone.utc)


def _as_aware(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def iso8601_duration(value: str) -> int | None:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not m:
        return None
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def youtube_format(duration: int | None, title: str = "", link: str = "") -> str:
    if "/shorts/" in link:
        return "short"
    if duration is not None:
        if duration <= 70:
            return "short"
        if duration <= 180 and "#short" in title.lower():
            return "short"
        return "long"
    return "short" if "#short" in title.lower() else "long"


# ------------------------------------------------------------ enlaces ------

def parse_link(url: str) -> dict | None:
    """Reconoce un enlace y devuelve plataforma, id y URL de reproducción integrada."""
    url = url.strip()
    if not re.match(r"^https?://", url):
        url = "https://" + url
    u = urlparse(url)
    host = (u.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    path = u.path.rstrip("/")
    if host in ("youtube.com", "music.youtube.com", "youtube-nocookie.com"):
        vid = parse_qs(u.query).get("v", [None])[0]
        fmt = "long"
        if not vid:
            m = re.match(r"^/(shorts|embed|live)/([A-Za-z0-9_-]{11})", path)
            if m:
                vid = m.group(2)
                fmt = "short" if m.group(1) == "shorts" else "long"
        if not vid:
            m = re.match(r"^/(channel)/(UC[A-Za-z0-9_-]{22})", path)
            if m:
                return {"kind": "creator", "platform": "youtube", "external_id": m.group(2), "url": url}
            m = re.match(r"^/@([A-Za-z0-9_.\-]+)", path)
            if m:
                return {"kind": "creator", "platform": "youtube", "handle": m.group(1), "url": url}
            return None
        if vid and YT_ID_RE.match(vid):
            return {"kind": "item", "platform": "youtube", "external_id": vid, "format": fmt,
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "embed_url": f"https://www.youtube-nocookie.com/embed/{vid}"}
    if host == "youtu.be":
        vid = path.lstrip("/")[:11]
        if YT_ID_RE.match(vid):
            return {"kind": "item", "platform": "youtube", "external_id": vid, "format": "long",
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "embed_url": f"https://www.youtube-nocookie.com/embed/{vid}"}
    if host.endswith("tiktok.com"):
        m = re.search(r"/video/(\d+)", path)
        if m:
            return {"kind": "item", "platform": "tiktok", "external_id": m.group(1), "format": "short",
                    "url": url, "embed_url": f"https://www.tiktok.com/embed/v2/{m.group(1)}"}
        m = re.match(r"^/@([A-Za-z0-9_.]+)$", path)
        if m:
            return {"kind": "creator", "platform": "tiktok", "handle": m.group(1), "url": url}
        if host.startswith("vm.") or host.startswith("vt."):
            return {"kind": "item", "platform": "tiktok", "external_id": "", "format": "short", "url": url,
                    "embed_url": "", "needs_resolve": True}
    if host == "instagram.com":
        m = re.match(r"^/(reel|reels|p|tv)/([A-Za-z0-9_-]+)", path)
        if m:
            code = m.group(2)
            return {"kind": "item", "platform": "instagram", "external_id": code, "format": "short",
                    "url": f"https://www.instagram.com/reel/{code}/",
                    "embed_url": f"https://www.instagram.com/reel/{code}/embed"}
        m = re.match(r"^/([A-Za-z0-9_.]+)$", path)
        if m:
            return {"kind": "creator", "platform": "instagram", "handle": m.group(1), "url": url}
    if host == "vimeo.com":
        m = re.match(r"^/(\d+)", path)
        if m:
            return {"kind": "item", "platform": "vimeo", "external_id": m.group(1), "format": "long",
                    "url": url, "embed_url": f"https://player.vimeo.com/video/{m.group(1)}"}
    if host:
        return {"kind": "item", "platform": "article", "external_id": url[:300], "format": "article",
                "url": url, "embed_url": ""}
    return None


OEMBED = {
    "youtube": "https://www.youtube.com/oembed?format=json&url={url}",
    "tiktok": "https://www.tiktok.com/oembed?url={url}",
    "vimeo": "https://vimeo.com/api/oembed.json?url={url}",
}

_META_RE = re.compile(r"<meta[^>]+(?:property|name)=[\"'](og:[a-z:]+|description)[\"'][^>]+content=[\"']([^\"']*)[\"']", re.I)


async def resolve_link(client: httpx.AsyncClient, info: dict) -> dict:
    """Completa título/autor/miniatura vía oEmbed (o etiquetas Open Graph para artículos)."""
    plat = info["platform"]
    out = dict(info)
    try:
        if plat in OEMBED:
            r = await client.get(OEMBED[plat].format(url=quote(info["url"], safe="")))
            if r.status_code == 200:
                d = r.json()
                out.update(title=d.get("title") or "", author_name=d.get("author_name") or "",
                           thumbnail_url=d.get("thumbnail_url") or "", author_url=d.get("author_url") or "")
                if plat == "tiktok" and not out.get("external_id"):
                    vid = str(d.get("embed_product_id") or "")
                    if vid:
                        out["external_id"] = vid
                        out["embed_url"] = f"https://www.tiktok.com/embed/v2/{vid}"
                out["verified"] = True
            elif r.status_code in (400, 401, 403, 404):
                out["verified"] = False
        elif plat in ("article", "instagram"):
            r = await client.get(info["url"])
            if r.status_code == 200 and "html" in r.headers.get("content-type", ""):
                meta = {k.lower(): v for k, v in _META_RE.findall(r.text[:200_000])}
                out.update(title=meta.get("og:title", ""), description=meta.get("og:description", meta.get("description", "")),
                           thumbnail_url=meta.get("og:image", ""), author_name=meta.get("og:site_name", ""))
                out["verified"] = True
    except (httpx.HTTPError, ValueError) as exc:
        log.info("No se pudo resolver %s: %s", info["url"], exc)
    return out


# ------------------------------------------------------------ RSS ----------

async def _conditional_get(client: httpx.AsyncClient, url: str, etag: str, last_mod: str) -> httpx.Response:
    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_mod:
        headers["If-Modified-Since"] = last_mod
    return await client.get(url, headers=headers)


def youtube_feed_entries(xml: bytes | str) -> list[dict]:
    feed = feedparser.parse(xml)
    out = []
    for e in feed.entries[:15]:
        vid = e.get("yt_videoid")
        if not vid:
            continue
        link = e.get("link", "")
        thumb = (e.get("media_thumbnail") or [{}])[0].get("url", "") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
        desc = e.get("summary", "") or (e.get("media_description") or "")
        title = e.get("title", "")
        out.append({
            "platform": "youtube", "external_id": vid,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "embed_url": f"https://www.youtube-nocookie.com/embed/{vid}",
            "title": title, "description": clean_description(desc), "author_name": e.get("author", ""),
            "thumbnail_url": thumb, "published_at": _dt(e.get("published_parsed")),
            "format": youtube_format(None, title, link),
        })
    return out


_IMG_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.I)


def article_feed_entries(xml: bytes | str, limit: int = 20) -> list[dict]:
    feed = feedparser.parse(xml)
    out = []
    for e in feed.entries[:limit]:
        link = e.get("link")
        if not link:
            continue
        thumb = ""
        for key in ("media_thumbnail", "media_content"):
            vals = e.get(key) or []
            if vals and vals[0].get("url"):
                thumb = vals[0]["url"]
                break
        if not thumb:
            for enc in e.get("enclosures", []):
                if enc.get("type", "").startswith("image") and enc.get("href"):
                    thumb = enc["href"]
                    break
        raw = e.get("summary", "") or ""
        if not thumb:
            m = _IMG_RE.search(raw)
            thumb = m.group(1) if m else ""
        info = parse_link(link) or {}
        if info.get("platform") == "youtube":  # algunos feeds enlazan vídeos
            base = {k: info[k] for k in ("platform", "external_id", "url", "embed_url", "format")}
        else:
            base = {"platform": "article", "external_id": link[:300], "url": link, "embed_url": "", "format": "article"}
        out.append({
            **base,
            "title": clean_description(e.get("title", ""), 300),
            "description": clean_description(raw, 900),
            "author_name": e.get("author", "") or feed.feed.get("title", ""),
            "thumbnail_url": thumb,
            "published_at": _dt(e.get("published_parsed") or e.get("updated_parsed")),
        })
    return out


async def upsert_items(session: AsyncSession, rows: list[dict], **common) -> int:
    """Inserta solo lo nuevo. Devuelve cuántos ítems se añadieron."""
    if not rows:
        return 0
    by_platform: dict[str, set[str]] = {}
    for r in rows:
        by_platform.setdefault(r["platform"], set()).add(r["external_id"])
    existing: set[tuple[str, str]] = set()
    for plat, ids in by_platform.items():
        res = await session.execute(
            select(Item.platform, Item.external_id).where(Item.platform == plat, Item.external_id.in_(list(ids)))
        )
        existing.update((p, e) for p, e in res.all())
    added = 0
    seen: set[tuple[str, str]] = set()
    for r in rows:
        key = (r["platform"], r["external_id"])
        if key in existing or key in seen or not r.get("title"):
            continue
        seen.add(key)
        data = {**common, **{k: v for k, v in r.items() if k in Item.__table__.columns.keys()}}
        session.add(Item(**data))
        added += 1
    return added


async def fetch_creator(client: httpx.AsyncClient, cr: Creator) -> list[dict]:
    """Solo red: devuelve filas nuevas. La escritura en BD se hace después, en serie."""
    if cr.platform != "youtube":
        return []
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={cr.external_id}"
    try:
        r = await _conditional_get(client, url, cr.etag, cr.last_modified)
    except httpx.HTTPError as exc:
        log.info("RSS %s falló: %s", cr.name, exc)
        cr.fetch_errors += 1
        return []
    cr.last_fetched_at = utcnow()
    if r.status_code == 304:
        return []
    if r.status_code != 200:
        cr.fetch_errors += 1
        if r.status_code == 404 and cr.fetch_errors >= 3:
            cr.status = "error"
        return []
    cr.fetch_errors = 0
    cr.etag = r.headers.get("etag", "")[:200]
    cr.last_modified = r.headers.get("last-modified", "")[:100]
    return youtube_feed_entries(r.content)


async def fetch_source(client: httpx.AsyncClient, src: Source) -> list[dict]:
    try:
        r = await _conditional_get(client, src.url, src.etag, src.last_modified)
    except httpx.HTTPError as exc:
        log.info("Fuente %s falló: %s", src.name, exc)
        src.fetch_errors += 1
        if src.fetch_errors >= 6:
            src.enabled = False
        return []
    src.last_fetched_at = utcnow()
    if r.status_code == 304:
        return []
    if r.status_code != 200:
        src.fetch_errors += 1
        if src.fetch_errors >= 6:
            src.enabled = False
        return []
    src.fetch_errors = 0
    src.etag = r.headers.get("etag", "")[:200]
    src.last_modified = r.headers.get("last-modified", "")[:100]
    rows = article_feed_entries(r.content)
    # Solo noticias de los últimos 21 días: lo viejo no aporta en un feed de actualidad.
    cutoff = datetime.now(timezone.utc) - timedelta(days=21)
    rows = [x for x in rows if not x["published_at"] or x["published_at"] >= cutoff]
    return rows


# ------------------------------------------------- YouTube Data API --------

YT_API = "https://www.googleapis.com/youtube/v3"


async def _quota_take(units: int) -> bool:
    key = f"yt:quota:{date.today().isoformat()}"
    cache = get_cache()
    used = int(await cache.get(key) or 0)
    # 10 000 unidades/día gratis; nos quedamos muy por debajo.
    limit = get_settings().youtube_daily_search_limit * 100 + 1500
    if used + units > limit:
        return False
    await cache.set(key, str(used + units), ttl=2 * 86400)
    return True


async def youtube_details(client: httpx.AsyncClient, ids: list[str]) -> dict[str, dict]:
    s = get_settings()
    if not s.youtube_api_enabled or not ids:
        return {}
    out: dict[str, dict] = {}
    for start in range(0, len(ids), 50):
        chunk = ids[start : start + 50]
        if not await _quota_take(1):
            break
        try:
            r = await client.get(f"{YT_API}/videos", params={
                "part": "contentDetails,snippet,status", "id": ",".join(chunk), "key": s.youtube_api_key})
        except httpx.HTTPError:
            break
        if r.status_code != 200:
            log.warning("YouTube API videos: %s", r.status_code)
            break
        for v in r.json().get("items", []):
            out[v["id"]] = {
                "duration_sec": iso8601_duration(v.get("contentDetails", {}).get("duration", "")),
                "embeddable": v.get("status", {}).get("embeddable", True),
                "channel_id": v.get("snippet", {}).get("channelId"),
                "channel_title": v.get("snippet", {}).get("channelTitle"),
                "language": (v.get("snippet", {}).get("defaultAudioLanguage") or "")[:2],
            }
    return out


async def youtube_search(client: httpx.AsyncClient, query: str, max_results: int = 12, days: int = 365) -> list[dict]:
    s = get_settings()
    if not s.youtube_api_enabled or not await _quota_take(100):
        return []
    params = {
        "part": "snippet", "q": query, "type": "video", "maxResults": max_results, "key": s.youtube_api_key,
        "safeSearch": "moderate", "videoEmbeddable": "true",
        "publishedAfter": (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    try:
        r = await client.get(f"{YT_API}/search", params=params)
    except httpx.HTTPError:
        return []
    if r.status_code != 200:
        log.warning("YouTube API search: %s %s", r.status_code, r.text[:200])
        return []
    rows = []
    for it in r.json().get("items", []):
        vid = it.get("id", {}).get("videoId")
        sn = it.get("snippet", {})
        if not vid:
            continue
        rows.append({
            "platform": "youtube", "external_id": vid,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "embed_url": f"https://www.youtube-nocookie.com/embed/{vid}",
            "title": clean_description(sn.get("title", ""), 300),
            "description": clean_description(sn.get("description", "")),
            "author_name": sn.get("channelTitle", ""),
            "thumbnail_url": (sn.get("thumbnails", {}).get("high") or sn.get("thumbnails", {}).get("default") or {}).get("url", ""),
            "published_at": datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00")) if sn.get("publishedAt") else None,
            "channel_id": sn.get("channelId", ""),
        })
    return rows


async def enrich_youtube(client: httpx.AsyncClient, session: AsyncSession, limit: int = 200) -> int:
    """Rellena duraciones con la API (1 unidad por cada 50 vídeos) y reclasifica corto/largo."""
    if not get_settings().youtube_api_enabled:
        return 0
    items = (await session.execute(
        select(Item).where(Item.platform == "youtube", Item.duration_sec.is_(None), Item.status == "active").limit(limit)
    )).scalars().all()
    details = await youtube_details(client, [i.external_id for i in items])
    for it in items:
        d = details.get(it.external_id)
        if not d:
            continue
        it.duration_sec = d["duration_sec"]
        it.format = youtube_format(it.duration_sec, it.title, "/shorts/" if it.format == "short" else "")
        if not d["embeddable"]:
            it.status = "broken"
    return len(details)


async def search_and_ingest(client: httpx.AsyncClient, session: AsyncSession, query: str,
                            category: str | None = None, subtopic: str | None = None, days: int = 365) -> int:
    rows = await youtube_search(client, query, days=days)
    if not rows:
        return 0
    known = {c.external_id: c for c in (await session.execute(select(Creator).where(Creator.platform == "youtube"))).scalars()}
    blocked = {k for k, c in known.items() if c.status in ("rejected", "muted")}
    rows = [r for r in rows if r.get("channel_id") not in blocked]
    added = 0
    for r in rows:
        cr = known.get(r.get("channel_id"))
        added += await upsert_items(
            session, [r], creator_id=cr.id if cr else None, category_slug=category, subtopic_slug=subtopic,
            credibility=cr.credibility if cr else 0.55, origin="search",
        )
    await note_candidate_channels(session, rows, category, query, known)
    return added


async def note_candidate_channels(session: AsyncSession, rows: list[dict], category: str | None, query: str,
                                  known: dict[str, Creator]) -> None:
    """Descubrimiento de creadores: un canal que aparece en varias búsquedas se propone para aprobación."""
    setting = await session.get(AppSetting, "candidate_channels")
    data: dict = dict(setting.value) if setting and isinstance(setting.value, dict) else {}
    for r in rows:
        ch = r.get("channel_id")
        if not ch or ch in known:
            continue
        entry = data.get(ch) or {"name": r.get("author_name", ""), "hits": 0, "queries": [], "category": category}
        entry["hits"] += 1
        if query not in entry["queries"]:
            entry["queries"] = (entry["queries"] + [query])[-5:]
        data[ch] = entry
        if entry["hits"] >= 3 and len(entry["queries"]) >= 2:
            cr = Creator(
                platform="youtube", external_id=ch, name=entry["name"][:160] or ch,
                url=f"https://www.youtube.com/channel/{ch}", category_slug=entry.get("category"),
                status="suggested", origin="ai", credibility=0.6, language="es",
                reason=f"Apareció {entry['hits']} veces en búsquedas como «{entry['queries'][0]}».",
            )
            session.add(cr)
            known[ch] = cr
            data.pop(ch, None)
    # Mantener el registro pequeño
    if len(data) > 300:
        data = dict(sorted(data.items(), key=lambda kv: -kv[1]["hits"])[:200])
    if setting:
        setting.value = data
    else:
        session.add(AppSetting(key="candidate_channels", value=data))


# ------------------------------------------------ verificación semilla -----

async def validate_items(client: httpx.AsyncClient, session: AsyncSession, limit: int = 40) -> dict:
    """Verifica vídeos semilla/añadidos con oEmbed y marca los que no existen."""
    setting = await session.get(AppSetting, "validated_items")
    done: list = list(setting.value) if setting and isinstance(setting.value, list) else []
    done_set = set(done)
    items = (await session.execute(
        select(Item).where(Item.platform == "youtube", Item.origin.in_(["seed", "user"]), Item.status == "active")
    )).scalars().all()
    todo = [i for i in items if i.id not in done_set][:limit]
    sem = asyncio.Semaphore(get_settings().network_concurrency)
    stats = {"ok": 0, "broken": 0, "unknown": 0}

    async def check(it: Item):
        async with sem:
            res = await resolve_link(client, {"platform": "youtube", "url": it.url, "external_id": it.external_id})
        v = res.get("verified")
        if v is True:
            it.title = res.get("title") or it.title
            it.author_name = res.get("author_name") or it.author_name
            if res.get("thumbnail_url"):
                it.thumbnail_url = res["thumbnail_url"]
            stats["ok"] += 1
            done.append(it.id)
        elif v is False:
            it.status = "broken"
            stats["broken"] += 1
            done.append(it.id)
        else:
            stats["unknown"] += 1

    await asyncio.gather(*(check(i) for i in todo))
    if setting:
        setting.value = done[-2000:]
    else:
        session.add(AppSetting(key="validated_items", value=done[-2000:]))
    return stats


# ------------------------------------------------------------ orquesta -----

def _due(last: datetime | None, hours: float) -> bool:
    last = _as_aware(last)
    return last is None or last < datetime.now(timezone.utc) - timedelta(hours=hours)


async def _rotate_queries(session: AsyncSession, n: int) -> list[tuple[str, str, str]]:
    """Elige n búsquedas por subtema en rotación, favoreciendo las categorías con más peso."""
    from ..models import Category, Subtopic

    cats = {c.slug: c for c in (await session.execute(select(Category))).scalars()}
    subs = [s for s in (await session.execute(select(Subtopic).where(Subtopic.enabled))).scalars()
            if cats.get(s.category_slug) and cats[s.category_slug].enabled and cats[s.category_slug].weight > 0]
    pool: list[tuple[str, str, str]] = []
    for s in subs:
        for q in s.search_queries or []:
            reps = 2 if cats[s.category_slug].weight >= 1.5 else 1
            pool.extend([(q, s.category_slug, s.slug)] * reps)
    if not pool:
        return []
    setting = await session.get(AppSetting, "search_cursor")
    cur = int(setting.value) if setting else 0
    picked = [pool[(cur + i) % len(pool)] for i in range(min(n, len(pool)))]
    if setting:
        setting.value = cur + n
    else:
        session.add(AppSetting(key="search_cursor", value=n))
    return picked


async def run(session: AsyncSession, force: bool = False, searches: int = 2) -> dict:
    s = get_settings()
    stats = {"creators": 0, "sources": 0, "new_items": 0, "searches": 0, "validated": {}}
    refresh = 0 if force else s.creator_refresh_hours
    creators = [c for c in (await session.execute(select(Creator).where(Creator.status == "approved"))).scalars()
                if _due(c.last_fetched_at, refresh)][:60]
    sources = [x for x in (await session.execute(select(Source).where(Source.enabled))).scalars()
               if _due(x.last_fetched_at, refresh)][:40]
    sem = asyncio.Semaphore(s.network_concurrency)
    async with http_client() as client:
        stats["validated"] = await validate_items(client, session)

        async def guarded(fn, obj):
            async with sem:
                return await fn(client, obj)

        # La red se solapa (con límite); la base de datos se escribe en serie,
        # porque una sesión async no admite operaciones concurrentes.
        targets = [(fetch_creator, c) for c in creators] + [(fetch_source, x) for x in sources]
        results = await asyncio.gather(*(guarded(fn, o) for fn, o in targets), return_exceptions=True)
        for (fn, obj), rows in zip(targets, results):
            if isinstance(rows, Exception):
                log.warning("Explorador: %s", rows)
                continue
            if isinstance(obj, Creator):
                stats["new_items"] += await upsert_items(
                    session, rows, creator_id=obj.id, language=obj.language, credibility=obj.credibility, origin="rss")
            else:
                stats["new_items"] += await upsert_items(
                    session, rows, source_id=obj.id, language=obj.language, credibility=obj.credibility, origin="rss")
        stats["creators"], stats["sources"] = len(creators), len(sources)

        if s.youtube_api_enabled and searches:
            for q, cat, sub in await _rotate_queries(session, searches):
                stats["new_items"] += await search_and_ingest(client, session, q, cat, sub)
                stats["searches"] += 1
        await session.flush()
        await enrich_youtube(client, session)
    await session.commit()
    return stats


def category_slugs() -> list[str]:
    return [c["slug"] for c in CATEGORIES]


__all__ = ["run", "parse_link", "resolve_link", "http_client", "search_and_ingest", "normalize", "category_slugs"]
