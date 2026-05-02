"""Convenient local seed entrypoint.

Run:
    uv run python scripts/dev_seed.py
"""
from __future__ import annotations

import asyncio
import os

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEMO_SEED_ENABLED", "true")
os.environ.setdefault("SECRET_KEY", "dev-seed-secret")

from seed_demo_data import seed_demo_data


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
