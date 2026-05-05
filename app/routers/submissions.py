from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.plugin_submission import ReviewDecision, SubmissionStatus
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.plugin_submission import (
    PluginSubmission,
    PluginSubmissionDetail,
    SubmissionDraftCreate,
    SubmissionDraftUpdate,
    SubmissionRevisionCreate,
    SubmitRequest,
)
from app.services.submission_review_service import SubmissionFilters, SubmissionReviewService

router = APIRouter(prefix="/review/submissions", tags=["review-submissions"])
service = SubmissionReviewService()


def _bad_request(error: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


async def _require_owned_submission(
    db: AsyncSession,
    submission_id: int,
    current_user: User,
):
    submission = await service.get_submission(db, submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提交申请不存在")
    if submission.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有权限访问此提交申请")
    return submission


@router.post("/drafts", response_model=PluginSubmission, status_code=status.HTTP_201_CREATED)
async def create_submission_draft(
    data: SubmissionDraftCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        submission = await service.create_draft(db, author_id=current_user.id, data=data)
        return service.enrich_submission(submission)
    except ValueError as error:
        raise _bad_request(error)


@router.get("/mine", response_model=PaginatedResponse[PluginSubmission])
async def list_my_submissions(
    q: str | None = Query(None),
    submission_status: SubmissionStatus | None = Query(None, alias="status"),
    decision: ReviewDecision | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await service.list_submissions(
        db,
        filters=SubmissionFilters(q=q, status=submission_status, decision=decision),
        page=page,
        page_size=page_size,
        author_id=current_user.id,
    )
    result.items = [service.enrich_submission(item) for item in result.items]
    return result


@router.get("/{submission_id}", response_model=PluginSubmissionDetail)
async def get_submission_detail(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    submission, events = await service.get_submission_with_events(db, submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提交申请不存在")
    if submission.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有权限访问此提交申请")
    setattr(submission, "events", events)
    return service.enrich_submission(submission)


@router.put("/{submission_id}/draft", response_model=PluginSubmission)
async def update_submission_draft(
    submission_id: int,
    data: SubmissionDraftUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    submission = await _require_owned_submission(db, submission_id, current_user)
    try:
        updated = await service.update_draft(db, submission=submission, actor_id=current_user.id, data=data)
        return service.enrich_submission(updated)
    except ValueError as error:
        raise _bad_request(error)


@router.post("/{submission_id}/revision", response_model=PluginSubmissionDetail)
async def create_submission_revision(
    submission_id: int,
    data: SubmissionRevisionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    submission = await _require_owned_submission(db, submission_id, current_user)
    try:
        updated = await service.create_revision(
            db,
            submission=submission,
            actor_id=current_user.id,
            data=data,
        )
        detail, events = await service.get_submission_with_events(db, updated.id)
        if detail is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提交申请不存在")
        setattr(detail, "events", events)
        return service.enrich_submission(detail)
    except ValueError as error:
        raise _bad_request(error)


@router.post("/{submission_id}/submit", response_model=PluginSubmission)
async def submit_submission(
    submission_id: int,
    data: SubmitRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    submission = await _require_owned_submission(db, submission_id, current_user)
    try:
        submitted = await service.submit(
            db,
            submission=submission,
            actor_id=current_user.id,
            note=data.note if data else None,
        )
        return service.enrich_submission(submitted)
    except ValueError as error:
        raise _bad_request(error)


@router.post("/{submission_id}/withdraw", response_model=PluginSubmission)
async def withdraw_submission(
    submission_id: int,
    data: SubmitRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    submission = await _require_owned_submission(db, submission_id, current_user)
    try:
        withdrawn = await service.withdraw(
            db,
            submission=submission,
            actor_id=current_user.id,
            note=data.note if data else None,
        )
        return service.enrich_submission(withdrawn)
    except ValueError as error:
        raise _bad_request(error)
