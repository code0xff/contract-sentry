#!/bin/sh
set -e

python3 - <<'PYEOF'
import asyncio, os, subprocess, sys

async def check():
    import asyncpg
    url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url)
    try:
        has_alembic = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version')"
        )
        if not has_alembic:
            has_users = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"
            )
            if has_users:
                print("Existing untracked DB — stamping to 0002", flush=True)
                subprocess.run(["alembic", "stamp", "0002"], check=True)
    finally:
        await conn.close()

asyncio.run(check())
PYEOF

echo "Running migrations..."
alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
