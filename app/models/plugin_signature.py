from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class PluginSignature(Base):
    """插件代码签名记录"""
    __tablename__ = "plugin_signatures"
    
    id = Column(Integer, primary_key=True, index=True)
    plugin_id = Column(Integer, ForeignKey("plugins.id"), nullable=False)
    
    # 签名信息
    signature = Column(Text, nullable=False)  # Base64 编码的 EC 签名
    files_hash = Column(String(32), nullable=False)  # 文件组合 MD5 哈希
    files_md5 = Column(JSON, nullable=False)  # 每个文件的 MD5: [{"path": "...", "md5": "..."}]
    payload = Column(Text, nullable=False)  # 签名载荷
    
    # 签名元数据
    plugin_name = Column(String(100), nullable=False)
    version = Column(String(20), nullable=False)
    author = Column(String(100), nullable=False)
    repo_url = Column(String(500), nullable=False)
    
    # 使用的密钥对
    keypair_id = Column(Integer, ForeignKey("server_key_pairs.id"), nullable=False)
    
    # 签名状态
    is_valid = Column(Boolean, default=True)  # 签名是否有效
    revoked_at = Column(DateTime, nullable=True)  # 撤销时间
    revoke_reason = Column(Text, nullable=True)  # 撤销原因
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)  # 最后验证时间
    
    # 关系
    plugin = relationship("Plugin", back_populates="signatures")
    keypair = relationship("ServerKeyPair", back_populates="signatures")
    
    def __repr__(self):
        return f"<PluginSignature(id={self.id}, plugin_id={self.plugin_id}, version='{self.version}')>"


class ServerKeyPair(Base):
    """服务器密钥对（用于签名插件）"""
    __tablename__ = "server_key_pairs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 密钥信息
    name = Column(String(50), nullable=False, unique=True)  # 密钥名称
    public_key = Column(Text, nullable=False)  # 公钥 PEM
    private_key_encrypted = Column(Text, nullable=False)  # 加密存储的私钥
    
    # 密钥状态
    is_active = Column(Boolean, default=True)  # 是否激活
    is_default = Column(Boolean, default=False)  # 是否默认密钥
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)
    deactivated_at = Column(DateTime, nullable=True)
    
    # 关系
    signatures = relationship("PluginSignature", back_populates="keypair")
    
    def __repr__(self):
        return f"<ServerKeyPair(id={self.id}, name='{self.name}', is_active={self.is_active})>"
