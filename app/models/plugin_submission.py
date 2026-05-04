import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.time import utc_now


class SubmissionStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    CLOSED = "closed"


class ReviewDecision(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELED = "canceled"
    SUPERSEDED = "superseded"


class ReviewCaseStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class ReviewCommentSeverity(str, enum.Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    NITPICK = "nitpick"


class ReviewTargetArea(str, enum.Enum):
    OWNERSHIP = "ownership"
    METADATA = "metadata"
    CODE = "code"
    SECURITY = "security"
    PACKAGING = "packaging"
    LICENSE = "license"
    DOCS = "docs"
    RELEASE = "release"
    OTHER = "other"


class ReviewEventType(str, enum.Enum):
    DRAFT_CREATED = "draft_created"
    DRAFT_UPDATED = "draft_updated"
    SUBMITTED = "submitted"
    REVIEW_STARTED = "review_started"
    COMMENTED = "commented"
    COMMENT_UPDATED = "comment_updated"
    COMMENT_RESOLVED = "comment_resolved"
    COMMENT_REOPENED = "comment_reopened"
    APPROVED = "approved"
    REJECTED = "rejected"
    CLOSED = "closed"
    REOPENED = "reopened"
    WITHDRAWN = "withdrawn"


class PluginSubmission(Base):
    __tablename__ = "plugin_submissions"

    id = Column(Integer, primary_key=True, index=True)
    plugin_id = Column(Integer, ForeignKey("plugins.id"), nullable=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum(SubmissionStatus), nullable=False, default=SubmissionStatus.DRAFT, index=True)
    decision = Column(Enum(ReviewDecision), nullable=True, index=True)
    current_snapshot_id = Column(
        Integer,
        ForeignKey("plugin_submission_snapshots.id", use_alter=True, name="fk_plugin_submissions_current_snapshot_id"),
        nullable=True,
    )
    current_review_case_id = Column(
        Integer,
        ForeignKey("plugin_review_cases.id", use_alter=True, name="fk_plugin_submissions_current_review_case_id"),
        nullable=True,
    )
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    plugin = relationship("Plugin", foreign_keys=[plugin_id])
    author = relationship("User")
    snapshots = relationship(
        "PluginSubmissionSnapshot",
        back_populates="submission",
        cascade="all, delete-orphan",
        foreign_keys="PluginSubmissionSnapshot.submission_id",
        order_by="PluginSubmissionSnapshot.revision_number",
    )
    review_cases = relationship(
        "PluginReviewCase",
        back_populates="submission",
        cascade="all, delete-orphan",
        foreign_keys="PluginReviewCase.submission_id",
        order_by="PluginReviewCase.opened_at",
    )
    current_snapshot = relationship("PluginSubmissionSnapshot", foreign_keys=[current_snapshot_id], post_update=True)
    current_review_case = relationship("PluginReviewCase", foreign_keys=[current_review_case_id], post_update=True)


class PluginSubmissionSnapshot(Base):
    __tablename__ = "plugin_submission_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("plugin_submissions.id"), nullable=False, index=True)
    revision_number = Column(Integer, nullable=False)
    repo_url = Column(String(500), nullable=False)
    repo_owner = Column(String(120), nullable=True)
    repo_name = Column(String(160), nullable=True)
    submitted_ref = Column(String(120), nullable=True)
    resolved_commit = Column(String(64), nullable=True)
    commit_url = Column(String(500), nullable=True)
    actions_run_url = Column(String(500), nullable=True)
    artifact_url = Column(String(500), nullable=True)
    license_name = Column(String(100), nullable=True)
    plugin_name = Column(String(100), nullable=False)
    plugin_slug = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    short_description = Column(String(255), nullable=True)
    zone_slug = Column(String(50), nullable=True)
    tags = Column(JSON, nullable=False, default=list)
    snapshot_metadata = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    submission = relationship(
        "PluginSubmission",
        back_populates="snapshots",
        foreign_keys=[submission_id],
    )


class PluginReviewCase(Base):
    __tablename__ = "plugin_review_cases"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("plugin_submissions.id"), nullable=False, index=True)
    snapshot_id = Column(Integer, ForeignKey("plugin_submission_snapshots.id"), nullable=False, index=True)
    status = Column(Enum(ReviewCaseStatus), nullable=False, default=ReviewCaseStatus.OPEN, index=True)
    decision = Column(Enum(ReviewDecision), nullable=True, index=True)
    opened_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    closed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    decision_summary = Column(Text, nullable=True)
    opened_at = Column(DateTime, default=utc_now, nullable=False)
    closed_at = Column(DateTime, nullable=True)

    submission = relationship(
        "PluginSubmission",
        back_populates="review_cases",
        foreign_keys=[submission_id],
    )
    snapshot = relationship("PluginSubmissionSnapshot")
    opener = relationship("User", foreign_keys=[opened_by])
    closer = relationship("User", foreign_keys=[closed_by])
    comments = relationship(
        "PluginReviewComment",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="PluginReviewComment.created_at",
    )


class PluginReviewComment(Base):
    __tablename__ = "plugin_review_comments"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("plugin_review_cases.id"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    severity = Column(Enum(ReviewCommentSeverity), nullable=False, index=True)
    target_area = Column(Enum(ReviewTargetArea), nullable=False, index=True)
    target_ref = Column(String(500), nullable=True)
    body = Column(Text, nullable=False)
    is_resolved = Column(Boolean, nullable=False, default=False, index=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    case = relationship("PluginReviewCase", back_populates="comments")
    author = relationship("User", foreign_keys=[author_id])
    resolver = relationship("User", foreign_keys=[resolved_by])


class PluginReviewEvent(Base):
    __tablename__ = "plugin_review_events"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("plugin_submissions.id"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("plugin_review_cases.id"), nullable=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    event_type = Column(Enum(ReviewEventType), nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    submission = relationship("PluginSubmission")
    case = relationship("PluginReviewCase")
    actor = relationship("User")
