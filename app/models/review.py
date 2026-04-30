from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    plugin_id = Column(Integer, ForeignKey("plugins.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 评分 1-5
    rating = Column(Float, nullable=False)
    title = Column(String(100), nullable=True)
    content = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    plugin = relationship("Plugin", back_populates="reviews")
    author = relationship("User", back_populates="reviews")
    
    # 一个用户只能对一个插件评分一次
    __table_args__ = (
        UniqueConstraint('plugin_id', 'author_id', name='unique_user_plugin_review'),
    )
    
    def __repr__(self):
        return f"<Review(id={self.id}, plugin_id={self.plugin_id}, rating={self.rating})>"
