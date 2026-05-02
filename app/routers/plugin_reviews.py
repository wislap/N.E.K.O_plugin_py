from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.security import PermissionChecker, get_current_user
from app.services.plugin_review_service import PluginReviewService
from app.services.plugin_service import PluginService
from app.models.plugin_review import PluginReview
from app.models.user import User

router = APIRouter()
review_service = PluginReviewService()
require_plugin_review = PermissionChecker("plugin:review")


async def require_plugin_owner_or_admin(
    db: AsyncSession,
    plugin_id: int,
    current_user: User,
):
    plugin = await PluginService.get_plugin_by_id(db, plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="插件不存在"
        )
    if plugin.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有插件作者或管理员可以访问审核信息"
        )
    return plugin


@router.post("/plugins/{plugin_id}/submit-review", response_model=dict)
async def submit_for_review(
    plugin_id: int,
    repo_url: str,
    repo_branch: str = "main",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    提交插件进行 AI 审核
    """
    await require_plugin_owner_or_admin(db, plugin_id, current_user)
    
    try:
        review = await review_service.submit_for_review(
            db, plugin_id, repo_url, repo_branch, current_user.id
        )
        return {
            "review_id": review.id,
            "stage": review.stage,
            "message": "插件已提交审核"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/reviews/{review_id}/start-ai-review", response_model=dict)
async def start_ai_review(
    review_id: int,
    current_user: User = Depends(require_plugin_review),
    db: AsyncSession = Depends(get_db)
):
    """
    开始 AI 审核流程
    """
    try:
        result = await review_service.perform_ai_review(db, review_id)
        review = result["review"]
        final_score = result["final_score"]
        
        return {
            "review_id": review.id,
            "stage": review.stage,
            "ai_score": review.ai_score,
            "ai_recommendation": review.ai_recommendation,
            "final_score": final_score["final_score"],
            "grading": final_score["grading"],
            "feedback": review.review_feedback
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/reviews/{review_id}/submit-revision", response_model=dict)
async def submit_revision(
    review_id: int,
    revision_notes: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    提交修改后的代码重新审核
    """
    existing_review = await db.get(PluginReview, review_id)
    if not existing_review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="审核记录不存在"
        )
    await require_plugin_owner_or_admin(db, existing_review.plugin_id, current_user)

    try:
        review = await review_service.submit_revision(
            db, review_id, revision_notes, current_user.id
        )
        return {
            "review_id": review.id,
            "stage": review.stage,
            "message": "修改已提交，重新进行 AI 审核"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/reviews/{review_id}/manual-review", response_model=dict)
async def manual_review(
    review_id: int,
    decision: str,  # approve/reject/needs_revision
    notes: str,
    current_user: User = Depends(require_plugin_review),
    db: AsyncSession = Depends(get_db)
):
    """
    人工审核（需要管理员权限）
    """
    if decision not in ["approve", "reject", "needs_revision"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="decision 必须是 approve/reject/needs_revision 之一"
        )
    
    try:
        review = await review_service.manual_review(
            db, review_id, decision, notes, current_user.id
        )
        return {
            "review_id": review.id,
            "stage": review.stage,
            "decision": decision,
            "message": f"人工审核完成: {decision}"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/plugins/{plugin_id}/review-history", response_model=list)
async def get_review_history(
    plugin_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取插件审核历史
    """
    await require_plugin_owner_or_admin(db, plugin_id, current_user)
    history = await review_service.get_review_history(db, plugin_id)
    return [
        {
            "id": h.id,
            "from_stage": h.from_stage,
            "to_stage": h.to_stage,
            "notes": h.notes,
            "operator_type": h.operator_type,
            "created_at": h.created_at
        }
        for h in history
    ]


@router.get("/plugins/{plugin_id}/active-review", response_model=Optional[dict])
async def get_active_review(
    plugin_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取进行中的审核
    """
    await require_plugin_owner_or_admin(db, plugin_id, current_user)
    review = await review_service.get_active_review(db, plugin_id)
    if not review:
        return None
    
    return {
        "id": review.id,
        "stage": review.stage,
        "repo_url": review.repo_url,
        "repo_branch": review.repo_branch,
        "ai_score": review.ai_score,
        "ai_recommendation": review.ai_recommendation,
        "review_feedback": review.review_feedback,
        "revision_notes": review.revision_notes,
        "submitted_at": review.submitted_at,
        "ai_reviewed_at": review.ai_reviewed_at
    }
