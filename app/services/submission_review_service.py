from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from urllib.parse import urlparse

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.time import utc_now
from app.models.plugin import Plugin, PluginStatus
from app.models.plugin_submission import (
    PluginReviewCase,
    PluginReviewComment,
    PluginReviewEvent,
    PluginSubmission,
    PluginSubmissionSnapshot,
    ReviewCaseStatus,
    ReviewCommentSeverity,
    ReviewDecision,
    ReviewEventType,
    SubmissionStatus,
)
from app.models.user import User
from app.models.zone import Zone
from app.schemas.common import PaginatedResponse
from app.schemas.plugin_submission import (
    ReviewCommentCreate,
    ReviewCommentUpdate,
    ReviewCounts,
    SubmissionDraftCreate,
    SubmissionDraftUpdate,
)
from app.services.transactions import commit_or_rollback
from app.utils.plugin_validator import validate_plugin_repo


@dataclass(frozen=True)
class SubmissionFilters:
    q: str | None = None
    status: SubmissionStatus | None = None
    decision: ReviewDecision | None = None
    severity: ReviewCommentSeverity | None = None
    unresolved_only: bool = False


class SubmissionReviewService:
    """GitHub-centered plugin submission and review workspace contract."""

    load_options = (
        selectinload(PluginSubmission.current_snapshot),
        selectinload(PluginSubmission.current_review_case).selectinload(PluginReviewCase.comments),
        selectinload(PluginSubmission.snapshots),
        selectinload(PluginSubmission.review_cases).selectinload(PluginReviewCase.comments),
    )

    async def create_draft(
        self,
        db: AsyncSession,
        *,
        author_id: int,
        data: SubmissionDraftCreate,
    ) -> PluginSubmission:
        self._validate_repo(data.repo_url)
        async with commit_or_rollback(db):
            submission = PluginSubmission(author_id=author_id, status=SubmissionStatus.DRAFT)
            db.add(submission)
            await db.flush()
            snapshot = self._build_snapshot(submission.id, 1, data)
            db.add(snapshot)
            await db.flush()
            submission.current_snapshot_id = snapshot.id
            self._add_event(
                db,
                submission_id=submission.id,
                actor_id=author_id,
                event_type=ReviewEventType.DRAFT_CREATED,
                payload={"snapshot_id": snapshot.id},
            )
        return await self._reload_submission(db, submission.id)

    async def update_draft(
        self,
        db: AsyncSession,
        *,
        submission: PluginSubmission,
        actor_id: int,
        data: SubmissionDraftUpdate,
    ) -> PluginSubmission:
        if submission.status != SubmissionStatus.DRAFT:
            raise ValueError("只有草稿状态可以更新")
        base = submission.current_snapshot
        if base is None:
            raise ValueError("申请缺少当前快照")

        merged = SubmissionDraftCreate(
            repo_url=data.repo_url if data.repo_url is not None else base.repo_url,
            plugin_name=data.plugin_name if data.plugin_name is not None else base.plugin_name,
            plugin_slug=data.plugin_slug if data.plugin_slug is not None else base.plugin_slug,
            description=data.description if data.description is not None else base.description,
            short_description=data.short_description if data.short_description is not None else base.short_description,
            zone_slug=data.zone_slug if data.zone_slug is not None else base.zone_slug,
            tags=data.tags if data.tags is not None else list(base.tags or []),
            submitted_ref=data.submitted_ref if data.submitted_ref is not None else base.submitted_ref,
            resolved_commit=data.resolved_commit if data.resolved_commit is not None else base.resolved_commit,
            commit_url=data.commit_url if data.commit_url is not None else base.commit_url,
            actions_run_url=data.actions_run_url if data.actions_run_url is not None else base.actions_run_url,
            artifact_url=data.artifact_url if data.artifact_url is not None else base.artifact_url,
            license_name=data.license_name if data.license_name is not None else base.license_name,
            metadata=data.metadata if data.metadata is not None else dict(base.snapshot_metadata or {}),
        )
        self._validate_repo(merged.repo_url)

        next_revision = len(submission.snapshots or []) + 1
        async with commit_or_rollback(db):
            snapshot = self._build_snapshot(submission.id, next_revision, merged)
            db.add(snapshot)
            await db.flush()
            submission.current_snapshot_id = snapshot.id
            submission.updated_at = utc_now()
            self._add_event(
                db,
                submission_id=submission.id,
                actor_id=actor_id,
                event_type=ReviewEventType.DRAFT_UPDATED,
                payload={"snapshot_id": snapshot.id, "revision_number": next_revision},
            )
        return await self._reload_submission(db, submission.id)

    async def submit(
        self,
        db: AsyncSession,
        *,
        submission: PluginSubmission,
        actor_id: int,
        note: str | None = None,
    ) -> PluginSubmission:
        if submission.status != SubmissionStatus.DRAFT:
            raise ValueError("只有草稿可以正式提交")
        if submission.current_snapshot is None:
            raise ValueError("申请缺少提交快照")
        async with commit_or_rollback(db):
            submission.status = SubmissionStatus.SUBMITTED
            submission.submitted_at = utc_now()
            submission.updated_at = utc_now()
            self._add_event(
                db,
                submission_id=submission.id,
                actor_id=actor_id,
                event_type=ReviewEventType.SUBMITTED,
                payload={"note": note, "snapshot_id": submission.current_snapshot_id},
            )
        return await self._reload_submission(db, submission.id)

    async def start_review(
        self,
        db: AsyncSession,
        *,
        submission: PluginSubmission,
        reviewer_id: int,
        note: str | None = None,
    ) -> PluginSubmission:
        if submission.status not in {SubmissionStatus.SUBMITTED, SubmissionStatus.IN_REVIEW}:
            raise ValueError("只有已提交的申请可以开始审核")
        if submission.current_snapshot_id is None:
            raise ValueError("申请缺少当前快照")
        if submission.current_review_case and submission.current_review_case.status == ReviewCaseStatus.OPEN:
            return submission

        async with commit_or_rollback(db):
            review_case = PluginReviewCase(
                submission_id=submission.id,
                snapshot_id=submission.current_snapshot_id,
                status=ReviewCaseStatus.OPEN,
                opened_by=reviewer_id,
                opened_at=utc_now(),
            )
            db.add(review_case)
            await db.flush()
            submission.status = SubmissionStatus.IN_REVIEW
            submission.current_review_case_id = review_case.id
            submission.updated_at = utc_now()
            self._add_event(
                db,
                submission_id=submission.id,
                case_id=review_case.id,
                actor_id=reviewer_id,
                event_type=ReviewEventType.REVIEW_STARTED,
                payload={"note": note, "snapshot_id": submission.current_snapshot_id},
            )
        return await self._reload_submission(db, submission.id)

    async def add_comment(
        self,
        db: AsyncSession,
        *,
        review_case: PluginReviewCase,
        actor_id: int,
        data: ReviewCommentCreate,
    ) -> PluginReviewComment:
        self._require_open_case(review_case)
        async with commit_or_rollback(db):
            comment = PluginReviewComment(
                case_id=review_case.id,
                author_id=actor_id,
                severity=data.severity,
                target_area=data.target_area,
                target_ref=data.target_ref,
                body=data.body,
                is_resolved=False,
            )
            db.add(comment)
            await db.flush()
            self._add_event(
                db,
                submission_id=review_case.submission_id,
                case_id=review_case.id,
                actor_id=actor_id,
                event_type=ReviewEventType.COMMENTED,
                payload={"comment_id": comment.id, "severity": data.severity.value},
            )
        await db.refresh(comment)
        return comment

    async def update_comment(
        self,
        db: AsyncSession,
        *,
        comment: PluginReviewComment,
        actor_id: int,
        data: ReviewCommentUpdate,
    ) -> PluginReviewComment:
        review_case = await self.get_case(db, comment.case_id)
        if review_case is None:
            raise ValueError("审核案件不存在")
        self._require_open_case(review_case)
        async with commit_or_rollback(db):
            if data.severity is not None:
                comment.severity = data.severity
            if data.target_area is not None:
                comment.target_area = data.target_area
            if data.target_ref is not None:
                comment.target_ref = data.target_ref
            if data.body is not None:
                comment.body = data.body
            comment.updated_at = utc_now()
            self._add_event(
                db,
                submission_id=review_case.submission_id,
                case_id=review_case.id,
                actor_id=actor_id,
                event_type=ReviewEventType.COMMENT_UPDATED,
                payload={"comment_id": comment.id},
            )
        await db.refresh(comment)
        return comment

    async def set_comment_resolved(
        self,
        db: AsyncSession,
        *,
        comment: PluginReviewComment,
        actor_id: int,
        resolved: bool,
    ) -> PluginReviewComment:
        review_case = await self.get_case(db, comment.case_id)
        if review_case is None:
            raise ValueError("审核案件不存在")
        self._require_open_case(review_case)
        async with commit_or_rollback(db):
            comment.is_resolved = resolved
            comment.resolved_by = actor_id if resolved else None
            comment.resolved_at = utc_now() if resolved else None
            comment.updated_at = utc_now()
            self._add_event(
                db,
                submission_id=review_case.submission_id,
                case_id=review_case.id,
                actor_id=actor_id,
                event_type=ReviewEventType.COMMENT_RESOLVED if resolved else ReviewEventType.COMMENT_REOPENED,
                payload={"comment_id": comment.id},
            )
        await db.refresh(comment)
        return comment

    async def approve_case(
        self,
        db: AsyncSession,
        *,
        review_case: PluginReviewCase,
        actor_id: int,
        summary: str | None = None,
        force: bool = False,
    ) -> PluginSubmission:
        self._require_open_case(review_case)
        counts = self.count_comments(review_case.comments)
        if counts.critical > 0:
            raise ValueError("仍有未解决的 critical 评论，不能通过")
        if counts.major > 0 and not force:
            raise ValueError("仍有未解决的 major 评论；如确认通过请使用 force=true")
        submission = await self.get_submission(db, review_case.submission_id)
        if submission is None or submission.current_snapshot is None:
            raise ValueError("申请不存在或缺少快照")

        async with commit_or_rollback(db):
            plugin = await self._ensure_approved_plugin(db, submission)
            review_case.status = ReviewCaseStatus.CLOSED
            review_case.decision = ReviewDecision.APPROVED
            review_case.closed_by = actor_id
            review_case.closed_at = utc_now()
            review_case.decision_summary = summary
            submission.plugin_id = plugin.id
            submission.status = SubmissionStatus.CLOSED
            submission.decision = ReviewDecision.APPROVED
            submission.closed_at = utc_now()
            submission.updated_at = utc_now()
            self._add_event(
                db,
                submission_id=submission.id,
                case_id=review_case.id,
                actor_id=actor_id,
                event_type=ReviewEventType.APPROVED,
                payload={"summary": summary, "plugin_id": plugin.id},
            )
        return await self._reload_submission(db, submission.id)

    async def reject_case(
        self,
        db: AsyncSession,
        *,
        review_case: PluginReviewCase,
        actor_id: int,
        summary: str | None = None,
    ) -> PluginSubmission:
        return await self._close_case(
            db,
            review_case=review_case,
            actor_id=actor_id,
            decision=ReviewDecision.REJECTED,
            event_type=ReviewEventType.REJECTED,
            summary=summary,
        )

    async def close_case(
        self,
        db: AsyncSession,
        *,
        review_case: PluginReviewCase,
        actor_id: int,
        summary: str | None = None,
    ) -> PluginSubmission:
        return await self._close_case(
            db,
            review_case=review_case,
            actor_id=actor_id,
            decision=ReviewDecision.CANCELED,
            event_type=ReviewEventType.CLOSED,
            summary=summary,
        )

    async def reopen_case(
        self,
        db: AsyncSession,
        *,
        submission: PluginSubmission,
        actor_id: int,
        note: str | None = None,
    ) -> PluginSubmission:
        if submission.status != SubmissionStatus.CLOSED:
            raise ValueError("只有已关闭的申请可以重新打开")
        if submission.current_snapshot_id is None:
            raise ValueError("申请缺少当前快照")
        async with commit_or_rollback(db):
            review_case = PluginReviewCase(
                submission_id=submission.id,
                snapshot_id=submission.current_snapshot_id,
                status=ReviewCaseStatus.OPEN,
                opened_by=actor_id,
                opened_at=utc_now(),
            )
            db.add(review_case)
            await db.flush()
            submission.status = SubmissionStatus.IN_REVIEW
            submission.decision = None
            submission.current_review_case_id = review_case.id
            submission.closed_at = None
            submission.updated_at = utc_now()
            self._add_event(
                db,
                submission_id=submission.id,
                case_id=review_case.id,
                actor_id=actor_id,
                event_type=ReviewEventType.REOPENED,
                payload={"note": note},
            )
        return await self._reload_submission(db, submission.id)

    async def withdraw(
        self,
        db: AsyncSession,
        *,
        submission: PluginSubmission,
        actor_id: int,
        note: str | None = None,
    ) -> PluginSubmission:
        if submission.status == SubmissionStatus.CLOSED:
            raise ValueError("已关闭的申请不能撤回")
        async with commit_or_rollback(db):
            if submission.current_review_case and submission.current_review_case.status == ReviewCaseStatus.OPEN:
                submission.current_review_case.status = ReviewCaseStatus.CLOSED
                submission.current_review_case.decision = ReviewDecision.CANCELED
                submission.current_review_case.closed_by = actor_id
                submission.current_review_case.closed_at = utc_now()
                submission.current_review_case.decision_summary = note
            submission.status = SubmissionStatus.CLOSED
            submission.decision = ReviewDecision.CANCELED
            submission.closed_at = utc_now()
            submission.updated_at = utc_now()
            self._add_event(
                db,
                submission_id=submission.id,
                case_id=submission.current_review_case_id,
                actor_id=actor_id,
                event_type=ReviewEventType.WITHDRAWN,
                payload={"note": note},
            )
        return await self._reload_submission(db, submission.id)

    async def list_submissions(
        self,
        db: AsyncSession,
        *,
        filters: SubmissionFilters,
        page: int = 1,
        page_size: int = 20,
        author_id: int | None = None,
    ) -> PaginatedResponse[PluginSubmission]:
        query = select(PluginSubmission).options(*self.load_options)
        count_query = select(func.count(PluginSubmission.id))
        conditions = []
        if author_id is not None:
            conditions.append(PluginSubmission.author_id == author_id)
        if filters.status is not None:
            conditions.append(PluginSubmission.status == filters.status)
        if filters.decision is not None:
            conditions.append(PluginSubmission.decision == filters.decision)
        if filters.q:
            query = query.join(
                PluginSubmissionSnapshot,
                PluginSubmission.current_snapshot_id == PluginSubmissionSnapshot.id,
            )
            count_query = count_query.join(
                PluginSubmissionSnapshot,
                PluginSubmission.current_snapshot_id == PluginSubmissionSnapshot.id,
            )
            like = f"%{filters.q}%"
            conditions.append(
                or_(
                    PluginSubmissionSnapshot.plugin_name.ilike(like),
                    PluginSubmissionSnapshot.plugin_slug.ilike(like),
                    PluginSubmissionSnapshot.repo_url.ilike(like),
                )
            )
        if filters.severity is not None or filters.unresolved_only:
            query = query.join(PluginReviewCase, PluginSubmission.current_review_case_id == PluginReviewCase.id)
            query = query.join(PluginReviewComment, PluginReviewComment.case_id == PluginReviewCase.id)
            count_query = count_query.join(PluginReviewCase, PluginSubmission.current_review_case_id == PluginReviewCase.id)
            count_query = count_query.join(PluginReviewComment, PluginReviewComment.case_id == PluginReviewCase.id)
            if filters.severity is not None:
                conditions.append(PluginReviewComment.severity == filters.severity)
            if filters.unresolved_only:
                conditions.append(PluginReviewComment.is_resolved.is_(False))
            query = query.distinct()
            count_query = count_query.with_only_columns(func.count(func.distinct(PluginSubmission.id)))

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        total = await db.scalar(count_query) or 0
        result = await db.execute(
            query.order_by(desc(PluginSubmission.updated_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(result.scalars().unique().all())
        total_pages = (total + page_size - 1) // page_size
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

    async def overview(self, db: AsyncSession) -> dict[str, int]:
        values = {key: 0 for key in ("draft", "submitted", "in_review", "closed", "approved", "rejected")}
        result = await db.execute(select(PluginSubmission.status, func.count()).group_by(PluginSubmission.status))
        for status, count in result.all():
            values[status.value] = count
        decision_result = await db.execute(select(PluginSubmission.decision, func.count()).group_by(PluginSubmission.decision))
        for decision, count in decision_result.all():
            if decision == ReviewDecision.APPROVED:
                values["approved"] = count
            elif decision == ReviewDecision.REJECTED:
                values["rejected"] = count
        values["unresolved_critical"] = await self._unresolved_count(db, ReviewCommentSeverity.CRITICAL)
        values["unresolved_major"] = await self._unresolved_count(db, ReviewCommentSeverity.MAJOR)
        return values

    async def get_submission(self, db: AsyncSession, submission_id: int) -> PluginSubmission | None:
        result = await db.execute(
            select(PluginSubmission)
            .options(
                *self.load_options,
                selectinload(PluginSubmission.review_cases).selectinload(PluginReviewCase.snapshot),
            )
            .where(PluginSubmission.id == submission_id)
        )
        return result.scalar_one_or_none()

    async def _reload_submission(self, db: AsyncSession, submission_id: int) -> PluginSubmission:
        submission = await self.get_submission(db, submission_id)
        if submission is None:
            raise RuntimeError(f"submission {submission_id} disappeared during transaction")
        return submission

    async def get_submission_with_events(self, db: AsyncSession, submission_id: int) -> tuple[PluginSubmission | None, list[PluginReviewEvent]]:
        submission = await self.get_submission(db, submission_id)
        if not submission:
            return None, []
        events = await db.execute(
            select(PluginReviewEvent)
            .where(PluginReviewEvent.submission_id == submission_id)
            .order_by(PluginReviewEvent.created_at)
        )
        return submission, list(events.scalars().all())

    async def get_case(self, db: AsyncSession, case_id: int) -> PluginReviewCase | None:
        result = await db.execute(
            select(PluginReviewCase)
            .options(selectinload(PluginReviewCase.comments), selectinload(PluginReviewCase.snapshot))
            .where(PluginReviewCase.id == case_id)
        )
        return result.scalar_one_or_none()

    async def get_comment(self, db: AsyncSession, comment_id: int) -> PluginReviewComment | None:
        return await db.get(PluginReviewComment, comment_id)

    @staticmethod
    def count_comments(comments: list[PluginReviewComment]) -> ReviewCounts:
        unresolved = [comment for comment in comments if not bool(comment.is_resolved)]
        counts = Counter(comment.severity for comment in unresolved)
        return ReviewCounts(
            critical=counts[ReviewCommentSeverity.CRITICAL],
            major=counts[ReviewCommentSeverity.MAJOR],
            minor=counts[ReviewCommentSeverity.MINOR],
            nitpick=counts[ReviewCommentSeverity.NITPICK],
            unresolved=len(unresolved),
        )

    def enrich_submission(self, submission: PluginSubmission) -> PluginSubmission:
        if submission.current_review_case:
            setattr(submission, "review_counts", self.count_comments(submission.current_review_case.comments or []))
        else:
            setattr(submission, "review_counts", ReviewCounts())
        return submission

    async def _close_case(
        self,
        db: AsyncSession,
        *,
        review_case: PluginReviewCase,
        actor_id: int,
        decision: ReviewDecision,
        event_type: ReviewEventType,
        summary: str | None,
    ) -> PluginSubmission:
        self._require_open_case(review_case)
        submission = await self.get_submission(db, review_case.submission_id)
        if submission is None:
            raise ValueError("申请不存在")
        async with commit_or_rollback(db):
            review_case.status = ReviewCaseStatus.CLOSED
            review_case.decision = decision
            review_case.closed_by = actor_id
            review_case.closed_at = utc_now()
            review_case.decision_summary = summary
            submission.status = SubmissionStatus.CLOSED
            submission.decision = decision
            submission.closed_at = utc_now()
            submission.updated_at = utc_now()
            self._add_event(
                db,
                submission_id=submission.id,
                case_id=review_case.id,
                actor_id=actor_id,
                event_type=event_type,
                payload={"summary": summary},
            )
        return await self._reload_submission(db, submission.id)

    async def _ensure_approved_plugin(self, db: AsyncSession, submission: PluginSubmission) -> Plugin:
        snapshot = submission.current_snapshot
        if snapshot is None:
            raise ValueError("申请缺少当前快照")
        if submission.plugin_id:
            plugin = await db.get(Plugin, submission.plugin_id)
            if not plugin:
                raise ValueError("绑定插件不存在")
            plugin.status = PluginStatus.APPROVED
            plugin.published_at = plugin.published_at or utc_now()
            return plugin

        existing = await db.scalar(select(Plugin).where(Plugin.slug == snapshot.plugin_slug))
        if existing:
            raise ValueError(f"插件 slug '{snapshot.plugin_slug}' 已存在")
        author = await db.get(User, submission.author_id)
        zone_id = None
        if snapshot.zone_slug:
            zone_id = await db.scalar(select(Zone.id).where(Zone.slug == snapshot.zone_slug))
        plugin = Plugin(
            name=snapshot.plugin_name,
            slug=snapshot.plugin_slug,
            description=snapshot.description,
            short_description=snapshot.short_description,
            author_id=submission.author_id,
            author_name=author.username if author else "",
            repo_url=snapshot.repo_url,
            zone_id=zone_id,
            tags=snapshot.tags or [],
            status=PluginStatus.APPROVED,
            published_at=utc_now(),
        )
        db.add(plugin)
        await db.flush()
        return plugin

    @staticmethod
    def _build_snapshot(
        submission_id: int,
        revision_number: int,
        data: SubmissionDraftCreate,
    ) -> PluginSubmissionSnapshot:
        owner, repo = SubmissionReviewService._parse_github_repo(data.repo_url)
        return PluginSubmissionSnapshot(
            submission_id=submission_id,
            revision_number=revision_number,
            repo_url=data.repo_url,
            repo_owner=owner,
            repo_name=repo,
            submitted_ref=data.submitted_ref,
            resolved_commit=data.resolved_commit,
            commit_url=data.commit_url,
            actions_run_url=data.actions_run_url,
            artifact_url=data.artifact_url,
            license_name=data.license_name,
            plugin_name=data.plugin_name,
            plugin_slug=data.plugin_slug,
            description=data.description,
            short_description=data.short_description,
            zone_slug=data.zone_slug,
            tags=data.tags,
            snapshot_metadata=data.metadata,
        )

    @staticmethod
    def _parse_github_repo(repo_url: str) -> tuple[str | None, str | None]:
        parsed = urlparse(repo_url)
        if parsed.netloc.lower() != "github.com":
            return None, None
        parts = [part for part in parsed.path.strip("/").split("/") if part]
        if len(parts) < 2:
            return None, None
        return parts[0], parts[1].removesuffix(".git")

    @staticmethod
    def _validate_repo(repo_url: str) -> None:
        valid, error = validate_plugin_repo(repo_url)
        if not valid:
            raise ValueError(f"仓库地址验证失败: {error}")

    @staticmethod
    def _require_open_case(review_case: PluginReviewCase) -> None:
        if review_case.status != ReviewCaseStatus.OPEN:
            raise ValueError("审核案件已关闭")

    @staticmethod
    def _add_event(
        db: AsyncSession,
        *,
        submission_id: int,
        event_type: ReviewEventType,
        actor_id: int | None = None,
        case_id: int | None = None,
        payload: dict | None = None,
    ) -> PluginReviewEvent:
        event = PluginReviewEvent(
            submission_id=submission_id,
            case_id=case_id,
            actor_id=actor_id,
            event_type=event_type,
            payload=payload or {},
        )
        db.add(event)
        return event

    @staticmethod
    async def _unresolved_count(db: AsyncSession, severity: ReviewCommentSeverity) -> int:
        result = await db.execute(
            select(func.count(PluginReviewComment.id)).where(
                PluginReviewComment.severity == severity,
                PluginReviewComment.is_resolved.is_(False),
            )
        )
        return result.scalar() or 0
