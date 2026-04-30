from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # 用户信息
    display_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(String(500), nullable=True)
    website = Column(String(200), nullable=True)
    
    # 权限 - 保留 is_admin 作为快速判断，详细权限通过 permission_groups 管理
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)  # 超管拥有所有权限
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # 关系
    plugins = relationship("Plugin", back_populates="author")
    reviews = relationship("Review", back_populates="author")
    
    # 权限组关系
    permission_groups = relationship(
        'PermissionGroup',
        secondary='user_permission_groups',
        back_populates='users'
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"
    
    def has_permission(self, permission_code):
        """检查用户是否有指定权限"""
        # 超管拥有所有权限
        if self.is_admin:
            return True
        
        # 检查所有权限组
        for group in self.permission_groups:
            if not group.is_active:
                continue
            if permission_code in group.get_all_permission_codes():
                return True
        
        return False
    
    def has_any_permission(self, permission_codes):
        """检查用户是否有任意一个权限"""
        return any(self.has_permission(code) for code in permission_codes)
    
    def has_all_permissions(self, permission_codes):
        """检查用户是否拥有所有权限"""
        return all(self.has_permission(code) for code in permission_codes)
    
    def get_all_permissions(self):
        """获取用户的所有权限代码"""
        if self.is_admin:
            return {'*'}  # 超管返回通配符表示所有权限
        
        all_permissions = set()
        for group in self.permission_groups:
            if group.is_active:
                all_permissions.update(group.get_all_permission_codes())
        
        return all_permissions
