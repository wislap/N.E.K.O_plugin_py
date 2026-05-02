"""baseline schema

Revision ID: 20260502_0001
Revises:
Create Date: 2026-05-02 00:01:00
"""
from alembic import op
import sqlalchemy as sa


revision = "20260502_0001"
down_revision = None
branch_labels = None
depends_on = None


PLUGIN_STATUS = sa.Enum(
    "PENDING",
    "APPROVED",
    "REJECTED",
    "DISABLED",
    name="pluginstatus",
)
REVIEW_STAGE = sa.Enum(
    "SUBMITTED",
    "FETCHING",
    "FETCHED",
    "AI_REVIEWING",
    "AI_REVIEWED",
    "NEEDS_REVISION",
    "REVISION_SUBMITTED",
    "AI_APPROVED",
    "MANUAL_REVIEWING",
    "APPROVED",
    "REJECTED",
    name="reviewstage",
)
RATING_GRADE = sa.Enum("S", "A", "B", "C", "D", name="ratinggrade")


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(length=100), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_categories_id"), "categories", ["id"], unique=False)

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_permissions_category"), "permissions", ["category"], unique=False)
    op.create_index(op.f("ix_permissions_code"), "permissions", ["code"], unique=True)
    op.create_index(op.f("ix_permissions_id"), "permissions", ["id"], unique=False)

    op.create_table(
        "server_key_pairs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("private_key_encrypted", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column("deactivated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_server_key_pairs_id"), "server_key_pairs", ["id"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("bio", sa.String(length=500), nullable=True),
        sa.Column("website", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=True),
        sa.Column("must_change_password", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "zones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(length=50), nullable=True),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_zones_id"), "zones", ["id"], unique=False)
    op.create_index(op.f("ix_zones_slug"), "zones", ["slug"], unique=True)

    op.create_table(
        "ai_sandbox_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("plugin_id", sa.Integer(), nullable=False),
        sa.Column("task_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("execution_time", sa.Float(), nullable=True),
        sa.Column("input_hash", sa.String(length=64), nullable=True),
        sa.Column("output_hash", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("memory_usage", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_sandbox_logs_id"), "ai_sandbox_logs", ["id"], unique=False)
    op.create_index(op.f("ix_ai_sandbox_logs_plugin_id"), "ai_sandbox_logs", ["plugin_id"], unique=False)
    op.create_index(op.f("ix_ai_sandbox_logs_task_id"), "ai_sandbox_logs", ["task_id"], unique=True)

    op.create_table(
        "jwt_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key_id", sa.String(length=32), nullable=False),
        sa.Column("secret_key", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column("deactivated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_jwt_keys_id"), "jwt_keys", ["id"], unique=False)
    op.create_index(op.f("ix_jwt_keys_key_id"), "jwt_keys", ["key_id"], unique=True)

    op.create_table(
        "permission_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("group_type", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["permission_groups.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_permission_groups_code"), "permission_groups", ["code"], unique=True)
    op.create_index(op.f("ix_permission_groups_id"), "permission_groups", ["id"], unique=False)
    op.create_index(op.f("ix_permission_groups_parent_id"), "permission_groups", ["parent_id"], unique=False)

    op.create_table(
        "permission_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("operator_id", sa.Integer(), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_permission_audit_logs_id"), "permission_audit_logs", ["id"], unique=False)

    op.create_table(
        "permission_group_inheritance",
        sa.Column("parent_group_id", sa.Integer(), nullable=False),
        sa.Column("child_group_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["child_group_id"], ["permission_groups.id"]),
        sa.ForeignKeyConstraint(["parent_group_id"], ["permission_groups.id"]),
        sa.PrimaryKeyConstraint("parent_group_id", "child_group_id"),
    )

    op.create_table(
        "permission_group_items",
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["permission_groups.id"]),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
        sa.PrimaryKeyConstraint("group_id", "permission_id"),
    )

    op.create_table(
        "plugins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("short_description", sa.String(length=255), nullable=True),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("author_name", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("download_url", sa.String(length=500), nullable=True),
        sa.Column("icon_url", sa.String(length=500), nullable=True),
        sa.Column("repo_url", sa.String(length=500), nullable=True),
        sa.Column("repo_branch", sa.String(length=100), nullable=True),
        sa.Column("zone_id", sa.Integer(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("readme", sa.Text(), nullable=True),
        sa.Column("download_count", sa.Integer(), nullable=True),
        sa.Column("likes", sa.Integer(), nullable=True),
        sa.Column("rating_average", sa.Float(), nullable=True),
        sa.Column("rating_count", sa.Integer(), nullable=True),
        sa.Column("status", PLUGIN_STATUS, nullable=True),
        sa.Column("is_featured", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plugins_id"), "plugins", ["id"], unique=False)
    op.create_index(op.f("ix_plugins_name"), "plugins", ["name"], unique=False)
    op.create_index(op.f("ix_plugins_slug"), "plugins", ["slug"], unique=True)

    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("is_encrypted", sa.Boolean(), nullable=True),
        sa.Column("group", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_system_settings_group"), "system_settings", ["group"], unique=False)
    op.create_index(op.f("ix_system_settings_id"), "system_settings", ["id"], unique=False)
    op.create_index(op.f("ix_system_settings_key"), "system_settings", ["key"], unique=True)

    op.create_table(
        "user_permission_groups",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["permission_groups.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "group_id"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("target_url", sa.String(length=500), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_id"), "notifications", ["id"], unique=False)
    op.create_index(op.f("ix_notifications_is_read"), "notifications", ["is_read"], unique=False)
    op.create_index(op.f("ix_notifications_type"), "notifications", ["type"], unique=False)
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)

    op.create_table(
        "plugin_categories",
        sa.Column("plugin_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["plugin_id"], ["plugins.id"]),
        sa.PrimaryKeyConstraint("plugin_id", "category_id"),
    )

    op.create_table(
        "plugin_ratings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plugin_id", sa.Integer(), nullable=False),
        sa.Column("rating_type", sa.String(length=20), nullable=False),
        sa.Column("functionality", RATING_GRADE, nullable=True),
        sa.Column("security", RATING_GRADE, nullable=True),
        sa.Column("documentation", RATING_GRADE, nullable=True),
        sa.Column("rated_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["plugin_id"], ["plugins.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plugin_ratings_id"), "plugin_ratings", ["id"], unique=False)

    op.create_table(
        "plugin_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plugin_id", sa.Integer(), nullable=False),
        sa.Column("stage", REVIEW_STAGE, nullable=True),
        sa.Column("repo_url", sa.String(length=500), nullable=True),
        sa.Column("repo_branch", sa.String(length=100), nullable=True),
        sa.Column("ai_review_result", sa.JSON(), nullable=True),
        sa.Column("ai_score", sa.Integer(), nullable=True),
        sa.Column("ai_recommendation", sa.String(length=20), nullable=True),
        sa.Column("review_feedback", sa.Text(), nullable=True),
        sa.Column("revision_notes", sa.Text(), nullable=True),
        sa.Column("manual_reviewer_id", sa.Integer(), nullable=True),
        sa.Column("manual_review_notes", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=True),
        sa.Column("ai_reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("revision_requested_at", sa.DateTime(), nullable=True),
        sa.Column("revision_submitted_at", sa.DateTime(), nullable=True),
        sa.Column("manual_reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["manual_reviewer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["plugin_id"], ["plugins.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plugin_reviews_id"), "plugin_reviews", ["id"], unique=False)

    op.create_table(
        "plugin_signatures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plugin_id", sa.Integer(), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("files_hash", sa.String(length=32), nullable=False),
        sa.Column("files_md5", sa.JSON(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("plugin_name", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("author", sa.String(length=100), nullable=False),
        sa.Column("repo_url", sa.String(length=500), nullable=False),
        sa.Column("keypair_id", sa.Integer(), nullable=False),
        sa.Column("is_valid", sa.Boolean(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["keypair_id"], ["server_key_pairs.id"]),
        sa.ForeignKeyConstraint(["plugin_id"], ["plugins.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plugin_signatures_id"), "plugin_signatures", ["id"], unique=False)

    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plugin_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["plugin_id"], ["plugins.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plugin_id", "author_id", name="unique_user_plugin_review"),
    )
    op.create_index(op.f("ix_reviews_id"), "reviews", ["id"], unique=False)

    op.create_table(
        "versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plugin_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.Column("download_url", sa.String(length=500), nullable=True),
        sa.Column("min_app_version", sa.String(length=20), nullable=True),
        sa.Column("max_app_version", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["plugin_id"], ["plugins.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_versions_id"), "versions", ["id"], unique=False)

    op.create_table(
        "plugin_review_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plugin_id", sa.Integer(), nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("from_stage", sa.String(length=50), nullable=True),
        sa.Column("to_stage", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("operator_id", sa.Integer(), nullable=True),
        sa.Column("operator_type", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["plugin_id"], ["plugins.id"]),
        sa.ForeignKeyConstraint(["review_id"], ["plugin_reviews.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plugin_review_history_id"), "plugin_review_history", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_plugin_review_history_id"), table_name="plugin_review_history")
    op.drop_table("plugin_review_history")
    op.drop_index(op.f("ix_versions_id"), table_name="versions")
    op.drop_table("versions")
    op.drop_index(op.f("ix_reviews_id"), table_name="reviews")
    op.drop_table("reviews")
    op.drop_index(op.f("ix_plugin_signatures_id"), table_name="plugin_signatures")
    op.drop_table("plugin_signatures")
    op.drop_index(op.f("ix_plugin_reviews_id"), table_name="plugin_reviews")
    op.drop_table("plugin_reviews")
    op.drop_index(op.f("ix_plugin_ratings_id"), table_name="plugin_ratings")
    op.drop_table("plugin_ratings")
    op.drop_table("plugin_categories")
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_type"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_is_read"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_id"), table_name="notifications")
    op.drop_table("notifications")
    op.drop_table("user_permission_groups")
    op.drop_index(op.f("ix_system_settings_key"), table_name="system_settings")
    op.drop_index(op.f("ix_system_settings_id"), table_name="system_settings")
    op.drop_index(op.f("ix_system_settings_group"), table_name="system_settings")
    op.drop_table("system_settings")
    op.drop_index(op.f("ix_plugins_slug"), table_name="plugins")
    op.drop_index(op.f("ix_plugins_name"), table_name="plugins")
    op.drop_index(op.f("ix_plugins_id"), table_name="plugins")
    op.drop_table("plugins")
    op.drop_table("permission_group_items")
    op.drop_table("permission_group_inheritance")
    op.drop_index(op.f("ix_permission_audit_logs_id"), table_name="permission_audit_logs")
    op.drop_table("permission_audit_logs")
    op.drop_index(op.f("ix_permission_groups_parent_id"), table_name="permission_groups")
    op.drop_index(op.f("ix_permission_groups_id"), table_name="permission_groups")
    op.drop_index(op.f("ix_permission_groups_code"), table_name="permission_groups")
    op.drop_table("permission_groups")
    op.drop_index(op.f("ix_jwt_keys_key_id"), table_name="jwt_keys")
    op.drop_index(op.f("ix_jwt_keys_id"), table_name="jwt_keys")
    op.drop_table("jwt_keys")
    op.drop_index(op.f("ix_ai_sandbox_logs_task_id"), table_name="ai_sandbox_logs")
    op.drop_index(op.f("ix_ai_sandbox_logs_plugin_id"), table_name="ai_sandbox_logs")
    op.drop_index(op.f("ix_ai_sandbox_logs_id"), table_name="ai_sandbox_logs")
    op.drop_table("ai_sandbox_logs")
    op.drop_index(op.f("ix_zones_slug"), table_name="zones")
    op.drop_index(op.f("ix_zones_id"), table_name="zones")
    op.drop_table("zones")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_server_key_pairs_id"), table_name="server_key_pairs")
    op.drop_table("server_key_pairs")
    op.drop_index(op.f("ix_permissions_id"), table_name="permissions")
    op.drop_index(op.f("ix_permissions_code"), table_name="permissions")
    op.drop_index(op.f("ix_permissions_category"), table_name="permissions")
    op.drop_table("permissions")
    op.drop_index(op.f("ix_categories_id"), table_name="categories")
    op.drop_table("categories")
