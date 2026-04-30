"""
AI 沙箱日志模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean
from datetime import datetime

from app.core.database import Base


class AISandboxLog(Base):
    """AI 沙箱执行日志"""
    __tablename__ = 'ai_sandbox_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 任务信息
    task_id = Column(String(64), unique=True, nullable=False, index=True)
    plugin_id = Column(Integer, nullable=False, index=True)
    task_type = Column(String(50), nullable=False)
    
    # 执行信息
    status = Column(String(20), nullable=False)
    execution_time = Column(Float, nullable=True)  # 执行时间（秒）
    
    # 输入输出哈希（用于审计，不存储实际内容）
    input_hash = Column(String(64), nullable=True)
    output_hash = Column(String(64), nullable=True)
    
    # 错误信息
    error_message = Column(Text, nullable=True)
    
    # 资源使用
    memory_usage = Column(Integer, nullable=True)  # 内存使用（MB）
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<AISandboxLog(task_id='{self.task_id}', status='{self.status}')>"
