from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def commit_or_rollback(db: AsyncSession) -> AsyncIterator[None]:
    try:
        yield
        await db.commit()
    except Exception:
        await db.rollback()
        raise
