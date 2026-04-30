from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class RatingGrade(str, enum.Enum):
    """评分等级 S/A/B/C/D"""
    S = "S"
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class PluginRating(Base):
    """插件评分模型（AI评分和人工评分）"""
    __tablename__ = "plugin_ratings"
    
    id = Column(Integer, primary_key=True, index=True)
    plugin_id = Column(Integer, ForeignKey("plugins.id"), nullable=False)
    
    # 评分类型
    rating_type = Column(String(20), nullable=False)  # 'ai' 或 'admin'
    
    # 各项评分 S/A/B/C/D
    functionality = Column(Enum(RatingGrade), default=RatingGrade.B)  # 功能性
    security = Column(Enum(RatingGrade), default=RatingGrade.B)  # 安全性
    documentation = Column(Enum(RatingGrade), default=RatingGrade.B)  # 文档完整性
    
    # 评分时间
    rated_at = Column(DateTime, default=datetime.utcnow)
    
    # 评分备注/理由
    notes = Column(Text, nullable=True)
    
    # 评分人（人工评分时）
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    plugin = relationship("Plugin", back_populates="ratings")
    reviewer = relationship("User")
    
    def __repr__(self):
        return f"<PluginRating(id={self.id}, plugin_id={self.plugin_id}, type='{self.rating_type}')>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "functionality": self.functionality.value if self.functionality else "B",
            "security": self.security.value if self.security else "B",
            "documentation": self.documentation.value if self.documentation else "B",
            "ratedAt": self.rated_at.isoformat() if self.rated_at else None
        }
