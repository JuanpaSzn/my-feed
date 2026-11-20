import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from . import scheduler
from .cache import get_cache
from .config import get_settings
from .db import SessionLocal, init_db
from .routers import feed, library, me
from .seed import seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("myfeed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    await init_db()
    if s.seed_on_start:
        async with SessionLocal() as session:
            stats = await seed(session)
        log.info("Semilla: %s", stats)
    task = stop = None
    if s.scheduler_enabled:
        task, stop = scheduler.start()
    log.info("MyFeed listo · Claude=%s · YouTube API=%s · Redis=%s",
             s.claude_enabled, s.youtube_api_enabled, bool(s.redis_url))
    yield
    if stop:
        stop.set()
        task.cancel()
    await get_cache().close()


async def require_token(request: Request):
    token = get_settings().app_token
    if not token:
        return
    given = request.headers.get("x-app-token") or request.query_params.get("token") or ""
    if not secrets.compare_digest(given, token):
        raise HTTPException(401, "Token de la app incorrecto")


app = FastAPI(title="MyFeed API", version="1.0.0", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=800)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)
for r in (feed.router, library.router, me.router):
    app.include_router(r, dependencies=[Depends(require_token)])


@app.get("/health")
async def health():
    return {"ok": True, "cache": await get_cache().ping()}
