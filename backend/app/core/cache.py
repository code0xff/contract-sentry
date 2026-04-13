"""Redis-backed analysis result cache keyed by bytecode hash + tools."""
from __future__ import annotations

import hashlib
import logging

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)


def make_cache_key(bytecode: str, tools: list[str]) -> str:
    """SHA-256 of bytecode + sorted tool list."""
    payload = bytecode + "|" + ",".join(sorted(tools))
    return "analysis_cache:" + hashlib.sha256(payload.encode()).hexdigest()


async def get_cached_job_id(bytecode: str, tools: list[str]) -> str | None:
    """Return cached job_id or None if not cached / Redis unavailable."""
    try:
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        async with client:
            return await client.get(make_cache_key(bytecode, tools))
    except Exception:
        logger.warning("cache lookup failed", exc_info=True)
        return None


async def set_cached_job_id(bytecode: str, tools: list[str], job_id: str) -> None:
    """Store job_id in cache with TTL. Silently fails if Redis unavailable."""
    try:
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        async with client:
            await client.setex(make_cache_key(bytecode, tools), settings.analysis_cache_ttl, job_id)
    except Exception:
        logger.warning("cache store failed", exc_info=True)
