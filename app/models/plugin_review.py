from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class ReviewStage(str, enum.Enum):
    """审核阶段"""
    SUBMITTED = "submitted"           # 已提交
    FETCHING = "fetching"             # 拉取代码中
    FETCHED = "fetched"               # 代码已拉取
    AI_REVIEWING = "ai_reviewing"     # AI审核中
    AI_REVIEWED = "ai_reviewed"       # AI审核完成
    NEEDS_REVISION = "needs_revision" # 需要修改
    REVISION_SUBMITTED = "revision_submitted"  # 修改已提交
    AI_APPROVED = "ai_approved"       # AI审核通过
    MANUAL_REVIEWING = "manual_reviewing"  # 人工审核中
    APPROVED = "approved"             # 审核通过
    REJECTED = "rejected"             # 审核拒绝


class PluginReview(Base):
    """插件审核记录"""
    __tablename__ = "plugin_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    plugin_id = Column(Integer, ForeignKey("plugins.id"), nullable=False)
    
    # 审核阶段
    stage = Column(Enum(ReviewStage), default=ReviewStage.SUBMITTED)
    
    # GitHub 仓库信息
    repo_url = Column(String(500), nullable=True)
    repo_branch = Column(String(100), default="main")
    
    # AI 审核结果
    ai_review_result = Column(JSON, nullable=True)
    ai_score = Column(Integer, nullable=True)  # AI评分 0-100
    ai_recommendation = Column(String(20), nullable=True)  # approve/reject/needs_revision/manual_review
    
    # 审核反馈
    review_feedback = Column(Text, nullable=True)  # AI或人工的审核意见
    revision_notes = Column(Text, nullable=True)   # 修改说明
    
    # 人工审核
    manual_reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    manual_review_notes = Column(Text, nullable=True)
    
    # 时间戳
    submitted_at = Column(DateTime, default=datetime.utcnow)
    fetched_at = Column(DateTime, nullable=True)
    ai_reviewed_at = Column(DateTime, nullable=True)
    revision_requested_at = Column(DateTime, nullable=True)
    revision_submitted_at = Column(DateTime, nullable=True)
    manual_reviewed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # 关系
    plugin = relationship("Plugin", back_populates="reviews_history")
    manual_reviewer = relationship("User")
    
    def __repr__(self):
        return f"<PluginReview(id={self.id}, plugin_id={self.plugin_id}, stage='{self.stage}')>"


class PluginReviewHistory(Base):
    """插件审核历史记录（每次修改都记录）"""
    __tablename__ = "plugin_review_history"
    
    id = Column(Integer, primary_key=True, index=True)
    plugin_id = Column(Integer, ForeignKey("plugins.id"), nullable=False)
    review_id = Column(Integer, ForeignKey("plugin_reviews.id"), nullable=False)
    
    # 变更信息
    from_stage = Column(String(50), nullable=True)
    to_stage = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    
    # 操作人
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    operator_type = Column(String(20), default="system")  # system/ai/user
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
