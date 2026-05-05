from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.plugin_submission import (
    ReviewCaseStatus,
    ReviewCommentSeverity,
    ReviewDecision,
    ReviewEventType,
    ReviewTargetArea,
    SubmissionStatus,
)


class SubmissionDraftCreate(BaseModel):
    repo_url: str = Field(..., min_length=1, max_length=500)
    plugin_name: str = Field(..., min_length=1, max_length=100)
    plugin_slug: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    short_description: str | None = Field(None, max_length=255)
    zone_slug: str | None = Field(None, max_length=50)
    tags: list[str] = Field(default_factory=list)
    submitted_ref: str | None = Field(None, max_length=120)
    resolved_commit: str | None = Field(None, max_length=64)
    commit_url: str | None = Field(None, max_length=500)
    actions_run_url: str | None = Field(None, max_length=500)
    artifact_url: str | None = Field(None, max_length=500)
    license_name: str | None = Field(None, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SubmissionDraftUpdate(BaseModel):
    repo_url: str | None = Field(None, min_length=1, max_length=500)
    plugin_name: str | None = Field(None, min_length=1, max_length=100)
    plugin_slug: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    short_description: str | None = Field(None, max_length=255)
    zone_slug: str | None = Field(None, max_length=50)
    tags: list[str] | None = None
    submitted_ref: str | None = Field(None, max_length=120)
    resolved_commit: str | None = Field(None, max_length=64)
    commit_url: str | None = Field(None, max_length=500)
    actions_run_url: str | None = Field(None, max_length=500)
    artifact_url: str | None = Field(None, max_length=500)
    license_name: str | None = Field(None, max_length=100)
    metadata: dict[str, Any] | None = None


class SubmissionRevisionCreate(SubmissionDraftUpdate):
    note: str | None = Field(None, max_length=1000)


class SubmitRequest(BaseModel):
    note: str | None = Field(None, max_length=1000)


class ReviewStartRequest(BaseModel):
    note: str | None = Field(None, max_length=1000)


class ReviewDecisionRequest(BaseModel):
    summary: str | None = Field(None, max_length=4000)
    force: bool = False


class ReviewCommentCreate(BaseModel):
    severity: ReviewCommentSeverity
    target_area: ReviewTargetArea
    body: str = Field(..., min_length=1, max_length=8000)
    target_ref: str | None = Field(None, max_length=500)


class ReviewCommentUpdate(BaseModel):
    severity: ReviewCommentSeverity | None = None
    target_area: ReviewTargetArea | None = None
    body: str | None = Field(None, min_length=1, max_length=8000)
    target_ref: str | None = Field(None, max_length=500)


class SubmissionSnapshot(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submission_id: int
    revision_number: int
    repo_url: str
    repo_owner: str | None
    repo_name: str | None
    submitted_ref: str | None
    resolved_commit: str | None
    commit_url: str | None
    actions_run_url: str | None
    artifact_url: str | None
    license_name: str | None
    plugin_name: str
    plugin_slug: str
    description: str | None
    short_description: str | None
    zone_slug: str | None
    tags: list[str]
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="snapshot_metadata")
    created_at: datetime


class ReviewComment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    author_id: int
    severity: ReviewCommentSeverity
    target_area: ReviewTargetArea
    target_ref: str | None
    body: str
    is_resolved: bool
    resolved_by: int | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReviewEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submission_id: int
    case_id: int | None
    actor_id: int | None
    event_type: ReviewEventType
    payload: dict[str, Any]
    created_at: datetime


class ReviewCase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submission_id: int
    snapshot_id: int
    status: ReviewCaseStatus
    decision: ReviewDecision | None
    opened_by: int | None
    closed_by: int | None
    decision_summary: str | None
    opened_at: datetime
    closed_at: datetime | None
    comments: list[ReviewComment] = Field(default_factory=list)


class ReviewCounts(BaseModel):
    critical: int = 0
    major: int = 0
    minor: int = 0
    nitpick: int = 0
    unresolved: int = 0


class PluginSubmission(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plugin_id: int | None
    author_id: int
    status: SubmissionStatus
    decision: ReviewDecision | None
    current_snapshot_id: int | None
    current_review_case_id: int | None
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    closed_at: datetime | None
    current_snapshot: SubmissionSnapshot | None = None
    current_review_case: ReviewCase | None = None
    review_counts: ReviewCounts = Field(default_factory=ReviewCounts)


class PluginSubmissionDetail(PluginSubmission):
    snapshots: list[SubmissionSnapshot] = Field(default_factory=list)
    review_cases: list[ReviewCase] = Field(default_factory=list)
    events: list[ReviewEvent] = Field(default_factory=list)


class ReviewOverview(BaseModel):
    draft: int = 0
    submitted: int = 0
    in_review: int = 0
    closed: int = 0
    approved: int = 0
    rejected: int = 0
    unresolved_critical: int = 0
    unresolved_major: int = 0
