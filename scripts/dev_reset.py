"""Reset local demo data to a known seeded state.

Run:
    uv run python scripts/dev_reset.py
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from sqlalchemy.engine import make_url

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEMO_SEED_ENABLED", "true")
os.environ.setdefault("SECRET_KEY", "dev-seed-secret")

from seed_demo_data import seed_demo_data


def remove_sqlite_database() -> None:
    database_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./plugin_market.db")
    parsed = make_url(database_url)
    if parsed.drivername not in {"sqlite", "sqlite+aiosqlite"}:
        raise RuntimeError("dev_reset only supports deleting local SQLite databases")

    database = parsed.database
    if not database or database == ":memory:":
        return

    database_path = Path(database)
    if not database_path.is_absolute():
        database_path = Path.cwd() / database_path
    database_path.unlink(missing_ok=True)


async def dev_reset() -> None:
    remove_sqlite_database()
    await seed_demo_data()


if __name__ == "__main__":
    asyncio.run(dev_reset())
