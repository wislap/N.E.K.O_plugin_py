"""
权限服务
提供权限管理、权限检查、权限组管理等功能
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Set, Dict, Any
from datetime import datetime

from app.models.permission import (
    Permission,
    PermissionGroup,
    PermissionAuditLog,
    permission_group_items,
    user_permission_groups,
)
from app.models.user import User
from app.core.time import utc_now


class PermissionService:
    """权限服务"""
    
    # 系统预定义权限
    SYSTEM_PERMISSIONS = {
        # 系统权限
        'system:settings': {'name': '管理系统设置', 'category': 'system'},
        'system:smtp': {'name': 'SMTP设置', 'category': 'system'},
        'system:logs': {'name': '系统日志查看', 'category': 'system'},
        'system:permission': {'name': '权限管理', 'category': 'system'},
        'system:user': {'name': '用户管理', 'category': 'system'},
        
        # 插件权限
        'plugin:review': {'name': '插件审核', 'category': 'plugin'},
        'plugin:manage': {'name': '插件管理', 'category': 'plugin'},
        'plugin:submit_logs': {'name': '插件提交日志查看', 'category': 'plugin'},
        'plugin:ai_review': {'name': 'AI审核内容管理', 'category': 'plugin'},
        
        # AI管理权限
        'ai:settings': {'name': 'AI相关设置', 'category': 'ai'},
        'ai:api_uri': {'name': 'API URI管理', 'category': 'ai'},
        'ai:api_key': {'name': 'API密钥管理', 'category': 'ai'},
        'ai:prompt': {'name': 'AI提示词管理', 'category': 'ai'},
        'ai:model': {'name': 'AI模型设置', 'category': 'ai'},
        'ai:logs': {'name': 'AI模型调用日志查看', 'category': 'ai'},
        'ai:stats': {'name': 'AI模型调用次数统计', 'category': 'ai'},
        'ai:review_model': {'name': 'AI审查组调用的模型', 'category': 'ai'},
    }
    
    # 系统预定义权限组
    SYSTEM_GROUPS = {
        'super_admin': {
            'name': '超级管理员',
            'description': '拥有所有权限',
            'is_system': True,
            'permissions': []  # 空列表表示所有权限
        },
        'plugin_admin': {
            'name': '插件管理员',
            'description': '管理插件相关功能',
            'is_system': True,
            'permissions': [
                'plugin:review', 'plugin:manage', 'plugin:submit_logs', 'plugin:ai_review'
            ]
        },
        'ai_admin': {
            'name': 'AI管理员',
            'description': '管理AI相关设置',
            'is_system': True,
            'permissions': [
                'ai:settings', 'ai:api_uri', 'ai:api_key', 'ai:prompt',
                'ai:model', 'ai:logs', 'ai:stats', 'ai:review_model'
            ]
        },
        'system_admin': {
            'name': '系统管理员',
            'description': '管理系统设置',
            'is_system': True,
            'permissions': [
                'system:settings', 'system:smtp', 'system:logs',
                'system:permission', 'system:user'
            ]
        }
    }
    
    async def init_system_permissions(self, db: AsyncSession):
        """初始化系统权限"""
        # 创建系统权限
        for code, info in self.SYSTEM_PERMISSIONS.items():
            result = await db.execute(
                select(Permission).where(Permission.code == code)
            )
            if not result.scalar_one_or_none():
                permission = Permission(
                    code=code,
                    name=info['name'],
                    category=info['category'],
                    is_active=True
                )
                db.add(permission)
        
        await db.commit()
        
        # 创建系统权限组
        for code, info in self.SYSTEM_GROUPS.items():
            result = await db.execute(
                select(PermissionGroup).where(PermissionGroup.code == code)
            )
            group = result.scalar_one_or_none()
            
            if not group:
                group = PermissionGroup(
                    code=code,
                    name=info['name'],
                    description=info['description'],
                    is_system=info['is_system'],
                    is_active=True
                )
                db.add(group)
                await db.commit()
                await db.refresh(group)
            
            # 关联权限
            if info['permissions']:
                for perm_code in info['permissions']:
                    result = await db.execute(
                        select(Permission).where(Permission.code == perm_code)
                    )
                    permission = result.scalar_one_or_none()
                    if permission and permission not in group.permissions:
                        group.permissions.append(permission)
        
        await db.commit()
    
    # ========== 权限管理 ==========
    
    async def create_permission(
        self,
        db: AsyncSession,
        code: str,
        name: str,
        category: str,
        description: Optional[str] = None
    ) -> Permission:
        """创建新权限"""
        # 检查权限代码是否已存在
        result = await db.execute(
            select(Permission).where(Permission.code == code)
        )
        if result.scalar_one_or_none():
            raise ValueError(f"权限代码 '{code}' 已存在")
        
        permission = Permission(
            code=code,
            name=name,
            category=category,
            description=description,
            is_active=True
        )
        db.add(permission)
        await db.commit()
        await db.refresh(permission)
        
        # 记录审计日志
        await self._log_action(db, 'create', 'permission', permission.id, None)
        
        return permission
    
    async def get_permission_by_code(
        self,
        db: AsyncSession,
        code: str
    ) -> Optional[Permission]:
        """通过代码获取权限"""
        result = await db.execute(
            select(Permission).where(Permission.code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_permissions_by_category(
        self,
        db: AsyncSession,
        category: str
    ) -> List[Permission]:
        """获取分类下的所有权限"""
        result = await db.execute(
            select(Permission).where(
                and_(
                    Permission.category == category,
                    Permission.is_active == True
                )
            )
        )
        return list(result.scalars().all())
    
    async def get_all_permissions(self, db: AsyncSession) -> List[Permission]:
        """获取所有权限"""
        result = await db.execute(
            select(Permission).where(Permission.is_active == True)
        )
        return list(result.scalars().all())
    
    # ========== 权限组管理 ==========
    
    async def create_permission_group(
        self,
        db: AsyncSession,
        code: str,
        name: str,
        description: Optional[str] = None,
        parent_id: Optional[int] = None,
        permission_codes: Optional[List[str]] = None
    ) -> PermissionGroup:
        """创建权限组"""
        # 检查代码是否已存在
        result = await db.execute(
            select(PermissionGroup).where(PermissionGroup.code == code)
        )
        if result.scalar_one_or_none():
            raise ValueError(f"权限组代码 '{code}' 已存在")
        
        # 检查父级是否存在
        if parent_id:
            parent = await db.get(PermissionGroup, parent_id)
            if not parent:
                raise ValueError(f"父级权限组不存在")
        
        group = PermissionGroup(
            code=code,
            name=name,
            description=description,
            parent_id=parent_id,
            is_active=True,
            is_system=False
        )
        db.add(group)
        await db.flush()
        
        # 添加权限
        if permission_codes:
            permission_ids = []
            for perm_code in permission_codes:
                permission = await self.get_permission_by_code(db, perm_code)
                if permission:
                    permission_ids.append(permission.id)
            if permission_ids:
                await db.execute(
                    permission_group_items.insert(),
                    [
                        {"group_id": group.id, "permission_id": permission_id}
                        for permission_id in permission_ids
                    ],
                )
        
        # 记录审计日志
        await self._log_action(db, 'create', 'group', group.id, None)
        await db.commit()
        
        return await self.get_permission_group_by_id(db, group.id) or group
    
    async def get_permission_group_by_code(
        self,
        db: AsyncSession,
        code: str
    ) -> Optional[PermissionGroup]:
        """通过代码获取权限组"""
        result = await db.execute(
            select(PermissionGroup).where(PermissionGroup.code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_permission_group_by_id(
        self,
        db: AsyncSession,
        group_id: int
    ) -> Optional[PermissionGroup]:
        """通过ID获取权限组"""
        result = await db.execute(
            select(PermissionGroup)
            .options(selectinload(PermissionGroup.permissions))
            .where(PermissionGroup.id == group_id)
        )
        return result.scalar_one_or_none()
    
    async def update_permission_group(
        self,
        db: AsyncSession,
        group_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> PermissionGroup:
        """更新权限组"""
        group = await self.get_permission_group_by_id(db, group_id)
        if not group:
            raise ValueError("权限组不存在")
        
        if group.is_system:
            raise ValueError("系统权限组不能修改")
        
        if name is not None:
            group.name = name
        if description is not None:
            group.description = description
        if is_active is not None:
            group.is_active = is_active
        
        group.updated_at = utc_now()
        await db.commit()
        await db.refresh(group)
        
        # 记录审计日志
        await self._log_action(db, 'update', 'group', group.id, None)
        
        return group
    
    async def delete_permission_group(
        self,
        db: AsyncSession,
        group_id: int
    ):
        """删除权限组"""
        group = await self.get_permission_group_by_id(db, group_id)
        if not group:
            raise ValueError("权限组不存在")
        
        if group.is_system:
            raise ValueError("系统权限组不能删除")
        
        # 记录审计日志
        await self._log_action(db, 'delete', 'group', group.id, None)
        
        await db.delete(group)
        await db.commit()
    
    async def add_permissions_to_group(
        self,
        db: AsyncSession,
        group_id: int,
        permission_codes: List[str]
    ) -> PermissionGroup:
        """向权限组添加权限"""
        group = await self.get_permission_group_by_id(db, group_id)
        if not group:
            raise ValueError("权限组不存在")
        
        for code in permission_codes:
            permission = await self.get_permission_by_code(db, code)
            if permission and permission not in group.permissions:
                group.permissions.append(permission)
        
        await db.commit()
        await db.refresh(group)
        
        # 记录审计日志
        await self._log_action(
            db, 'grant', 'group', group.id,
            f"添加权限: {', '.join(permission_codes)}"
        )
        
        return group
    
    async def remove_permissions_from_group(
        self,
        db: AsyncSession,
        group_id: int,
        permission_codes: List[str]
    ) -> PermissionGroup:
        """从权限组移除权限"""
        group = await self.get_permission_group_by_id(db, group_id)
        if not group:
            raise ValueError("权限组不存在")
        
        for code in permission_codes:
            permission = await self.get_permission_by_code(db, code)
            if permission and permission in group.permissions:
                group.permissions.remove(permission)
        
        await db.commit()
        await db.refresh(group)
        
        # 记录审计日志
        await self._log_action(
            db, 'revoke', 'group', group.id,
            f"移除权限: {', '.join(permission_codes)}"
        )
        
        return group
    
    # ========== 权限继承 ==========
    
    async def set_group_inheritance(
        self,
        db: AsyncSession,
        group_id: int,
        inherit_from_ids: List[int]
    ) -> PermissionGroup:
        """设置权限组继承关系"""
        group = await self.get_permission_group_by_id(db, group_id)
        if not group:
            raise ValueError("权限组不存在")
        
        # 检查循环继承
        for parent_id in inherit_from_ids:
            if parent_id == group_id:
                raise ValueError("权限组不能继承自己")
            # TODO: 检查更深层次的循环继承
        
        # 清空现有继承
        group.inherited_groups = []
        
        # 设置新的继承关系
        for parent_id in inherit_from_ids:
            parent = await self.get_permission_group_by_id(db, parent_id)
            if parent:
                group.inherited_groups.append(parent)
        
        await db.commit()
        await db.refresh(group)
        
        return group
    
    # ========== 用户权限管理 ==========
    
    async def assign_groups_to_user(
        self,
        db: AsyncSession,
        user_id: int,
        group_ids: List[int]
    ) -> User:
        """为用户分配权限组"""
        user = await db.get(User, user_id)
        if not user:
            raise ValueError("用户不存在")

        existing_result = await db.execute(
            select(user_permission_groups.c.group_id)
            .join(
                PermissionGroup,
                user_permission_groups.c.group_id == PermissionGroup.id,
            )
            .where(
                user_permission_groups.c.user_id == user_id,
                PermissionGroup.is_system == True,
            )
        )
        preserved_group_ids = {row[0] for row in existing_result.all()}

        requested_group_ids = set()
        for group_id in group_ids:
            group = await self.get_permission_group_by_id(db, group_id)
            if group:
                requested_group_ids.add(group.id)

        target_group_ids = preserved_group_ids | requested_group_ids

        await db.execute(
            user_permission_groups.delete().where(
                user_permission_groups.c.user_id == user_id
            )
        )
        if target_group_ids:
            await db.execute(
                user_permission_groups.insert(),
                [
                    {"user_id": user_id, "group_id": group_id}
                    for group_id in target_group_ids
                ],
            )
        
        await db.commit()
        user = await self._get_user_with_permissions(db, user_id)
        
        # 记录审计日志
        await self._log_action(
            db, 'grant', 'user', user_id,
            f"分配权限组: {group_ids}"
        )
        
        return user
    
    async def get_user_permissions(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Set[str]:
        """获取用户的所有权限代码"""
        user = await self._get_user_with_permissions(db, user_id)
        if not user:
            return set()
        
        return user.get_all_permissions()
    
    async def check_user_permission(
        self,
        db: AsyncSession,
        user_id: int,
        permission_code: str
    ) -> bool:
        """检查用户是否有指定权限"""
        user = await self._get_user_with_permissions(db, user_id)
        if not user:
            return False
        
        return user.has_permission(permission_code)

    async def _get_user_with_permissions(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Optional[User]:
        result = await db.execute(
            select(User)
            .options(
                selectinload(User.permission_groups).selectinload(PermissionGroup.permissions),
                selectinload(User.permission_groups).selectinload(PermissionGroup.inherited_groups),
                selectinload(User.permission_groups).selectinload(PermissionGroup.parent),
            )
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    # ========== 审计日志 ==========
    
    async def _log_action(
        self,
        db: AsyncSession,
        action: str,
        target_type: str,
        target_id: int,
        details: Optional[str],
        operator_id: Optional[int] = None
    ):
        """记录权限操作审计日志"""
        log = PermissionAuditLog(
            action=action,
            target_type=target_type,
            target_id=target_id,
            operator_id=operator_id or 0,  # 系统操作时为0
            details=details
        )
        db.add(log)
        await db.commit()
    
    async def get_audit_logs(
        self,
        db: AsyncSession,
        target_type: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100
    ) -> List[PermissionAuditLog]:
        """获取审计日志"""
        query = select(PermissionAuditLog)
        
        if target_type:
            query = query.where(PermissionAuditLog.target_type == target_type)
        if action:
            query = query.where(PermissionAuditLog.action == action)
        
        query = query.order_by(PermissionAuditLog.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())
