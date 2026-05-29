from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Enum, JSON
from sqlalchemy import inspect
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.core.time import utc_now


class PluginStatus(str, enum.Enum):
    APPROVED = "approved"    # 已通过
    DISABLED = "disabled"    # 已禁用


class Plugin(Base):
    __tablename__ = "plugins"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    short_description = Column(String(255), nullable=True)
    
    # 作者信息
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    author_name = Column(String(100), nullable=False)
    
    # 插件展示
    icon_url = Column(String(500), nullable=True)
    
    # GitHub 仓库信息
    repo_url = Column(String(500), nullable=True)
    repo_branch = Column(String(100), default="main")
    
    # 区域和标签（匹配前端结构）
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    tags = Column(JSON, default=list)  # 标签列表，如：["游戏", "查询", "攻略"]
    
    # README 内容
    readme = Column(Text, nullable=True)
    
    # 统计数据
    download_count = Column(Integer, default=0)
    likes = Column(Integer, default=0)  # 点赞数
    rating_average = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    
    # 状态
    status = Column(Enum(PluginStatus), default=PluginStatus.APPROVED)
    is_featured = Column(Integer, default=0)  # 是否推荐
    
    # 时间戳
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    published_at = Column(DateTime, nullable=True)
    
    # 关系
    author = relationship("User", back_populates="plugins")
    reviews = relationship("Review", back_populates="plugin", cascade="all, delete-orphan")
    versions = relationship("Version", back_populates="plugin", cascade="all, delete-orphan")
    categories = relationship("Category", secondary="plugin_categories", back_populates="plugins")
    signatures = relationship("PluginSignature", back_populates="plugin")
    zone = relationship("Zone", back_populates="plugins")
    ratings = relationship("PluginRating", back_populates="plugin", cascade="all, delete-orphan")
    user_installs = relationship("UserPluginInstall", back_populates="plugin", cascade="all, delete-orphan")
    user_likes = relationship("PluginLike", back_populates="plugin", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Plugin(id={self.id}, name='{self.name}', status='{self.status}')>"
    
    @property
    def ai_rating(self):
        """获取 AI 评分"""
        for rating in self.ratings:
            if rating.rating_type == 'ai':
                return rating.to_dict()
        return None
    
    @property
    def admin_rating(self):
        """获取人工评分"""
        for rating in self.ratings:
            if rating.rating_type == 'admin':
                return rating.to_dict()
        return None

    @property
    def zone_slug(self):
        """获取插件分区 slug"""
        if "zone" in inspect(self).unloaded:
            return None
        return self.zone.slug if self.zone else None

    def to_frontend_dict(self):
        """转换为前端需要的格式

        注意：`version` / `downloadUrl` 等"当前版本"语义已不再从 Plugin
        本体读，转由 versions 表通过 `attach_latest_version` 投影出来。
        本方法仅保留旧版本兼容路径下用到的字段；新代码应直接走 Pydantic
        schema (`Plugin` / `LatestVersionPublic`)。
        """
        latest = getattr(self, "latest_version", None)
        latest_dict = None
        if latest is not None:
            latest_dict = {
                "version": latest.version,
                "channel": latest.channel,
                "package_url": latest.package_url or "",
                "package_sha256": latest.package_sha256 or "",
                "payload_hash": latest.payload_hash,
                "created_at": (
                    latest.created_at.isoformat() if latest.created_at else None
                ),
            }
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description or self.short_description or "",
            "latest_version": latest_dict,
            "author": {
                "name": self.author_name,
                "avatar": self.author.avatar_url if self.author else "",
                "github": self.repo_url.split('/')[3] if self.repo_url and len(self.repo_url.split('/')) > 3 else ""
            },
            "githubRepo": self.repo_url or "",
            "zone": self.zone.slug if self.zone else "function",
            "tags": self.tags or [],
            "downloads": self.download_count,
            "likes": self.likes,
            "aiRating": self.ai_rating,
            "adminRating": self.admin_rating,
            "readme": self.readme or "",
            "createdAt": self.created_at.isoformat() if self.created_at else "",
            "updatedAt": self.updated_at.isoformat() if self.updated_at else "",
            "isRecommended": bool(self.is_featured)
        }
