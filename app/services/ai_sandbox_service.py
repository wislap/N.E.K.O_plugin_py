"""
AI 审核沙箱服务
提供隔离的 AI 调用环境，防止安全问题
"""
import asyncio
import json
import logging
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import httpx

from app.core.config import settings
from app.core.time import utc_now
from app.models.ai_sandbox_log import AISandboxLog

logger = logging.getLogger(__name__)


class SandboxStatus(str, Enum):
    """沙箱任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class SandboxTask:
    """沙箱任务"""
    task_id: str
    plugin_id: int
    task_type: str
    status: SandboxStatus = SandboxStatus.PENDING
    created_at: datetime = field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0


class AISandboxService:
    """
    AI 审核沙箱服务
    
    功能：
    1. 隔离 AI 调用环境
    2. 限制执行时间和资源
    3. 记录所有操作日志
    4. 防止恶意代码执行
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'AI_API_KEY', None)
        self.api_base = getattr(settings, 'AI_API_BASE', 'https://api.openai.com/v1')
        self.model = getattr(settings, 'AI_MODEL', 'gpt-4')
        
        # 沙箱配置
        self.max_execution_time = getattr(settings, 'AI_SANDBOX_TIMEOUT', 300)  # 默认5分钟
        self.max_concurrent_tasks = getattr(settings, 'AI_MAX_CONCURRENT', 3)
        self.max_calls_per_day = getattr(settings, 'AI_MAX_CALLS_PER_DAY', 1000)
        
        # 任务管理
        self._tasks: Dict[str, SandboxTask] = {}
        self._semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        self._daily_calls = 0
        self._last_reset = utc_now()
        
        # 内容安全过滤规则
        self._blocked_patterns = [
            "import os",
            "import sys",
            "subprocess",
            "eval(",
            "exec(",
            "__import__",
            "compile(",
            "open(",
            "file(",
        ]
    
    def _generate_task_id(self, plugin_id: int, task_type: str) -> str:
        """生成任务ID"""
        timestamp = str(time.time())
        content = f"{plugin_id}:{task_type}:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _check_content_safety(self, content: str) -> tuple:
        """
        检查内容安全性
        返回: (是否安全, 发现的问题列表)
        """
        issues = []
        content_lower = content.lower()
        
        for pattern in self._blocked_patterns:
            if pattern.lower() in content_lower:
                issues.append(f"发现潜在风险代码: {pattern}")
        
        # 检查代码长度
        if len(content) > 100000:  # 100KB
            issues.append("代码超过最大长度限制")
        
        return len(issues) == 0, issues
    
    def _check_rate_limit(self) -> bool:
        """检查调用频率限制"""
        now = utc_now()
        
        # 重置每日计数
        if now.date() > self._last_reset.date():
            self._daily_calls = 0
            self._last_reset = now
        
        return self._daily_calls < self.max_calls_per_day
    
    async def _log_task_start(
        self,
        db_session,
        task: SandboxTask,
        input_content: str
    ):
        """记录任务开始"""
        input_hash = hashlib.sha256(input_content.encode()).hexdigest()
        
        log = AISandboxLog(
            task_id=task.task_id,
            plugin_id=task.plugin_id,
            task_type=task.task_type,
            status=task.status.value,
            input_hash=input_hash,
            created_at=task.created_at,
            started_at=task.started_at
        )
        db_session.add(log)
        await db_session.commit()
    
    async def _log_task_complete(
        self,
        db_session,
        task: SandboxTask,
        output_content: Optional[str] = None
    ):
        """记录任务完成"""
        output_hash = None
        if output_content:
            output_hash = hashlib.sha256(output_content.encode()).hexdigest()
        
        from sqlalchemy import select
        result = await db_session.execute(
            select(AISandboxLog).where(AISandboxLog.task_id == task.task_id)
        )
        log = result.scalar_one_or_none()
        
        if log:
            log.status = task.status.value
            log.execution_time = task.execution_time
            log.output_hash = output_hash
            log.error_message = task.error
            log.completed_at = task.completed_at
            await db_session.commit()
    
    async def execute_in_sandbox(
        self,
        db_session,
        plugin_id: int,
        task_type: str,
        operation: Callable,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        在沙箱中执行 AI 操作
        
        Args:
            db_session: 数据库会话
            plugin_id: 插件ID
            task_type: 任务类型
            operation: 要执行的操作函数
            *args, **kwargs: 传递给操作函数的参数
            
        Returns:
            执行结果
        """
        # 生成任务ID
        task_id = self._generate_task_id(plugin_id, task_type)
        
        # 创建任务
        task = SandboxTask(
            task_id=task_id,
            plugin_id=plugin_id,
            task_type=task_type
        )
        self._tasks[task_id] = task
        
        # 检查频率限制
        if not self._check_rate_limit():
            task.status = SandboxStatus.FAILED
            task.error = "超出每日调用限制"
            task.completed_at = utc_now()
            await self._log_task_complete(db_session, task)
            raise ValueError("超出每日 AI 调用限制")
        
        try:
            # 使用信号量限制并发
            async with self._semaphore:
                task.status = SandboxStatus.RUNNING
                task.started_at = utc_now()
                
                # 记录任务开始
                input_content = json.dumps({"args": str(args), "kwargs": str(kwargs)})
                await self._log_task_start(db_session, task, input_content)
                
                # 增加调用计数
                self._daily_calls += 1
                
                # 设置超时执行
                start_time = time.time()
                
                try:
                    # 在超时限制内执行操作
                    result = await asyncio.wait_for(
                        operation(*args, **kwargs),
                        timeout=self.max_execution_time
                    )
                    
                    task.status = SandboxStatus.SUCCESS
                    task.result = result
                    
                except asyncio.TimeoutError:
                    task.status = SandboxStatus.TIMEOUT
                    task.error = f"执行超时（超过 {self.max_execution_time} 秒）"
                    raise ValueError(task.error)
                
                except Exception as e:
                    task.status = SandboxStatus.FAILED
                    task.error = str(e)
                    raise
                
                finally:
                    task.execution_time = time.time() - start_time
                    task.completed_at = utc_now()
                    
                    # 记录任务完成
                    output_content = json.dumps(task.result) if task.result else None
                    await self._log_task_complete(db_session, task, output_content)
                
                return {
                    "success": True,
                    "task_id": task_id,
                    "execution_time": task.execution_time,
                    "result": task.result
                }
                
        except Exception as e:
            logger.error(f"沙箱任务执行失败: {task_id}, 错误: {e}")
            return {
                "success": False,
                "task_id": task_id,
                "error": str(e),
                "execution_time": task.execution_time if task.execution_time else 0
            }
    
    async def safe_ai_call(
        self,
        db_session,
        plugin_id: int,
        prompt: str,
        task_type: str = "code_review",
        temperature: float = 0.3,
        max_tokens: int = 4000
    ) -> Dict[str, Any]:
        """
        安全的 AI 调用（在沙箱中执行）
        
        Args:
            db_session: 数据库会话
            plugin_id: 插件ID
            prompt: 提示词
            task_type: 任务类型
            temperature: 温度参数
            max_tokens: 最大token数
        """
        if not self.api_key:
            raise ValueError("AI API 密钥未配置")
        
        # 检查内容安全
        is_safe, issues = self._check_content_safety(prompt)
        if not is_safe:
            return {
                "success": False,
                "error": f"内容安全检查失败: {', '.join(issues)}"
            }
        
        async def ai_operation():
            """实际的 AI 调用操作"""
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "你是一个安全的代码审查助手。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                return response.json()
        
        return await self.execute_in_sandbox(
            db_session,
            plugin_id,
            task_type,
            ai_operation
        )
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "plugin_id": task.plugin_id,
            "task_type": task.task_type,
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "execution_time": task.execution_time,
            "result": task.result,
            "error": task.error
        }
    
    async def get_sandbox_stats(self) -> Dict[str, Any]:
        """获取沙箱统计信息"""
        total_tasks = len(self._tasks)
        running_tasks = sum(1 for t in self._tasks.values() if t.status == SandboxStatus.RUNNING)
        pending_tasks = sum(1 for t in self._tasks.values() if t.status == SandboxStatus.PENDING)
        failed_tasks = sum(1 for t in self._tasks.values() if t.status == SandboxStatus.FAILED)
        
        return {
            "total_tasks": total_tasks,
            "running_tasks": running_tasks,
            "pending_tasks": pending_tasks,
            "failed_tasks": failed_tasks,
            "daily_calls": self._daily_calls,
            "max_calls_per_day": self.max_calls_per_day,
            "max_concurrent": self.max_concurrent_tasks,
            "max_execution_time": self.max_execution_time
        }


# 全局沙箱服务实例
ai_sandbox_service = AISandboxService()
