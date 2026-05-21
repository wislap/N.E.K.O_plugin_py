from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.time import utc_now


class UserPluginInstall(Base):
    """User-level record that a Market plugin was installed via N.E.K.O."""

    __tablename__ = "user_plugin_installs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plugin_id = Column(Integer, ForeignKey("plugins.id"), nullable=False, index=True)

    version = Column(String(50), nullable=True)
    channel = Column(String(16), nullable=True)
    package_sha256 = Column(String(64), nullable=True)
    payload_hash = Column(String(128), nullable=True)
    installed_plugin_id = Column(String(100), nullable=True)
    client_id = Column(String(50), nullable=False, default="neko-desktop")

    installed_at = Column(DateTime, default=utc_now, nullable=False)
    last_seen_at = Column(DateTime, default=utc_now, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="plugin_installs")
    plugin = relationship("Plugin", back_populates="user_installs")

    __table_args__ = (
        UniqueConstraint("user_id", "plugin_id", name="uq_user_plugin_install"),
    )
