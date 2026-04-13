# Alembic Migrations

Production deployments should use Alembic for schema management.

Bootstrap:

```
alembic init app/db/migrations
alembic revision --autogenerate -m "init"
alembic upgrade head
```

For local development and tests the app uses `init_models()` from
`app/db/session.py` which calls `Base.metadata.create_all` against the
configured database URL.
