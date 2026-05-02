from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.time import utc_now


class Zone(Base):
    """插件区域/分区模型"""
    __tablename__ = "zones"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)  # 区域名称，如：游戏区、陪玩区
    slug = Column(String(50), unique=True, nullable=False, index=True)  # URL友好的标识
    description = Column(Text, nullable=True)  # 区域描述
    icon = Column(String(50), nullable=True)  # 图标名称，如：Gamepad2, Heart
    color = Column(String(7), nullable=True)  # 主题色，如：#EF4444
    sort_order = Column(Integer, default=0)  # 排序顺序
    
    # 时间戳
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # 关系
    plugins = relationship("Plugin", back_populates="zone")
    
    @property
    def plugin_count(self):
        """插件数量（通过关系计算）"""
        return len(self.plugins) if self.plugins else 0
    
    def __repr__(self):
        return f"<Zone(id={self.id}, name='{self.name}', slug='{self.slug}')>"
