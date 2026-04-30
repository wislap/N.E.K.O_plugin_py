"""
系统设置模型
用于存储管理后台配置，如 SMTP 设置
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime

from app.core.database import Base


class SystemSetting(Base):
    """系统设置"""
    __tablename__ = 'system_settings'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 设置键值
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    
    # 设置描述
    description = Column(String(500), nullable=True)
    
    # 是否加密存储（用于敏感信息如密码）
    is_encrypted = Column(Boolean, default=False)
    
    # 设置分组
    group = Column(String(50), default='general', index=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, nullable=True)  # 最后修改者ID
    
    def __repr__(self):
        return f"<SystemSetting(key='{self.key}', group='{self.group}')>"


class SMTPSettingKeys:
    """SMTP 设置键名常量"""
    HOST = 'smtp_host'
    PORT = 'smtp_port'
    USER = 'smtp_user'
    PASSWORD = 'smtp_password'
    TLS = 'smtp_tls'
    FROM = 'smtp_from'
    ENABLED = 'smtp_enabled'
