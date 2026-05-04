from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import PermissionChecker
from app.models.plugin_submission import ReviewCommentSeverity, ReviewDecision, SubmissionStatus
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.plugin_submission import (
    PluginSubmission,
    PluginSubmissionDetail,
    ReviewComment,
    ReviewCommentCreate,
    ReviewCommentUpdate,
    ReviewDecisionRequest,
    ReviewOverview,
    ReviewStartRequest,
)
from app.services.submission_review_service import SubmissionFilters, SubmissionReviewService

router = APIRouter(prefix="/review", tags=["admin-review"])
require_plugin_review = PermissionChecker("plugin:review")
service = SubmissionReviewService()


def _bad_request(error: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


async def _require_submission(db: AsyncSession, submission_id: int):
    submission = await service.get_submission(db, submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提交申请不存在")
    return submission


async def _require_case(db: AsyncSession, case_id: int):
    review_case = await service.get_case(db, case_id)
    if not review_case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审核案件不存在")
    return review_case


async def _require_comment(db: AsyncSession, comment_id: int):
    comment = await service.get_comment(db, comment_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审核评论不存在")
    return comment


@router.get("/overview", response_model=ReviewOverview)
async def get_review_overview(
    current_user: User = Depends(require_plugin_review),
    db: AsyncSession = Depends(get_db),
):
    return await service.overview(db)


@router.get("/submissions", response_model=PaginatedResponse[PluginSubmission])
async def list_review_submissions(
    q: str | None = Query(None),
    submission_status: SubmissionStatus | None = Query(None, alias="status"),
    decision: ReviewDecision | None = Query(None),
    severity: ReviewCommentSeverity | None = Query(None),
    unresolved_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_plugin_review),
    db: AsyncSession = Depends(get_db),
):
    result = await service.list_submissions(
        db,
        filters=SubmissionFilters(
            q=q,
            status=submission_status,
            decision=decision,
            severity=severity,
            unresolved_only=unresolved_only,
        ),
        page=page,
        page_size=page_size,
    )
    result.items = [service.enrich_submission(item) for item in result.items]
    return result


@router.get("/submissions/{submission_id}", response_model=PluginSubmissionDetail)
async def get_admin_submission_detail(
    submission_id: int,
    current_user: User = Depends(require_plugin_review),
    db: AsyncSession = Depends(get_db),
):
    submission, events = await service.get_submission_with_events(db, submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提交申请不存在")
    setattr(submission, "events", events)
    return service.enrich_submission(submission)


@router.post("/submissions/{submission_id}/start", response_model=PluginSubmission)
async def start_submission_review(
    submission_id: int,
    data: ReviewStartRequest | None = None,
    current_user: User = Depends(require_plugin_review),
    db: AsyncSession = Depends(get_db),
):
    submission = await _require_submission(db, submission_id)
    try:
        started = await service.start_review(
            db,
            submission=submission,
            reviewer_id=current_user.id,
            note=data.note if data else None,
        )
        return service.enrich_submission(started)
    except ValueError as error:
        raise _bad_request(error)


@router.post("/cases/{case_id}/comments", response_model=ReviewComment, status_code=status.HTTP_201_CREATED)
async def add_review_comment(
    case_id: int,
    data: ReviewCommentCreate,
    current_user: User = Depends(require_plugin_review),
    db: AsyncSession = Depends(get_db),
):
    review_case = await _require_case(db, case_id)
    try:
        return await service.add_comment(db, review_case=review_case, actor_id=current_user.id, data=data)
    except ValueError as error:
        raise _bad_request(error)


@router.patch("/comments/{comment_id}", response_model=ReviewComment)
async def update_review_comment(
    comment_id: int,
    data: ReviewCommentUpdate,
    current_user: User = Depends(require_plugin_review),
    db: AsyncSession = Depends(get_db),
):
    comment = await _require_comment(db, comment_id)
    try:
        return await service.update_comment(db, comment=comment, actor_id=current_user.id, data=data)
    except ValueError as error:
        raise _bad_request(error)


@router.post("/comments/{comment_id}/resolve", response_model=ReviewComment)
async def resolve_review_comment(
    comment_id: int,
    current_user: User = Depends(require_plugin_review),
    db: AsyncSession = Depends(get_db),
):
    comment = await _require_comment(db, comment_id)
    try:
        return await service.set_comment_resolved(db, comment=comment, actor_id=current_user.id, resolved=True)
    except ValueError as error:
        raise _bad_request(error)


@router.post("/comments/{comment_id}/reopen", response_model=ReviewComment)
async def reopen_review_comment(
    comment_id: int,
    current_user: User = Depends(require_plugin_review),
    db: AsyncSession = Depends(get_db),
):
    comment = await _require_comment(db, comment_id)
    try:
        return await service.set_comment_resolved(db, comment=comment, actor_id=current_user.id, resolved=False)
    except ValueError as error:
        raise _bad_request(error)


@router.post("/cases/{case_id}/approve", response_model=PluginSubmission)
async def approve_review_case(
    case_id: int,
    data: ReviewDecisionRequest | None = None,
    current_user: User = Depends(require_plugin_review),
    db: AsyncSession = Depends(get_db),
):
    review_case = await _require_case(db, case_id)
    try:
        approved = await service.approve_case(
            db,
            review_case=review_case,
            actor_id=current_user.id,
            summary=data.summary if data else None,
            force=data.force if data else False,
        )
        return service.enrich_submission(approved)
    except ValueError as error:
        raise _bad_request(error)


@router.post("/cases/{case_id}/reject", response_model=PluginSubmission)
async def reject_review_case(
    case_id: int,
    data: ReviewDecisionRequest | None = None,
    current_user: User = Depends(require_plugin_review),
    db: AsyncSession = Depends(get_db),
):
    review_case = await _require_case(db, case_id)
    try:
        rejected = await service.reject_case(
            db,
            review_case=review_case,
            actor_id=current_user.id,
            summary=data.summary if data else None,
        )
        return service.enrich_submission(rejected)
    except ValueError as error:
        raise _bad_request(error)


@router.post("/cases/{case_id}/close", response_model=PluginSubmission)
async def close_review_case(
    case_id: int,
    data: ReviewDecisionRequest | None = None,
    current_user: User = Depends(require_plugin_review),
    db: AsyncSession = Depends(get_db),
):
    review_case = await _require_case(db, case_id)
    try:
        closed = await service.close_case(
            db,
            review_case=review_case,
            actor_id=current_user.id,
            summary=data.summary if data else None,
        )
        return service.enrich_submission(closed)
    except ValueError as error:
        raise _bad_request(error)


@router.post("/submissions/{submission_id}/reopen", response_model=PluginSubmission)
async def reopen_review_case(
    submission_id: int,
    data: ReviewStartRequest | None = None,
    current_user: User = Depends(require_plugin_review),
    db: AsyncSession = Depends(get_db),
):
    submission = await _require_submission(db, submission_id)
    try:
        reopened = await service.reopen_case(
            db,
            submission=submission,
            actor_id=current_user.id,
            note=data.note if data else None,
        )
        return service.enrich_submission(reopened)
    except ValueError as error:
        raise _bad_request(error)
