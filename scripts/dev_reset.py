"""Reset local demo data to a known seeded state.

Run:
    uv run python scripts/dev_reset.py
"""
from __future__ import annotations

import asyncio
import os

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEMO_SEED_ENABLED", "true")
os.environ.setdefault("SECRET_KEY", "dev-seed-secret")

from clear_demo_data import clear_demo_data
from seed_demo_data import seed_demo_data


async def dev_reset() -> None:
    await clear_demo_data()
    await seed_demo_data()


if __name__ == "__main__":
    asyncio.run(dev_reset())
