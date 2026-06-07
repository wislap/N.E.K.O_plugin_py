from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.time import utc_now


class User(Base):
    __tablename__ = "users"
    SUPER_ADMIN_LEVEL = 1000
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # 用户信息
    display_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(String(500), nullable=True)
    website = Column(String(200), nullable=True)
    
    # 权限 - is_admin 表示超级管理员，普通管理能力通过角色（permission_groups）管理
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)  # 超管拥有所有权限
    must_change_password = Column(Boolean, default=False, nullable=False)
    
    # 时间戳
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    last_login = Column(DateTime, nullable=True)
    email_verified_at = Column(DateTime, nullable=True)
    
    # 关系
    plugins = relationship("Plugin", back_populates="author")
    reviews = relationship("Review", back_populates="author")
    plugin_installs = relationship(
        "UserPluginInstall",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    plugin_likes = relationship(
        "PluginLike",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    
    # 权限组关系
    permission_groups = relationship(
        'PermissionGroup',
        secondary='user_permission_groups',
        back_populates='users'
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"
    
    def _usable_permission_groups(self):
        """可参与授权计算的激活角色；超级管理员身份只由 is_admin 表示。"""
        return [
            group for group in self.permission_groups
            if group.is_active and group.code != "super_admin"
        ]

    def has_permission(self, permission_code):
        """检查用户是否有指定权限"""
        # 超管拥有所有权限
        if self.is_admin:
            return True
        
        # 检查所有权限组
        for group in self._usable_permission_groups():
            if permission_code in group.get_all_permission_codes():
                return True
        
        return False
    
    def has_any_permission(self, permission_codes):
        """检查用户是否有任意一个权限"""
        return any(self.has_permission(code) for code in permission_codes)
    
    def has_all_permissions(self, permission_codes):
        """检查用户是否拥有所有权限"""
        return all(self.has_permission(code) for code in permission_codes)

    @property
    def is_email_verified(self) -> bool:
        return self.email_verified_at is not None

    def get_all_permissions(self):
        """获取用户的所有权限代码"""
        if self.is_admin:
            return {'*'}  # 超管返回通配符表示所有权限
        
        all_permissions = set()
        for group in self._usable_permission_groups():
            all_permissions.update(group.get_all_permission_codes())
        
        return all_permissions

    @property
    def effective_level(self) -> int:
        """用户管理等级；超级管理员固定最高，普通用户取激活角色中的最高等级。"""
        if self.is_admin:
            return self.SUPER_ADMIN_LEVEL

        levels = [group.level or 0 for group in self._usable_permission_groups()]
        return max(levels, default=0)

    @property
    def level(self) -> int:
        return self.effective_level

    @property
    def role_summaries(self):
        """后台用户列表使用的角色摘要。"""
        return self._usable_permission_groups()

    @property
    def roles(self):
        return self.role_summaries
