"""
基于沙箱的 AI 审核服务
在隔离环境中执行 AI 审核操作
"""
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.services.ai_sandbox_service import ai_sandbox_service, SandboxStatus
from app.core.config import settings
from app.core.time import utc_now

logger = logging.getLogger(__name__)


class AIReviewServiceSandboxed:
    """
    基于沙箱的 AI 审核服务
    所有 AI 调用都在沙箱环境中执行
    """
    
    def __init__(self):
        self.sandbox = ai_sandbox_service
        self.model = getattr(settings, 'AI_MODEL', 'gpt-4')
    
    async def analyze_code(
        self,
        db_session,
        plugin_id: int,
        code_content: str,
        file_type: str = "python"
    ) -> Dict[str, Any]:
        """在沙箱中分析代码"""
        
        prompt = f"""
你是一位专业的代码审查专家。请对以下 {file_type} 代码进行全面分析：

代码内容：
```{file_type}
{code_content[:8000]}
```

请从以下几个方面进行评估，并返回 JSON 格式的结果：
{{
    "security_score": 0-100,
    "code_quality_score": 0-100,
    "performance_score": 0-100,
    "security_issues": ["问题1", "问题2"],
    "code_issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"],
    "overall_assessment": "总体评价",
    "recommendation": "approve|reject|needs_revision"
}}
"""
        
        result = await self.sandbox.safe_ai_call(
            db_session=db_session,
            plugin_id=plugin_id,
            prompt=prompt,
            task_type="code_analysis",
            temperature=0.3
        )
        
        if result["success"]:
            try:
                content = result["result"]["choices"][0]["message"]["content"]
                return json.loads(content)
            except (KeyError, json.JSONDecodeError) as e:
                logger.error(f"解析 AI 响应失败: {e}")
                return {
                    "error": "解析响应失败",
                    "raw_response": result.get("result")
                }
        else:
            return {
                "error": result.get("error", "未知错误"),
                "task_id": result.get("task_id")
            }
    
    async def review_plugin_manifest(
        self,
        db_session,
        plugin_id: int,
        manifest: Dict[str, Any]
    ) -> Dict[str, Any]:
        """在沙箱中审核插件清单"""
        
        manifest_json = json.dumps(manifest, indent=2, ensure_ascii=False)
        
        prompt = f"""
请审核以下插件清单文件，评估其完整性和规范性：

```json
{manifest_json}
```

请检查以下项目：
1. 必需字段是否完整（name, version, description, author）
2. 版本号格式是否正确
3. 描述是否清晰完整
4. 依赖项是否合理
5. 权限声明是否明确

返回 JSON 格式：
{{
    "completeness_score": 0-100,
    "documentation_score": 0-100,
    "missing_fields": ["字段名"],
    "issues": ["问题描述"],
    "suggestions": ["改进建议"],
    "recommendation": "approve|reject|needs_revision"
}}
"""
        
        result = await self.sandbox.safe_ai_call(
            db_session=db_session,
            plugin_id=plugin_id,
            prompt=prompt,
            task_type="manifest_review",
            temperature=0.3
        )
        
        if result["success"]:
            try:
                content = result["result"]["choices"][0]["message"]["content"]
                return json.loads(content)
            except (KeyError, json.JSONDecodeError) as e:
                return {"error": "解析响应失败"}
        else:
            return {"error": result.get("error", "未知错误")}
    
    async def comprehensive_review(
        self,
        db_session,
        plugin_id: int,
        manifest: Optional[Dict[str, Any]],
        readme: str,
        code_files: List[Dict[str, str]],
        repo_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        在沙箱中执行综合审核
        
        这是一个长时间运行的任务，会在沙箱中超时控制
        """
        
        # 准备代码摘要
        code_summary = ""
        for file_info in code_files[:5]:
            code_summary += f"\n\n文件: {file_info['path']}\n"
            code_summary += f"```\n{file_info['content'][:2000]}\n```"
        
        manifest_json = json.dumps(manifest, indent=2, ensure_ascii=False) if manifest else "未提供"
        repo_info_json = json.dumps(repo_info, indent=2, ensure_ascii=False) if repo_info else "未提供"
        
        prompt = f"""
请对以下插件进行全面的综合审核：

## 插件清单
```json
{manifest_json}
```

## README
```markdown
{readme[:3000]}
```

## 代码文件
{code_summary}

## 仓库信息
```json
{repo_info_json}
```

请从以下维度进行评估，并返回详细的 JSON 报告：
{{
    "overall_score": 0-100,
    "security_assessment": {{
        "score": 0-100,
        "risks": ["风险1", "风险2"],
        "safe": true/false
    }},
    "code_quality": {{
        "score": 0-100,
        "strengths": ["优点1"],
        "weaknesses": ["缺点1"]
    }},
    "documentation": {{
        "score": 0-100,
        "completeness": "complete|partial|minimal"
    }},
    "functionality": {{
        "score": 0-100,
        "assessment": "功能评估"
    }},
    "detailed_findings": [
        {{
            "category": "security|quality|documentation|other",
            "severity": "critical|high|medium|low",
            "description": "问题描述",
            "suggestion": "修复建议"
        }}
    ],
    "recommendation": "approve|reject|needs_revision|manual_review",
    "reasoning": "推荐理由的详细说明"
}}

注意：
- critical 级别的问题必须修复
- 如果存在任何安全风险，建议 reject 或 manual_review
- 如果文档严重缺失，建议 needs_revision
"""
        
        # 在沙箱中执行（有超时保护）
        result = await self.sandbox.safe_ai_call(
            db_session=db_session,
            plugin_id=plugin_id,
            prompt=prompt,
            task_type="comprehensive_review",
            temperature=0.2,
            max_tokens=4000
        )
        
        if result["success"]:
            try:
                content = result["result"]["choices"][0]["message"]["content"]
                review_result = json.loads(content)
                
                # 添加元数据
                review_result["reviewed_at"] = utc_now().isoformat()
                review_result["model"] = self.model
                review_result["task_id"] = result.get("task_id")
                review_result["execution_time"] = result.get("execution_time")
                
                # 计算最终评分
                final_result = self._calculate_final_score(review_result)
                review_result.update(final_result)
                
                return review_result
                
            except (KeyError, json.JSONDecodeError) as e:
                logger.error(f"解析综合审核响应失败: {e}")
                return {
                    "error": "解析响应失败",
                    "raw_response": result.get("result"),
                    "task_id": result.get("task_id")
                }
        else:
            return {
                "error": result.get("error", "未知错误"),
                "task_id": result.get("task_id"),
                "execution_time": result.get("execution_time")
            }
    
    def _calculate_final_score(self, review_result: Dict[str, Any]) -> Dict[str, Any]:
        """计算最终评分"""
        scores = {
            "security": review_result.get("security_assessment", {}).get("score", 0),
            "code_quality": review_result.get("code_quality", {}).get("score", 0),
            "documentation": review_result.get("documentation", {}).get("score", 0),
            "functionality": review_result.get("functionality", {}).get("score", 0),
        }
        
        # 加权计算
        weights = {
            "security": 0.4,
            "code_quality": 0.25,
            "documentation": 0.2,
            "functionality": 0.15
        }
        
        weighted_score = sum(scores[k] * weights[k] for k in scores)
        
        # 根据关键问题调整
        findings = review_result.get("detailed_findings", [])
        critical_count = sum(1 for f in findings if f.get("severity") == "critical")
        high_count = sum(1 for f in findings if f.get("severity") == "high")
        
        if critical_count > 0:
            final_score = min(weighted_score, 40)
            recommendation = "reject"
        elif high_count > 2:
            final_score = min(weighted_score, 60)
            recommendation = "needs_revision"
        else:
            final_score = weighted_score
            recommendation = review_result.get("recommendation", "manual_review")
        
        return {
            "final_score": round(final_score, 2),
            "component_scores": scores,
            "critical_issues": critical_count,
            "high_issues": high_count,
            "recommendation": recommendation,
            "grading": self._get_grade(final_score)
        }
    
    def _get_grade(self, score: float) -> str:
        """根据分数获取等级"""
        if score >= 90:
            return "S"
        elif score >= 85:
            return "A"
        elif score >= 75:
            return "B"
        elif score >= 65:
            return "C"
        else:
            return "D"
    
    async def get_sandbox_stats(self) -> Dict[str, Any]:
        """获取沙箱统计信息"""
        return await self.sandbox.get_sandbox_stats()
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return await self.sandbox.get_task_status(task_id)


# 全局沙箱化审核服务实例
ai_review_service_sandboxed = AIReviewServiceSandboxed()
