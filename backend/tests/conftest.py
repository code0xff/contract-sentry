"""Shared test fixtures."""
from __future__ import annotations

import asyncio
import os
import tempfile
import uuid
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio

_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_db_file.close()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_file.name}"
os.environ["CELERY_BROKER_URL"] = "memory://"
os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def app_instance():
    from app.db.session import init_models

    await init_models()
    from app.main import create_app

    return create_app()


@pytest_asyncio.fixture
async def client(app_instance) -> AsyncIterator:
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client) -> dict[str, str]:
    email = f"test-{uuid.uuid4()}@example.com"
    password = "password123"
    register = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert register.status_code == 201
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
