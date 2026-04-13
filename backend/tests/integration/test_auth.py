"""Auth endpoint integration tests."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_register_creates_user(client):
    resp = await client.post("/api/v1/auth/register", json={"email": "a@test.com", "password": "password123"})
    assert resp.status_code == 201
    assert resp.json()["email"] == "a@test.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await client.post("/api/v1/auth/register", json={"email": "dup@test.com", "password": "password123"})
    resp = await client.post("/api/v1/auth/register", json={"email": "dup@test.com", "password": "password123"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_returns_token(client):
    await client.post("/api/v1/auth/register", json={"email": "b@test.com", "password": "password123"})
    resp = await client.post("/api/v1/auth/login", json={"email": "b@test.com", "password": "password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={"email": "c@test.com", "password": "password123"})
    resp = await client.post("/api/v1/auth/login", json={"email": "c@test.com", "password": "wrongpass"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_with_token(client):
    await client.post("/api/v1/auth/register", json={"email": "d@test.com", "password": "password123"})
    login = await client.post("/api/v1/auth/login", json={"email": "d@test.com", "password": "password123"})
    token = login.json()["access_token"]
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "d@test.com"
