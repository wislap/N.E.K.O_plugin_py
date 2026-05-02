from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base
from app.core.time import utc_now


class Version(Base):
    __tablename__ = "versions"
    
    id = Column(Integer, primary_key=True, index=True)
    plugin_id = Column(Integer, ForeignKey("plugins.id"), nullable=False)
    
    # 版本信息
    version = Column(String(20), nullable=False)
    changelog = Column(Text, nullable=True)
    download_url = Column(String(500), nullable=True)
    
    # 兼容性
    min_app_version = Column(String(20), nullable=True)
    max_app_version = Column(String(20), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=utc_now)
    
    # 关系
    plugin = relationship("Plugin", back_populates="versions")
    
    def __repr__(self):
        return f"<Version(id={self.id}, plugin_id={self.plugin_id}, version='{self.version}')>"
