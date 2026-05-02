"""Seed semi-real demo users, plugins, and review states."""
from __future__ import annotations

import asyncio

from sqlalchemy import delete, select

from demo_data import (
    DEFAULT_CATEGORIES,
    DEFAULT_ZONES,
    DEMO_PASSWORD,
    DEMO_NOTIFICATIONS,
    DEMO_PLUGINS,
    DEMO_REVIEWS,
    DEMO_USERS,
    assert_demo_seed_allowed,
)

from app.core.config import settings
from app.core.database import AsyncSessionLocal, Base, engine
from app.core.security import get_password_hash
from app.core.time import utc_now
from app.models import (
    Category,
    Notification,
    Plugin,
    PluginCategory,
    PluginRating,
    PluginReview,
    PluginReviewHistory,
    PluginStatus,
    RatingGrade,
    Review,
    ReviewStage,
    User,
    Version,
    Zone,
)
from app.services.bootstrap_service import BootstrapService
from app.services.permission_service import PermissionService


def status_from_value(value: str) -> PluginStatus:
    return PluginStatus(value)


def review_stage_for_status(status: PluginStatus) -> ReviewStage:
    if status == PluginStatus.APPROVED:
        return ReviewStage.APPROVED
    if status == PluginStatus.REJECTED:
        return ReviewStage.REJECTED
    if status == PluginStatus.DISABLED:
        return ReviewStage.APPROVED
    return ReviewStage.SUBMITTED


async def get_or_create_zone(db, zone_data: dict) -> Zone:
    result = await db.execute(select(Zone).where(Zone.slug == zone_data["slug"]))
    zone = result.scalar_one_or_none()
    if zone:
        return zone

    zone = Zone(**zone_data)
    db.add(zone)
    await db.flush()
    return zone


async def get_or_create_category(db, category_data: dict) -> Category:
    result = await db.execute(select(Category).where(Category.slug == category_data["slug"]))
    category = result.scalar_one_or_none()
    if category:
        return category

    category = Category(**category_data)
    db.add(category)
    await db.flush()
    return category


async def upsert_user(db, user_data: dict) -> User:
    result = await db.execute(select(User).where(User.username == user_data["username"]))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            username=user_data["username"],
            email=user_data["email"],
            hashed_password=get_password_hash(DEMO_PASSWORD),
            display_name=user_data["display_name"],
            bio=user_data["bio"],
            is_admin=user_data["is_admin"],
            is_active=True,
            must_change_password=False,
        )
        db.add(user)
        await db.flush()
        return user

    user.email = user_data["email"]
    user.hashed_password = get_password_hash(DEMO_PASSWORD)
    user.display_name = user_data["display_name"]
    user.bio = user_data["bio"]
    user.is_admin = user_data["is_admin"]
    user.is_active = True
    user.must_change_password = False
    return user


async def upsert_root_admin(db) -> User:
    result = await db.execute(select(User).where(User.username == settings.INITIAL_ADMIN_USERNAME))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(username=settings.INITIAL_ADMIN_USERNAME)
        db.add(user)

    user.email = settings.INITIAL_ADMIN_EMAIL
    user.hashed_password = get_password_hash(settings.INITIAL_ADMIN_PASSWORD)
    user.display_name = user.display_name or "Root"
    user.is_admin = True
    user.is_active = True
    user.must_change_password = True
    await db.flush()
    return user


async def remove_existing_plugin_artifacts(db, plugin: Plugin) -> None:
    await db.execute(delete(PluginReviewHistory).where(PluginReviewHistory.plugin_id == plugin.id))
    await db.execute(delete(PluginReview).where(PluginReview.plugin_id == plugin.id))
    await db.execute(delete(PluginRating).where(PluginRating.plugin_id == plugin.id))
    await db.execute(delete(Review).where(Review.plugin_id == plugin.id))
    await db.execute(delete(Version).where(Version.plugin_id == plugin.id))
    await db.execute(delete(PluginCategory).where(PluginCategory.plugin_id == plugin.id))


async def upsert_plugin(db, plugin_data: dict, users: dict[str, User], zones: dict[str, Zone], categories: dict[str, Category]) -> Plugin:
    result = await db.execute(select(Plugin).where(Plugin.slug == plugin_data["slug"]))
    plugin = result.scalar_one_or_none()
    author = users[plugin_data["author"]]
    status = status_from_value(plugin_data["status"])
    now = utc_now()

    if plugin is None:
        plugin = Plugin(slug=plugin_data["slug"], author_id=author.id, author_name=author.username)
        db.add(plugin)
    else:
        await remove_existing_plugin_artifacts(db, plugin)

    plugin.name = plugin_data["name"]
    plugin.short_description = plugin_data["short_description"]
    plugin.description = plugin_data["description"]
    plugin.version = "1.0.0"
    plugin.author_id = author.id
    plugin.author_name = author.username
    plugin.download_url = f"{plugin_data['repo']}/releases/latest/download/plugin.zip"
    plugin.icon_url = None
    plugin.repo_url = plugin_data["repo"]
    plugin.repo_branch = "main"
    plugin.readme = (
        f"# {plugin_data['name']}\n\n"
        f"{plugin_data['description']}\n\n"
        "## Install\n\n"
        "Download the latest release and place it in the N.E.K.O plugins directory.\n"
    )
    plugin.zone_id = zones[plugin_data["zone"]].id
    plugin.tags = plugin_data["tags"]
    plugin.download_count = plugin_data["download_count"]
    plugin.likes = plugin_data["likes"]
    plugin.rating_average = plugin_data["rating_average"]
    plugin.rating_count = plugin_data["rating_count"]
    plugin.status = status
    plugin.is_featured = 1 if status == PluginStatus.APPROVED else 0
    plugin.published_at = now if status in {PluginStatus.APPROVED, PluginStatus.DISABLED} else None

    await db.flush()
    for category_slug in plugin_data["categories"]:
        db.add(
            PluginCategory(
                plugin_id=plugin.id,
                category_id=categories[category_slug].id,
            )
        )

    stage = review_stage_for_status(status)
    reviewer = users["reviewer"]
    completed = status in {PluginStatus.APPROVED, PluginStatus.REJECTED, PluginStatus.DISABLED}
    review = PluginReview(
        plugin_id=plugin.id,
        repo_url=plugin.repo_url,
        repo_branch=plugin.repo_branch,
        stage=stage,
        ai_score=plugin_data["ai_score"],
        ai_recommendation=plugin_data["ai_recommendation"],
        review_feedback=plugin_data["review_note"] or None,
        manual_reviewer_id=reviewer.id if completed else None,
        manual_review_notes=plugin_data["review_note"] or None,
        submitted_at=now,
        ai_reviewed_at=now,
        manual_reviewed_at=now if completed else None,
        completed_at=now if completed else None,
    )
    db.add(review)
    await db.flush()

    db.add(
        PluginReviewHistory(
            plugin_id=plugin.id,
            review_id=review.id,
            from_stage=None,
            to_stage=ReviewStage.SUBMITTED.value,
            notes="Demo seed: 插件提交审核",
            operator_id=author.id,
            operator_type="user",
        )
    )
    if completed:
        db.add(
            PluginReviewHistory(
                plugin_id=plugin.id,
                review_id=review.id,
                from_stage=ReviewStage.SUBMITTED.value,
                to_stage=stage.value,
                notes=f"Demo seed: {plugin_data['review_note']}",
                operator_id=reviewer.id,
                operator_type="user",
            )
        )

    db.add(
        Version(
            plugin_id=plugin.id,
            version="1.0.0",
            changelog="Demo seed initial version.",
            download_url=plugin.download_url,
            min_app_version="1.0.0",
        )
    )

    if status == PluginStatus.APPROVED:
        db.add(
            PluginRating(
                plugin_id=plugin.id,
                rating_type="admin",
                functionality=RatingGrade.A,
                security=RatingGrade.A,
                documentation=RatingGrade.A,
                notes=plugin_data["review_note"],
                reviewer_id=reviewer.id,
            )
        )

    return plugin


async def seed_reviews(db, users: dict[str, User], plugins: dict[str, Plugin]) -> None:
    for review_data in DEMO_REVIEWS:
        plugin = plugins[review_data["plugin"]]
        author = users[review_data["author"]]
        db.add(
            Review(
                plugin_id=plugin.id,
                author_id=author.id,
                rating=review_data["rating"],
                title=review_data["title"],
                content=review_data["content"],
            )
        )


async def clear_demo_notifications(db, users: dict[str, User]) -> None:
    user_ids = [user.id for user in users.values()]
    if user_ids:
        await db.execute(delete(Notification).where(Notification.user_id.in_(user_ids)))


async def seed_notifications(db, users: dict[str, User]) -> None:
    for notification_data in DEMO_NOTIFICATIONS:
        user = users[notification_data["user"]]
        db.add(
            Notification(
                user_id=user.id,
                type=notification_data["type"],
                title=notification_data["title"],
                content=notification_data["content"],
                target_url=notification_data["target_url"],
                is_read=notification_data["is_read"],
            )
        )


async def seed_demo_data() -> None:
    assert_demo_seed_allowed()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        await BootstrapService.ensure_schema_compatibility(db)
        await BootstrapService.ensure_initial_admin(db)
        await PermissionService().init_system_permissions(db)

        zones = {
            zone_data["slug"]: await get_or_create_zone(db, zone_data)
            for zone_data in DEFAULT_ZONES
        }
        categories = {
            category_data["slug"]: await get_or_create_category(db, category_data)
            for category_data in DEFAULT_CATEGORIES
        }
        users = {
            user_data["username"]: await upsert_user(db, user_data)
            for user_data in DEMO_USERS
        }
        users[settings.INITIAL_ADMIN_USERNAME] = await upsert_root_admin(db)
        await clear_demo_notifications(db, users)
        plugins = {
            plugin_data["slug"]: await upsert_plugin(db, plugin_data, users, zones, categories)
            for plugin_data in DEMO_PLUGINS
        }
        await seed_reviews(db, users, plugins)
        await seed_notifications(db, users)

        await db.commit()

    print("Demo data seeded.")
    print("Accounts:")
    print(f"  root / password")
    for user in DEMO_USERS:
        print(f"  {user['username']} / {DEMO_PASSWORD}")
    print("Plugins:")
    for plugin in plugins.values():
        print(f"  {plugin.slug} ({plugin.status.value})")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
