from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.time import utc_now


class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    plugin_id = Column(Integer, ForeignKey("plugins.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Deprecated: user-facing star ratings have been retired.
    rating = Column(Float, nullable=True)
    title = Column(String(100), nullable=True)
    content = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # 关系
    plugin = relationship("Plugin", back_populates="reviews")
    author = relationship("User", back_populates="reviews")
    
    # 一个用户只能对一个插件评论一次
    __table_args__ = (
        UniqueConstraint('plugin_id', 'author_id', name='unique_user_plugin_review'),
    )
    
    def __repr__(self):
        return f"<Review(id={self.id}, plugin_id={self.plugin_id})>"
