import logging
from contextlib import asynccontextmanager

from app.core.cache import cache_ping, cache_stats, close_redis, init_redis
from app.core.config import get_settings
from app.core.database import init_db
from app.core.monitoring import get_metrics, setup_monitoring
from app.core.ratelimit import limiter
from app.routes import auth, github, issues, maintainer, searches
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi.errors import RateLimitExceeded

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("issuecompass")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("IssueCompass API starting up...")

    config_errors = settings.check_errors()
    if config_errors:
        for err in config_errors:
            logger.error("CONFIG: %s", err)
        logger.warning("CONFIG: %d issue(s) found", len(config_errors))
    else:
        logger.info("CONFIG: all checks passed")

    await init_db()

    try:
        await init_redis()
    except Exception as e:
        logger.warning("Redis init failed: %s", e)

    logger.info("IssueCompass API ready")
    yield

    logger.info("IssueCompass API shutting down")
    try:
        from app.services.ai_service import close_client
        await close_client()
    except Exception:
        pass
    try:
        from app.services.github_service import close_client
        await close_client()
    except Exception:
        pass
    await close_redis()


app = FastAPI(
    title="IssueCompass API",
    description="Match open-source contributors to issues they can actually solve.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)
app.state.config_errors = settings.check_errors()
app.state.limiter = limiter

setup_monitoring(app)

app.add_middleware(GZipMiddleware, minimum_size=1000)


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."},
        headers={"Retry-After": str(exc.retry_after)},
    )

app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)


async def _generic_exception_handler(request: Request, exc: Exception):
    from fastapi.responses import JSONResponse
    logger.error(
        "[%s] Unhandled %s on %s %s: %s",
        getattr(request.state, "request_id", "?"),
        type(exc).__name__,
        request.method,
        request.url.path,
        str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_id": getattr(request.state, "request_id", None)},
    )


app.add_exception_handler(Exception, _generic_exception_handler)

_allowed_raw = settings.ALLOWED_ORIGINS
if settings.ALLOW_ORIGINS:
    _allowed_raw = _allowed_raw + "," + settings.ALLOW_ORIGINS
ALLOWED_ORIGINS = [o.strip() for o in _allowed_raw.split(",") if o.strip()]
if settings.FRONTEND_URL:
    ALLOWED_ORIGINS.append(settings.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(github.router, prefix=API_PREFIX)
app.include_router(issues.router, prefix=API_PREFIX)
app.include_router(searches.router, prefix=API_PREFIX)
app.include_router(maintainer.router, prefix=API_PREFIX)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": "IssueCompass API",
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.head("/", include_in_schema=False)
@app.head("/health", include_in_schema=False)
async def root_head():
    from fastapi.responses import Response
    return Response(status_code=200)


@app.get("/health")
async def health(request: Request):
    errors = list(request.app.state.config_errors)
    req_metrics = get_metrics()

    redis_ok = False
    try:
        redis_ok = await cache_ping()
    except Exception:
        pass

    db_ok = False
    try:
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        logger.warning("Healthcheck DB connection failed: %s", e)

    if not db_ok:
        errors.append("Database connection failed")
    status = "ok"
    if errors:
        status = "degraded"

    result: dict = {
        "status": status,
        "version": settings.APP_VERSION,
        "database": db_ok,
        "redis": redis_ok,
        "ai_enabled": bool(settings.GROQ_API_KEY and settings.AI_ENABLED),
        "metrics": req_metrics,
        "cache": cache_stats(),
    }
    if errors:
        result["config_errors"] = errors
    return result


@app.get("/metrics")
async def metrics(request: Request):
    api_key = request.headers.get("X-Metrics-Key") or request.query_params.get("key")
    expected = settings.METRICS_API_KEY
    if expected and api_key != expected:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=403,
            content={"error": "Forbidden. Set X-Metrics-Key header or METRICS_API_KEY env var."},
        )
    return {
        "requests": get_metrics(),
        "cache": cache_stats(),
    }
