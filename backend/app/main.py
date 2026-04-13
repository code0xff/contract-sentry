"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from app.api.v1.router import api_router
from app.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.metrics import REGISTRY
from app.db.session import SessionLocal, engine, init_models

configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_models()
    except Exception as exc:  # pragma: no cover
        log.warning("init_models_failed", error=str(exc))
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(api_router)

    @app.get("/health/live", tags=["health"])
    async def live() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/health/ready", tags=["health"])
    async def ready() -> Response:
        checks: dict[str, str] = {}
        ready_ok = True

        # DB probe
        try:
            async with SessionLocal() as session:
                await session.execute(text("SELECT 1"))
            checks["db"] = "ok"
        except Exception as exc:
            checks["db"] = f"error: {exc}"
            ready_ok = False

        # Redis probe (optional)
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(settings.redis_url)
            await client.ping()
            await client.aclose()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"
            # Redis non-fatal for readiness in dev; flip below to True for strict
            # ready_ok = False

        import json as _json

        return Response(
            content=_json.dumps({"status": "ready" if ready_ok else "not_ready", "checks": checks}),
            media_type="application/json",
            status_code=200 if ready_ok else 503,
        )

    @app.get("/metrics", tags=["health"])
    async def metrics() -> Response:
        return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
