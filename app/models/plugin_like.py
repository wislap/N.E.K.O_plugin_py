from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.time import utc_now


class PluginLike(Base):
    """A user's like for a plugin."""

    __tablename__ = "plugin_likes"

    id = Column(Integer, primary_key=True, index=True)
    plugin_id = Column(Integer, ForeignKey("plugins.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    plugin = relationship("Plugin", back_populates="user_likes")
    user = relationship("User", back_populates="plugin_likes")

    __table_args__ = (
        UniqueConstraint("plugin_id", "user_id", name="uq_plugin_like_user"),
    )
