import httpx
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from app.core.config import settings
from app.core.time import utc_now

# 配置日志
logger = logging.getLogger(__name__)


class ReviewStatus(str, Enum):
    """AI 审核状态"""
    PENDING = "pending"           # 待审核
    FETCHING = "fetching"         # 拉取代码中
    ANALYZING = "analyzing"       # AI 分析中
    NEEDS_REVISION = "needs_revision"  # 需要修改
    APPROVED = "approved"         # AI 审核通过
    REJECTED = "rejected"         # AI 审核拒绝
    MANUAL_REVIEW = "manual_review"    # 转人工审核


class AIReviewService:
    """AI 插件审核服务"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'AI_API_KEY', None)
        self.api_base = getattr(settings, 'AI_API_BASE', 'https://api.openai.com/v1')
        self.model = getattr(settings, 'AI_MODEL', 'gpt-4')
        self.max_retries = 3
        self.retry_delay = 2  # 重试间隔秒数
    
    async def _call_api_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: dict,
        json_data: dict,
        timeout: float,
        operation_name: str = "API调用"
    ) -> Dict[str, Any]:
        """
        带重试机制的 API 调用
        
        Args:
            client: HTTP 客户端
            url: 请求 URL
            headers: 请求头
            json_data: 请求体
            timeout: 超时时间
            operation_name: 操作名称（用于日志）
            
        Returns:
            API 响应数据
            
        Raises:
            ValueError: 调用失败时抛出
        """
        last_exception = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"{operation_name} 尝试第 {attempt} 次")
                
                response = await client.post(
                    url,
                    headers=headers,
                    json=json_data,
                    timeout=timeout
                )
                response.raise_for_status()
                
                logger.info(f"{operation_name} 成功")
                return response.json()
                
            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(f"{operation_name} 第 {attempt} 次超时")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                    
            except httpx.HTTPStatusError as e:
                last_exception = e
                status_code = e.response.status_code
                
                # 5xx 错误重试
                if status_code >= 500:
                    logger.warning(f"{operation_name} 第 {attempt} 次失败，状态码: {status_code}")
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.retry_delay * attempt)
                        continue
                
                # 4xx 错误不重试
                logger.error(f"{operation_name} 客户端错误，状态码: {status_code}")
                raise ValueError(f"AI API 错误: {status_code}")
                
            except httpx.RequestError as e:
                last_exception = e
                logger.warning(f"{operation_name} 第 {attempt} 次网络错误: {str(e)}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                    
            except Exception as e:
                last_exception = e
                logger.error(f"{operation_name} 第 {attempt} 次未知错误: {str(e)}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
        
        # 所有重试都失败
        logger.error(f"{operation_name} 在 {self.max_retries} 次尝试后失败")
        raise ValueError(f"AI API 调用失败，请稍后重试")
    
    async def analyze_code(self, code_content: str, file_type: str = "python") -> Dict[str, Any]:
        """使用 AI 分析代码"""
        if not self.api_key:
            raise ValueError("AI API 密钥未配置")
        
        prompt = f"""
你是一位专业的代码审查专家。请对以下 {file_type} 代码进行全面分析：

代码内容：
```{file_type}
{code_content[:8000]}  # 限制代码长度
```

请从以下几个方面进行评估，并返回 JSON 格式的结果：
{{
    "security_score": 0-100,  // 安全性评分
    "code_quality_score": 0-100,  // 代码质量评分
    "performance_score": 0-100,  // 性能评分
    "security_issues": ["问题1", "问题2"],  // 安全问题列表
    "code_issues": ["问题1", "问题2"],  // 代码质量问题列表
    "suggestions": ["建议1", "建议2"],  // 改进建议
    "overall_assessment": "总体评价",
    "recommendation": "approve|reject|needs_revision"  // 建议操作
}}
"""
        
        async with httpx.AsyncClient() as client:
            result = await self._call_api_with_retry(
                client=client,
                url=f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json_data={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是一个专业的代码审查助手，只返回 JSON 格式的结果。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"}
                },
                timeout=60.0,
                operation_name="代码分析"
            )
            
            content = result["choices"][0]["message"]["content"]
            return json.loads(content)
    
    async def review_plugin_manifest(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """审核插件清单文件"""
        if not self.api_key:
            raise ValueError("AI API 密钥未配置")
        
        prompt = f"""
请审核以下插件清单文件，评估其完整性和规范性：

```json
{json.dumps(manifest, indent=2, ensure_ascii=False)}
```

请检查以下项目：
1. 必需字段是否完整（name, version, description, author）
2. 版本号格式是否正确（语义化版本）
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
        
        async with httpx.AsyncClient() as client:
            result = await self._call_api_with_retry(
                client=client,
                url=f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json_data={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是一个插件清单审核专家，只返回 JSON 格式的结果。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"}
                },
                timeout=30.0,
                operation_name="清单审核"
            )
            
            content = result["choices"][0]["message"]["content"]
            return json.loads(content)
    
    async def review_readme(self, readme_content: str) -> Dict[str, Any]:
        """审核 README 文档"""
        if not self.api_key:
            raise ValueError("AI API 密钥未配置")
        
        prompt = f"""
请审核以下 README 文档的质量：

```markdown
{readme_content[:5000]}
```

评估维度：
1. 安装说明是否清晰
2. 使用文档是否完整
3. 是否包含示例代码
4. 是否说明了配置选项
5. 是否提供了故障排除指南

返回 JSON 格式：
{{
    "documentation_score": 0-100,
    "missing_sections": ["缺失的章节"],
    "issues": ["问题描述"],
    "suggestions": ["改进建议"],
    "recommendation": "approve|needs_revision"
}}
"""
        
        async with httpx.AsyncClient() as client:
            result = await self._call_api_with_retry(
                client=client,
                url=f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json_data={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是一个技术文档审核专家，只返回 JSON 格式的结果。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"}
                },
                timeout=30.0,
                operation_name="README审核"
            )
            
            content = result["choices"][0]["message"]["content"]
            return json.loads(content)
    
    async def comprehensive_review(
        self,
        manifest: Optional[Dict[str, Any]],
        readme: str,
        code_files: List[Dict[str, str]],
        repo_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        综合审核插件
        
        Args:
            manifest: 插件清单
            readme: README 内容
            code_files: 代码文件列表 [{"path": "...", "content": "..."}]
            repo_info: 仓库信息
        """
        if not self.api_key:
            raise ValueError("AI API 密钥未配置")
        
        # 准备代码摘要
        code_summary = ""
        for file_info in code_files[:5]:  # 限制文件数量
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
    "overall_score": 0-100,  // 综合评分
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
        
        async with httpx.AsyncClient() as client:
            result = await self._call_api_with_retry(
                client=client,
                url=f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json_data={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是一个专业的插件审核专家，严格评估插件的安全性、质量和文档完整性。只返回 JSON 格式的结果。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"}
                },
                timeout=120.0,
                operation_name="综合审核"
            )
            
            content = result["choices"][0]["message"]["content"]
            review_result = json.loads(content)
            
            # 添加元数据
            review_result["reviewed_at"] = utc_now().isoformat()
            review_result["model"] = self.model
            
            return review_result
    
    def calculate_final_score(self, review_result: Dict[str, Any]) -> Dict[str, Any]:
        """计算最终评分"""
        scores = {
            "security": review_result.get("security_assessment", {}).get("score", 0),
            "code_quality": review_result.get("code_quality", {}).get("score", 0),
            "documentation": review_result.get("documentation", {}).get("score", 0),
            "functionality": review_result.get("functionality", {}).get("score", 0),
        }
        
        # 加权计算
        weights = {
            "security": 0.4,      # 安全性最重要
            "code_quality": 0.25,
            "documentation": 0.2,
            "functionality": 0.15
        }
        
        weighted_score = sum(scores[k] * weights[k] for k in scores)
        
        # 根据关键问题调整分数
        findings = review_result.get("detailed_findings", [])
        critical_count = sum(1 for f in findings if f.get("severity") == "critical")
        high_count = sum(1 for f in findings if f.get("severity") == "high")
        
        # 有严重问题直接降级
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
            return "A+"
        elif score >= 85:
            return "A"
        elif score >= 80:
            return "A-"
        elif score >= 75:
            return "B+"
        elif score >= 70:
            return "B"
        elif score >= 65:
            return "B-"
        elif score >= 60:
            return "C"
        else:
            return "F"
