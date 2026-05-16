"""market version management

Revision ID: 20260516_0001
Revises: 20260505_0001
Create Date: 2026-05-16

变更要点（与 spec
`Plugin Market (Backend + Frontend)/.kiro/specs/market-version-management/`
中 R1 / R2 对应）：

- versions 表新增 channel / is_latest / yanked_* / published_by 列；
- 数据搬运：把 plugins.download_url 非空但 versions 表无对应行的 plugin
  补一条 legacy Version 行（verification_status='legacy_unverified'）；
- 删除 plugins.version、plugins.download_url 列；
- 加 (plugin_id, version) 全表唯一索引；
- 加 (plugin_id, channel) WHERE is_latest=1 的部分唯一索引（P1 兜底）；
- CHECK (channel IN ('stable','beta'))；
- yanked_by / published_by 外键 ON DELETE SET NULL。

注意：原 versions.plugin_id 外键在 fresh_schema 中是匿名的，本迁移不动它，
保留 `cascade="all, delete-orphan"` ORM 层兜底。
"""
from alembic import op
import sqlalchemy as sa


revision = '20260516_0001'
down_revision = '20260505_0001'
branch_labels = None
depends_on = None



def upgrade() -> None:
    # 1) versions 表新增 6 列（先 nullable=True，便于 backfill）
    with op.batch_alter_table("versions") as batch:
        batch.add_column(sa.Column("channel", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("is_latest", sa.Boolean(), nullable=True))
        batch.add_column(sa.Column("yanked_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("yanked_reason", sa.Text(), nullable=True))
        batch.add_column(sa.Column("yanked_by", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("published_by", sa.Integer(), nullable=True))

    # 2) backfill 现存 versions 行 channel='stable', is_latest=0
    op.execute("UPDATE versions SET channel = 'stable' WHERE channel IS NULL")
    op.execute("UPDATE versions SET is_latest = 0 WHERE is_latest IS NULL")

    # 3) 每个 plugin_id 的 created_at desc 第一条置 is_latest=1
    op.execute(
        """
        UPDATE versions SET is_latest = 1
        WHERE id IN (
            SELECT id FROM (
                SELECT v.id,
                       ROW_NUMBER() OVER (
                           PARTITION BY v.plugin_id
                           ORDER BY v.created_at DESC, v.id DESC
                       ) AS rn
                FROM versions v
            ) ranked
            WHERE rn = 1
        )
        """
    )

    # 4) plugins.download_url 非空但 versions 表无对应行的 plugin 补 legacy 行
    op.execute(
        """
        INSERT INTO versions (
            plugin_id, version, channel, is_latest, yanked_at,
            download_url, package_url, package_sha256,
            verification_status, published_by, created_at
        )
        SELECT p.id,
               COALESCE(NULLIF(p.version, ''), '0.0.0'),
               'stable',
               1,
               NULL,
               p.download_url,
               p.download_url,
               '',
               'legacy_unverified',
               p.author_id,
               COALESCE(p.published_at, p.created_at)
        FROM plugins p
        WHERE (p.download_url IS NOT NULL AND p.download_url <> '')
          AND NOT EXISTS (SELECT 1 FROM versions v WHERE v.plugin_id = p.id)
        """
    )


    # 5) 把 channel / is_latest 改为 NOT NULL + 加 CHECK + 加新 FK
    with op.batch_alter_table("versions") as batch:
        batch.alter_column(
            "channel",
            existing_type=sa.String(length=16),
            nullable=False,
            server_default="stable",
        )
        batch.alter_column(
            "is_latest",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        )
        batch.create_check_constraint(
            "ck_versions_channel",
            "channel IN ('stable','beta')",
        )
        batch.create_foreign_key(
            "fk_versions_yanked_by_users",
            "users",
            ["yanked_by"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_foreign_key(
            "fk_versions_published_by_users",
            "users",
            ["published_by"],
            ["id"],
            ondelete="SET NULL",
        )

    # 6) 唯一索引：(plugin_id, version) 全表唯一 + (plugin_id, channel) WHERE is_latest=1 部分唯一
    op.create_index(
        "uq_versions_plugin_version",
        "versions",
        ["plugin_id", "version"],
        unique=True,
    )
    op.create_index(
        "uq_versions_plugin_channel_latest",
        "versions",
        ["plugin_id", "channel"],
        unique=True,
        sqlite_where=sa.text("is_latest = 1"),
    )

    # 7) plugins 表删除 version / download_url
    with op.batch_alter_table("plugins") as batch:
        batch.drop_column("version")
        batch.drop_column("download_url")



def downgrade() -> None:
    """最简实现：drop 索引 / 约束 / FK / 6 列；恢复 plugins.version / download_url。

    不还原数据搬运（被搬到 versions 的 download_url 不会回填回 plugins）。
    spec R1.9 已声明 downgrade 不强制完美。
    """
    op.drop_index("uq_versions_plugin_channel_latest", table_name="versions")
    op.drop_index("uq_versions_plugin_version", table_name="versions")

    with op.batch_alter_table("versions") as batch:
        batch.drop_constraint("fk_versions_published_by_users", type_="foreignkey")
        batch.drop_constraint("fk_versions_yanked_by_users", type_="foreignkey")
        batch.drop_constraint("ck_versions_channel", type_="check")
        batch.drop_column("published_by")
        batch.drop_column("yanked_by")
        batch.drop_column("yanked_reason")
        batch.drop_column("yanked_at")
        batch.drop_column("is_latest")
        batch.drop_column("channel")

    with op.batch_alter_table("plugins") as batch:
        batch.add_column(
            sa.Column(
                "download_url",
                sa.String(length=500),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "version",
                sa.String(length=20),
                nullable=False,
                server_default="0.0.0",
            )
        )
