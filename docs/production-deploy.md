# Production Deploy

This guide describes the lightweight production shape for the N.E.K.O Plugin
Market. It keeps SQLite as the primary database for portability, but treats it
as production data: persistent volume, online backup, restore drill, and
explicit migrations.

## Topology

```text
Internet
  -> Caddy (:80/:443)
    -> frontend (nginx static dist)
    -> backend (FastAPI /api/* and /health)

backend
  -> /data/plugin_market.db
  -> Alembic migrations
```

## First Deploy

1. Create the production environment file:

```bash
cp .env.production.example .env.production
```

2. Edit `.env.production`:

- Set `SECRET_KEY` to a strong random value.
- Set `INITIAL_ADMIN_PASSWORD` before first start.
- Set `MARKET_SITE_ADDRESS` to your domain, for example `market.example.com`.
- Set `FRONTEND_BASE_URL` and `ALLOWED_HOSTS` to the public origin.

Example:

```env
MARKET_SITE_ADDRESS=market.example.com
MARKET_HTTP_PORT=80
MARKET_HTTPS_PORT=443
FRONTEND_BASE_URL=https://market.example.com
ALLOWED_HOSTS=["https://market.example.com"]
DATABASE_URL=sqlite+aiosqlite:////data/plugin_market.db
DEV_AUTO_CREATE_TABLES=false
```

For a local smoke test without binding privileged ports, keep
`MARKET_SITE_ADDRESS=:80` and override only the host ports:

```env
MARKET_HTTP_PORT=18080
MARKET_HTTPS_PORT=18443
FRONTEND_BASE_URL=http://localhost:18080
ALLOWED_HOSTS=["http://localhost:18080"]
```

3. Build and start:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

The `migrate` service runs `alembic upgrade head` before the backend starts.

## Backup

Run an online SQLite backup without stopping the backend:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm backup
```

The backup is written to the `market_backups` volume as:

```text
plugin_market-YYYYMMDD-HHMMSS.db.gz
plugin_market-YYYYMMDD-HHMMSS.db.gz.sha256
```

To copy backups out of Docker:

```bash
docker run --rm \
  -v neko_plugin_py_market_backups:/backups:ro \
  -v "$PWD/backups:/out" \
  alpine sh -c 'cp -a /backups/. /out/'
```

Adjust the volume name if your Compose project name differs.

## Restore

Restore requires stopping the backend so no process writes the database while it
is replaced:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml stop backend
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm \
  -v "$PWD/backups:/restore:ro" \
  backend python scripts/restore_sqlite.py \
    /restore/plugin_market-YYYYMMDD-HHMMSS.db.gz --force
docker compose --env-file .env.production -f docker-compose.prod.yml up -d
```

After restore, verify:

```bash
curl -fsS https://market.example.com/health
```

## Moving Servers

Bring these items to the new server:

- `.env.production`
- `docker-compose.prod.yml`
- the current backup file from `market_backups`
- optional Caddy data if you want to preserve existing certificates

On the new server:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml build
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm \
  -v "$PWD/backups:/restore:ro" \
  backend python scripts/restore_sqlite.py \
    /restore/plugin_market-YYYYMMDD-HHMMSS.db.gz --force
docker compose --env-file .env.production -f docker-compose.prod.yml up -d
```

## Notes

- Keep `ENVIRONMENT=production`; development auto-create is intentionally off.
- Do not use `docker-compose.yml` for production. It runs dev servers and mounts
  source code into containers.
- SQLite is fine for this stage because the operational goal is portability and
  recoverability, not high write concurrency.
- If the service later needs multiple backend replicas or heavier write load,
  switch `DATABASE_URL` to PostgreSQL and add `asyncpg`.
