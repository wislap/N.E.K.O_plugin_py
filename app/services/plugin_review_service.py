from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.plugin_review import PluginReview, PluginReviewHistory, ReviewStage
from app.models.plugin import Plugin, PluginStatus
from app.core.time import utc_now
from app.services.github_service import GitHubService
from app.services.ai_review_service import AIReviewService
from app.services.notification_service import NotificationService


class PluginReviewService:
    """插件审核流程服务"""
    
    def __init__(self):
        self.github_service = GitHubService()
        self.ai_service = AIReviewService()
    
    async def submit_for_review(
        self,
        db: AsyncSession,
        plugin_id: int,
        repo_url: str,
        repo_branch: str = "main",
        submitter_id: Optional[int] = None
    ) -> PluginReview:
        """提交插件进行审核"""
        # 检查是否已有进行中的审核
        result = await db.execute(
            select(PluginReview).where(
                PluginReview.plugin_id == plugin_id,
                PluginReview.stage.notin_([
                    ReviewStage.APPROVED,
                    ReviewStage.REJECTED
                ])
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError("该插件已有进行中的审核")
        
        # 创建审核记录
        review = PluginReview(
            plugin_id=plugin_id,
            repo_url=repo_url,
            repo_branch=repo_branch,
            stage=ReviewStage.SUBMITTED
        )
        
        db.add(review)
        await db.flush()
        
        # 记录历史
        await self._add_history(
            db, plugin_id, review.id, None, ReviewStage.SUBMITTED,
            "插件提交审核", submitter_id, "user"
        )
        
        # 更新插件状态
        plugin = await db.get(Plugin, plugin_id)
        if plugin:
            plugin.status = PluginStatus.PENDING
        
        await db.commit()
        await db.refresh(review)
        return review
    
    async def fetch_repository(
        self,
        db: AsyncSession,
        review_id: int
    ) -> Dict[str, Any]:
        """拉取仓库代码进行分析"""
        review = await db.get(PluginReview, review_id)
        if not review:
            raise ValueError("审核记录不存在")
        
        # 更新阶段
        await self._transition_stage(
            db, review, ReviewStage.FETCHING, "开始拉取仓库代码"
        )
        
        try:
            # 获取仓库信息
            repo_info = await self.github_service.get_repo_info(review.repo_url)
            
            # 获取文件树
            tree = await self.github_service.get_repo_tree(
                review.repo_url, 
                recursive=True,
                ref=review.repo_branch
            )
            
            # 获取关键文件
            files_data = []
            
            # 获取清单文件
            manifest = await self.github_service.get_plugin_manifest(
                review.repo_url, 
                review.repo_branch
            )
            
            # 获取 README
            readme = await self.github_service.get_readme(
                review.repo_url, 
                review.repo_branch
            )
            
            # 获取主要代码文件（最多5个）
            code_extensions = ['.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c']
            code_files = [
                item for item in tree 
                if any(item['path'].endswith(ext) for ext in code_extensions)
                and item['type'] == 'blob'
            ][:5]
            
            for file_item in code_files:
                try:
                    content = await self.github_service.get_file_content(
                        review.repo_url,
                        file_item['path'],
                        review.repo_branch
                    )
                    files_data.append({
                        "path": file_item['path'],
                        "content": content
                    })
                except Exception:
                    continue
            
            # 更新阶段
            await self._transition_stage(
                db, review, ReviewStage.FETCHED, "仓库代码拉取完成"
            )
            
            review.fetched_at = utc_now()
            await db.commit()
            
            return {
                "repo_info": repo_info,
                "manifest": manifest,
                "readme": readme,
                "code_files": files_data,
                "tree": tree
            }
            
        except Exception as e:
            await self._transition_stage(
                db, review, ReviewStage.SUBMITTED, f"拉取失败: {str(e)}"
            )
            raise ValueError(f"拉取仓库失败: {str(e)}")
    
    async def perform_ai_review(
        self,
        db: AsyncSession,
        review_id: int
    ) -> Dict[str, Any]:
        """执行 AI 审核"""
        review = await db.get(PluginReview, review_id)
        if not review:
            raise ValueError("审核记录不存在")
        
        # 更新阶段
        await self._transition_stage(
            db, review, ReviewStage.AI_REVIEWING, "AI 开始审核"
        )
        
        try:
            # 拉取代码
            repo_data = await self.fetch_repository(db, review_id)
            
            # 执行 AI 审核
            ai_result = await self.ai_service.comprehensive_review(
                manifest=repo_data.get("manifest"),
                readme=repo_data.get("readme", ""),
                code_files=repo_data.get("code_files", []),
                repo_info=repo_data.get("repo_info")
            )
            
            # 计算最终评分
            final_score = self.ai_service.calculate_final_score(ai_result)
            
            # 更新审核记录
            review.ai_review_result = ai_result
            review.ai_score = int(final_score["final_score"])
            review.ai_recommendation = final_score["recommendation"]
            review.ai_reviewed_at = utc_now()
            
            # 根据 AI 建议更新阶段
            if final_score["recommendation"] == "needs_revision":
                review.stage = ReviewStage.NEEDS_REVISION
                review.review_feedback = self._format_feedback(ai_result)
            elif final_score["recommendation"] == "reject":
                review.stage = ReviewStage.REJECTED
                review.review_feedback = self._format_feedback(ai_result)
                review.completed_at = utc_now()
                
                # 更新插件状态
                plugin = await db.get(Plugin, review.plugin_id)
                if plugin:
                    plugin.status = PluginStatus.REJECTED
            elif final_score["recommendation"] == "manual_review":
                review.stage = ReviewStage.MANUAL_REVIEWING
                review.review_feedback = self._format_feedback(ai_result)
            else:  # approve
                review.stage = ReviewStage.AI_APPROVED
                review.review_feedback = self._format_feedback(ai_result)
            
            await self._add_history(
                db, review.plugin_id, review.id,
                ReviewStage.AI_REVIEWING, review.stage,
                f"AI 审核完成，评分: {review.ai_score}，建议: {review.ai_recommendation}",
                None, "ai"
            )
            
            await db.commit()
            
            return {
                "review": review,
                "ai_result": ai_result,
                "final_score": final_score
            }
            
        except Exception as e:
            await self._transition_stage(
                db, review, ReviewStage.FETCHED, f"AI 审核失败: {str(e)}"
            )
            raise ValueError(f"AI 审核失败: {str(e)}")
    
    async def submit_revision(
        self,
        db: AsyncSession,
        review_id: int,
        revision_notes: str,
        submitter_id: Optional[int] = None
    ) -> PluginReview:
        """提交修改后的代码"""
        review = await db.get(PluginReview, review_id)
        if not review:
            raise ValueError("审核记录不存在")
        
        if review.stage != ReviewStage.NEEDS_REVISION:
            raise ValueError("当前状态不允许提交修改")
        
        review.revision_notes = revision_notes
        review.revision_submitted_at = utc_now()
        
        await self._transition_stage(
            db, review, ReviewStage.REVISION_SUBMITTED,
            f"修改已提交: {revision_notes}", submitter_id, "user"
        )
        
        # 重新进行 AI 审核
        return await self.perform_ai_review(db, review_id)
    
    async def manual_review(
        self,
        db: AsyncSession,
        review_id: int,
        decision: str,  # approve/reject/needs_revision
        notes: str,
        reviewer_id: int
    ) -> PluginReview:
        """人工审核"""
        review = await db.get(PluginReview, review_id)
        if not review:
            raise ValueError("审核记录不存在")
        
        if review.stage not in [ReviewStage.AI_APPROVED, ReviewStage.MANUAL_REVIEWING]:
            raise ValueError("当前状态不允许人工审核")
        
        review.manual_reviewer_id = reviewer_id
        review.manual_review_notes = notes
        review.manual_reviewed_at = utc_now()
        
        if decision == "approve":
            review.stage = ReviewStage.APPROVED
            review.completed_at = utc_now()
            
            # 更新插件状态
            plugin = await db.get(Plugin, review.plugin_id)
            if plugin:
                plugin.status = PluginStatus.APPROVED
                plugin.published_at = utc_now()
                
        elif decision == "reject":
            review.stage = ReviewStage.REJECTED
            review.completed_at = utc_now()
            
            # 更新插件状态
            plugin = await db.get(Plugin, review.plugin_id)
            if plugin:
                plugin.status = PluginStatus.REJECTED
                
        elif decision == "needs_revision":
            review.stage = ReviewStage.NEEDS_REVISION
            review.revision_requested_at = utc_now()
        
        await self._add_history(
            db, review.plugin_id, review.id,
            ReviewStage.MANUAL_REVIEWING, review.stage,
            f"人工审核: {decision} - {notes}", reviewer_id, "user"
        )
        
        await db.commit()
        await db.refresh(review)
        return review

    async def record_admin_decision(
        self,
        db: AsyncSession,
        plugin: Plugin,
        decision: str,
        reviewer_id: int,
        notes: str = ""
    ) -> Plugin:
        """记录管理员快速审核结果，并同步插件状态。"""
        if decision not in {"approve", "reject"}:
            raise ValueError("不支持的审核决定")

        result = await db.execute(
            select(PluginReview)
            .where(PluginReview.plugin_id == plugin.id)
            .order_by(desc(PluginReview.submitted_at), desc(PluginReview.id))
        )
        review = result.scalars().first()

        if not review:
            review = PluginReview(
                plugin_id=plugin.id,
                repo_url=plugin.repo_url,
                repo_branch=plugin.repo_branch or "main",
                stage=ReviewStage.SUBMITTED,
            )
            db.add(review)
            await db.flush()
            await self._add_history(
                db,
                plugin.id,
                review.id,
                None,
                ReviewStage.SUBMITTED,
                "插件进入管理员审核",
                reviewer_id,
                "user",
            )

        old_stage = review.stage
        now = utc_now()
        new_stage = ReviewStage.APPROVED if decision == "approve" else ReviewStage.REJECTED
        action_label = "通过" if decision == "approve" else "拒绝"

        review.stage = new_stage
        review.manual_reviewer_id = reviewer_id
        review.manual_review_notes = notes or None
        review.review_feedback = notes or review.review_feedback
        review.manual_reviewed_at = now
        review.completed_at = now

        if decision == "approve":
            plugin.status = PluginStatus.APPROVED
            plugin.published_at = now
            NotificationService.add(
                db,
                user_id=plugin.author_id,
                type="plugin_approved",
                title="插件审核通过",
                content=f"你的插件「{plugin.name}」已通过审核并上架。",
                target_url=f"/plugin/{plugin.id}",
            )
        else:
            plugin.status = PluginStatus.REJECTED
            NotificationService.add(
                db,
                user_id=plugin.author_id,
                type="plugin_rejected",
                title="插件审核未通过",
                content=notes or f"你的插件「{plugin.name}」未通过审核，请查看审核意见。",
                target_url="/my/plugins",
            )

        await self._add_history(
            db,
            plugin.id,
            review.id,
            old_stage,
            new_stage,
            f"管理员审核{action_label}" + (f": {notes}" if notes else ""),
            reviewer_id,
            "user",
        )

        await db.commit()
        await db.refresh(plugin)
        return plugin
    
    async def get_review_history(
        self,
        db: AsyncSession,
        plugin_id: int
    ) -> List[PluginReviewHistory]:
        """获取插件审核历史"""
        result = await db.execute(
            select(PluginReviewHistory)
            .where(PluginReviewHistory.plugin_id == plugin_id)
            .order_by(desc(PluginReviewHistory.created_at))
        )
        return list(result.scalars().all())
    
    async def get_active_review(
        self,
        db: AsyncSession,
        plugin_id: int
    ) -> Optional[PluginReview]:
        """获取进行中的审核"""
        result = await db.execute(
            select(PluginReview).where(
                PluginReview.plugin_id == plugin_id,
                PluginReview.stage.notin_([
                    ReviewStage.APPROVED,
                    ReviewStage.REJECTED
                ])
            )
        )
        return result.scalar_one_or_none()
    
    async def _transition_stage(
        self,
        db: AsyncSession,
        review: PluginReview,
        new_stage: ReviewStage,
        notes: str = "",
        operator_id: Optional[int] = None,
        operator_type: str = "system"
    ):
        """转换审核阶段"""
        old_stage = review.stage
        review.stage = new_stage
        
        await self._add_history(
            db, review.plugin_id, review.id,
            old_stage, new_stage, notes, operator_id, operator_type
        )
    
    async def _add_history(
        self,
        db: AsyncSession,
        plugin_id: int,
        review_id: int,
        from_stage: Optional[ReviewStage],
        to_stage: ReviewStage,
        notes: str = "",
        operator_id: Optional[int] = None,
        operator_type: str = "system"
    ):
        """添加历史记录"""
        history = PluginReviewHistory(
            plugin_id=plugin_id,
            review_id=review_id,
            from_stage=from_stage.value if from_stage else None,
            to_stage=to_stage.value,
            notes=notes,
            operator_id=operator_id,
            operator_type=operator_type
        )
        db.add(history)
    
    def _format_feedback(self, ai_result: Dict[str, Any]) -> str:
        """格式化 AI 反馈"""
        feedback_parts = []
        
        # 总体评价
        feedback_parts.append(f"总体评分: {ai_result.get('overall_score', 0)}/100")
        feedback_parts.append(f"评估结果: {ai_result.get('recommendation', 'unknown')}")
        feedback_parts.append("")
        
        # 详细发现
        findings = ai_result.get('detailed_findings', [])
        if findings:
            feedback_parts.append("详细发现:")
            for finding in findings:
                severity = finding.get('severity', 'low')
                category = finding.get('category', 'other')
                description = finding.get('description', '')
                suggestion = finding.get('suggestion', '')
                feedback_parts.append(f"  [{severity.upper()}] {category}: {description}")
                if suggestion:
                    feedback_parts.append(f"    建议: {suggestion}")
            feedback_parts.append("")
        
        # 推理说明
        reasoning = ai_result.get('reasoning', '')
        if reasoning:
            feedback_parts.append(f"审核说明: {reasoning}")
        
        return "\n".join(feedback_parts)
