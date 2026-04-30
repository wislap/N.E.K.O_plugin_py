"""
JWT 密钥模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime

from app.core.database import Base


class JWTKeyRecord(Base):
    """JWT 密钥记录"""
    __tablename__ = 'jwt_keys'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 密钥信息
    key_id = Column(String(32), unique=True, nullable=False, index=True)  # 密钥标识
    secret_key = Column(String(255), nullable=False)  # 密钥值（加密存储）
    
    # 密钥状态
    is_active = Column(Boolean, default=True)  # 是否激活
    is_primary = Column(Boolean, default=False)  # 是否主密钥（用于签发新令牌）
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)
    deactivated_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<JWTKeyRecord(key_id='{self.key_id}', is_primary={self.is_primary})>"
