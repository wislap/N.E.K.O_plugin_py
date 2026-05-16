from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.time import utc_now


class Version(Base):
    """插件版本记录。

    每条 Version 对应一次发布。`channel` 区分正式版 / 测试版；同一
    (plugin_id, channel) 至多一条 `is_latest=True AND yanked_at IS NULL`，
    由数据库 partial unique index `uq_versions_plugin_channel_latest` 兜底。

    Frozen_Fact 字段（`package_url` / `package_sha256` / `payload_hash` /
    `release_url` / `release_tag` / `source_commit` / `version` / `channel`）
    一旦写入不允许通过任何 PATCH 接口修改 —— 由 Pydantic schema 中
    `VersionPublishRequest` 字段集与路由层的删除共同保证。
    """

    __tablename__ = "versions"

    id = Column(Integer, primary_key=True, index=True)
    plugin_id = Column(
        Integer,
        ForeignKey("plugins.id"),
        nullable=False,
    )

    # 版本基本信息
    version = Column(String(20), nullable=False)
    changelog = Column(Text, nullable=True)

    # 渠道与生命周期标记
    channel = Column(String(16), nullable=False, default="stable")
    is_latest = Column(Boolean, nullable=False, default=False)

    yanked_at = Column(DateTime, nullable=True)
    yanked_reason = Column(Text, nullable=True)
    yanked_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    published_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


    # 包文件 / 校验信息（Frozen_Fact）
    download_url = Column(String(500), nullable=True)
    package_url = Column(String(500), nullable=True)
    package_sha256 = Column(String(64), nullable=True)
    payload_hash = Column(String(64), nullable=True)

    # 来源元数据
    source_repo_url = Column(String(500), nullable=True)
    source_commit = Column(String(64), nullable=True)
    release_tag = Column(String(100), nullable=True)
    release_url = Column(String(500), nullable=True)
    actions_run_url = Column(String(500), nullable=True)

    # NEKO 客户端兼容字段（保留供未来 spec 用）
    neko_repo = Column(String(200), nullable=True)
    neko_ref = Column(String(100), nullable=True)
    neko_commit = Column(String(64), nullable=True)

    # 校验状态
    verification_status = Column(String(20), nullable=False, default="unverified")
    verification_summary = Column(Text, nullable=True)

    # 兼容性约束（本特性不强校验，留给客户端 spec）
    min_app_version = Column(String(20), nullable=True)
    max_app_version = Column(String(20), nullable=True)

    created_at = Column(DateTime, default=utc_now)

    # 关系
    plugin = relationship("Plugin", back_populates="versions")
    yanker = relationship("User", foreign_keys=[yanked_by])
    publisher = relationship("User", foreign_keys=[published_by])

    __table_args__ = (
        CheckConstraint(
            "channel IN ('stable','beta')",
            name="ck_versions_channel",
        ),
        Index(
            "uq_versions_plugin_version",
            "plugin_id",
            "version",
            unique=True,
        ),
        # 部分唯一索引：每个 (plugin, channel) 至多一条 is_latest=true。
        # 这是 P1（is_latest 唯一性）与 P3（并发同 release_url 幂等）的兜底。
        # SQLite partial index 通过 sqlite_where 表达。
        Index(
            "uq_versions_plugin_channel_latest",
            "plugin_id",
            "channel",
            unique=True,
            sqlite_where=text("is_latest = 1"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Version(id={self.id}, plugin_id={self.plugin_id}, "
            f"version='{self.version}', channel='{self.channel}', "
            f"is_latest={self.is_latest})>"
        )
