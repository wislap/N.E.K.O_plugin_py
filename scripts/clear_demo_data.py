"""Remove demo users, plugins, and review artifacts."""
from __future__ import annotations

import asyncio

from sqlalchemy import delete, select

from demo_data import (
    DEMO_EMAIL_DOMAIN,
    DEMO_PLUGIN_SLUG_PREFIX,
    LEGACY_DEMO_EMAIL_DOMAINS,
    assert_demo_seed_allowed,
)

from app.core.database import AsyncSessionLocal, engine
from app.models import (
    Notification,
    Plugin,
    PluginCategory,
    PluginRating,
    Review,
    User,
    Version,
)


async def clear_demo_data() -> None:
    assert_demo_seed_allowed()

    async with AsyncSessionLocal() as db:
        plugin_result = await db.execute(
            select(Plugin.id).where(Plugin.slug.like(f"{DEMO_PLUGIN_SLUG_PREFIX}%"))
        )
        plugin_ids = list(plugin_result.scalars().all())
        demo_domains = [DEMO_EMAIL_DOMAIN, *LEGACY_DEMO_EMAIL_DOMAINS]
        user_ids = []
        for domain in demo_domains:
            user_result = await db.execute(
                select(User.id).where(User.email.like(f"%@{domain}"))
            )
            user_ids.extend(user_result.scalars().all())
        user_ids = list(dict.fromkeys(user_ids))

        if plugin_ids:
            await db.execute(delete(PluginRating).where(PluginRating.plugin_id.in_(plugin_ids)))
            await db.execute(delete(Review).where(Review.plugin_id.in_(plugin_ids)))
            await db.execute(delete(Version).where(Version.plugin_id.in_(plugin_ids)))
            await db.execute(delete(PluginCategory).where(PluginCategory.plugin_id.in_(plugin_ids)))
            await db.execute(delete(Plugin).where(Plugin.id.in_(plugin_ids)))

        if user_ids:
            await db.execute(delete(Notification).where(Notification.user_id.in_(user_ids)))

        for domain in demo_domains:
            await db.execute(delete(User).where(User.email.like(f"%@{domain}")))
        await db.commit()

    print(f"Demo data cleared. Removed {len(plugin_ids)} demo plugins and {len(user_ids)} demo users.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(clear_demo_data())
