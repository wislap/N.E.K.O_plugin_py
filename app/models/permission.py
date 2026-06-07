"""
权限系统模型
支持权限组、权限组合、权限继承、树权限
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, Text, and_
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.time import utc_now


RETIRED_PERMISSION_CODES = {"system:permission"}


# 权限组与子权限关联表
permission_group_items = Table(
    'permission_group_items',
    Base.metadata,
    Column('group_id', Integer, ForeignKey('permission_groups.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True)
)

# 权限组继承关联表（树权限）
permission_group_inheritance = Table(
    'permission_group_inheritance',
    Base.metadata,
    Column('parent_group_id', Integer, ForeignKey('permission_groups.id'), primary_key=True),
    Column('child_group_id', Integer, ForeignKey('permission_groups.id'), primary_key=True)
)

# 用户与权限组关联表
user_permission_groups = Table(
    'user_permission_groups',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('permission_groups.id'), primary_key=True)
)


class Permission(Base):
    """子权限模型 - 最细粒度的权限单位"""
    __tablename__ = 'permissions'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 权限标识
    code = Column(String(100), unique=True, nullable=False, index=True)  # 权限代码，如: plugin:review
    name = Column(String(100), nullable=False)  # 权限名称
    description = Column(Text, nullable=True)  # 权限描述
    
    # 权限分类
    category = Column(String(50), nullable=False, index=True)  # system/plugin/ai
    
    # 状态
    is_active = Column(Boolean, default=True)
    
    # 时间戳
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # 关系
    groups = relationship(
        'PermissionGroup',
        secondary=permission_group_items,
        back_populates='permissions'
    )
    
    def __repr__(self):
        return f"<Permission(code='{self.code}', name='{self.name}')>"


class PermissionGroup(Base):
    """权限组模型 - 包含多个子权限，支持树形结构和继承"""
    __tablename__ = 'permission_groups'
    RETIRED_PERMISSION_CODES = RETIRED_PERMISSION_CODES
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 权限组标识
    code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # 树权限结构
    parent_id = Column(Integer, ForeignKey('permission_groups.id'), nullable=True, index=True)
    
    # 权限组类型
    group_type = Column(String(50), default='custom')  # system/custom/role
    level = Column(Integer, default=10, nullable=False)  # 管理等级，越高越能管理更低等级用户/角色
    
    # 状态
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)  # 系统内置权限组，不可删除
    
    # 时间戳
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # 关系
    permissions = relationship(
        'Permission',
        secondary=permission_group_items,
        secondaryjoin=lambda: and_(
            permission_group_items.c.permission_id == Permission.id,
            Permission.is_active == True,
            Permission.code.notin_(RETIRED_PERMISSION_CODES),
        ),
        back_populates='groups'
    )
    
    # 树形关系 - 使用 backref 简化
    children = relationship(
        'PermissionGroup',
        backref='parent',
        remote_side=[id]
    )
    
    # 继承的权限组（额外继承其他组的权限）
    inherited_groups = relationship(
        'PermissionGroup',
        secondary=permission_group_inheritance,
        primaryjoin=id == permission_group_inheritance.c.child_group_id,
        secondaryjoin=id == permission_group_inheritance.c.parent_group_id,
        backref='inherited_by'
    )
    
    # 关联的用户
    users = relationship(
        'User',
        secondary=user_permission_groups,
        back_populates='permission_groups'
    )
    
    def __repr__(self):
        return f"<PermissionGroup(code='{self.code}', name='{self.name}')>"
    
    def get_all_permissions(self, visited=None):
        """
        获取权限组的所有权限（包括继承的）
        使用 DFS 避免循环继承
        """
        if visited is None:
            visited = set()
        
        if self.id in visited:
            return set()
        
        visited.add(self.id)
        
        all_permissions = {
            permission for permission in self.permissions
            if permission.is_active and permission.code not in self.RETIRED_PERMISSION_CODES
        }
        
        # 添加直接继承的权限组的权限
        for inherited_group in self.inherited_groups:
            if inherited_group.is_active:
                all_permissions.update(inherited_group.get_all_permissions(visited))
        
        # 添加父级权限组的权限（树权限继承）
        if self.parent and self.parent.is_active:
            all_permissions.update(self.parent.get_all_permissions(visited))
        
        return all_permissions
    
    def get_all_permission_codes(self):
        """获取所有权限代码"""
        return {p.code for p in self.get_all_permissions()}


class PermissionAuditLog(Base):
    """权限操作审计日志"""
    __tablename__ = 'permission_audit_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 操作信息
    action = Column(String(50), nullable=False)  # create/update/delete/grant/revoke
    target_type = Column(String(50), nullable=False)  # permission/group/user
    target_id = Column(Integer, nullable=False)
    
    # 操作人
    operator_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # 操作详情
    details = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=utc_now)
    
    def __repr__(self):
        return f"<PermissionAuditLog(action='{self.action}', target_type='{self.target_type}')>"
