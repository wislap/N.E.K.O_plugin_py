import sys
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from app.core.security import verify_password
from app.models import (
    Category,
    Notification,
    Plugin,
    PluginCategory,
    PluginRating,
    PluginReview,
    PluginReviewHistory,
    PluginStatus,
    Review,
    ReviewStage,
    User,
    Version,
    Zone,
)
from demo_data import (
    DEFAULT_CATEGORIES,
    DEFAULT_ZONES,
    DEMO_NOTIFICATIONS,
    DEMO_PASSWORD,
    DEMO_PLUGINS,
    DEMO_REVIEWS,
    DEMO_USERS,
    assert_demo_seed_allowed,
)
from seed_demo_data import (
    clear_demo_notifications,
    get_or_create_category,
    get_or_create_zone,
    review_stage_for_status,
    seed_notifications,
    seed_reviews,
    upsert_plugin,
    upsert_root_admin,
    upsert_user,
)


def test_demo_seed_requires_explicit_opt_in(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DEMO_SEED_ENABLED", raising=False)

    with pytest.raises(SystemExit, match="DEMO_SEED_ENABLED is not enabled"):
        assert_demo_seed_allowed()


def test_demo_seed_blocks_production_even_when_enabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEMO_SEED_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "production")

    with pytest.raises(SystemExit, match="blocked while ENVIRONMENT=production"):
        assert_demo_seed_allowed()


def test_demo_seed_allows_enabled_development(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEMO_SEED_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")

    assert_demo_seed_allowed()


def test_review_stage_for_status():
    assert review_stage_for_status(PluginStatus.APPROVED) == ReviewStage.APPROVED
    assert review_stage_for_status(PluginStatus.REJECTED) == ReviewStage.REJECTED
    assert review_stage_for_status(PluginStatus.DISABLED) == ReviewStage.APPROVED
    assert review_stage_for_status(PluginStatus.PENDING) == ReviewStage.SUBMITTED


@pytest.mark.asyncio
async def test_upsert_user_resets_demo_account(db_session: AsyncSession):
    user_data = DEMO_USERS[0]

    user = await upsert_user(db_session, user_data)
    await db_session.flush()

    user.email = "stale@example.com"
    user.is_admin = True
    user.must_change_password = True
    user.hashed_password = "stale-hash"

    updated = await upsert_user(db_session, user_data)
    await db_session.flush()

    assert updated.id == user.id
    assert updated.email == user_data["email"]
    assert updated.is_admin is user_data["is_admin"]
    assert updated.must_change_password is False
    assert verify_password(DEMO_PASSWORD, updated.hashed_password)


@pytest.mark.asyncio
async def test_upsert_root_admin_forces_initial_password_change(db_session: AsyncSession):
    root = await upsert_root_admin(db_session)

    assert root.username == "root"
    assert root.is_admin is True
    assert root.must_change_password is True
    assert verify_password("password", root.hashed_password)


@pytest.mark.asyncio
async def test_upsert_plugin_replaces_existing_artifacts(db_session: AsyncSession):
    zones = {
        zone["slug"]: await get_or_create_zone(db_session, zone)
        for zone in DEFAULT_ZONES
    }
    categories = {
        category["slug"]: await get_or_create_category(db_session, category)
        for category in DEFAULT_CATEGORIES
    }
    users = {
        user["username"]: await upsert_user(db_session, user)
        for user in DEMO_USERS
    }
    plugin_data = next(plugin for plugin in DEMO_PLUGINS if plugin["status"] == "approved")

    first = await upsert_plugin(db_session, plugin_data, users, zones, categories)
    await db_session.flush()
    second = await upsert_plugin(db_session, plugin_data, users, zones, categories)
    await db_session.flush()

    assert second.id == first.id
    assert second.status == PluginStatus.APPROVED
    assert second.is_featured == 1

    plugin_id = second.id
    assert await db_session.scalar(select(func.count(Plugin.id)).where(Plugin.slug == plugin_data["slug"])) == 1
    assert await db_session.scalar(select(func.count(PluginReview.id)).where(PluginReview.plugin_id == plugin_id)) == 1
    assert await db_session.scalar(select(func.count(PluginReviewHistory.id)).where(PluginReviewHistory.plugin_id == plugin_id)) == 2
    assert await db_session.scalar(select(func.count(PluginRating.id)).where(PluginRating.plugin_id == plugin_id)) == 1
    assert await db_session.scalar(select(func.count(Version.id)).where(Version.plugin_id == plugin_id)) == 1
    assert await db_session.scalar(select(func.count(PluginCategory.plugin_id)).where(PluginCategory.plugin_id == plugin_id)) == len(plugin_data["categories"])


@pytest.mark.asyncio
async def test_seed_reviews_and_notifications_create_expected_demo_closure(db_session: AsyncSession):
    zones = {
        zone["slug"]: await get_or_create_zone(db_session, zone)
        for zone in DEFAULT_ZONES
    }
    categories = {
        category["slug"]: await get_or_create_category(db_session, category)
        for category in DEFAULT_CATEGORIES
    }
    users = {
        user["username"]: await upsert_user(db_session, user)
        for user in DEMO_USERS
    }
    plugins = {
        plugin["slug"]: await upsert_plugin(db_session, plugin, users, zones, categories)
        for plugin in DEMO_PLUGINS
    }

    await seed_reviews(db_session, users, plugins)
    await clear_demo_notifications(db_session, users)
    await seed_notifications(db_session, users)
    await db_session.flush()

    assert await db_session.scalar(select(func.count(Review.id))) == len(DEMO_REVIEWS)
    assert await db_session.scalar(select(func.count(Notification.id))) == len(DEMO_NOTIFICATIONS)

    await clear_demo_notifications(db_session, users)
    await seed_notifications(db_session, users)
    await db_session.flush()

    assert await db_session.scalar(select(func.count(Notification.id))) == len(DEMO_NOTIFICATIONS)
