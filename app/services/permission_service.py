"""
权限服务
提供权限管理、角色管理、权限检查等功能。
"""
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.time import utc_now
from app.models.permission import (
    Permission,
    PermissionAuditLog,
    PermissionGroup,
    RETIRED_PERMISSION_CODES as MODEL_RETIRED_PERMISSION_CODES,
    permission_group_items,
    user_permission_groups,
)
from app.models.user import User


class PermissionService:
    """权限服务"""

    SUPER_ADMIN_LEVEL = User.SUPER_ADMIN_LEVEL
    DEFAULT_ROLE_LEVEL = 10
    RESERVED_ROLE_CODES = {"super_admin"}
    RESERVED_PERMISSION_CODES = {"system:permission_definition"}
    RETIRED_PERMISSION_CODES = MODEL_RETIRED_PERMISSION_CODES

    # 系统预定义权限
    SYSTEM_PERMISSIONS: Dict[str, Dict[str, str]] = {
        # 系统权限
        "system:settings": {"name": "管理系统设置", "category": "system"},
        "system:smtp": {"name": "SMTP设置", "category": "system"},
        "system:logs": {"name": "系统日志查看", "category": "system"},
        "system:role": {"name": "角色管理", "category": "system"},
        "system:permission_definition": {"name": "权限定义管理", "category": "system"},
        "system:user": {"name": "用户管理", "category": "system"},

        # 插件权限
        "plugin:review": {"name": "插件审核", "category": "plugin"},
        "plugin:manage": {"name": "插件管理", "category": "plugin"},
        "plugin:category": {"name": "插件分类管理", "category": "plugin"},
        "plugin:zone": {"name": "插件分区管理", "category": "plugin"},
        "plugin:signature": {"name": "插件签名管理", "category": "plugin"},
        "plugin:submit_logs": {"name": "插件提交日志查看", "category": "plugin"},
        "plugin:ai_review": {"name": "AI审核内容管理", "category": "plugin"},

        # AI管理权限
        "ai:settings": {"name": "AI相关设置", "category": "ai"},
        "ai:api_uri": {"name": "API URI管理", "category": "ai"},
        "ai:api_key": {"name": "API密钥管理", "category": "ai"},
        "ai:prompt": {"name": "AI提示词管理", "category": "ai"},
        "ai:model": {"name": "AI模型设置", "category": "ai"},
        "ai:logs": {"name": "AI模型调用日志查看", "category": "ai"},
        "ai:stats": {"name": "AI模型调用次数统计", "category": "ai"},
        "ai:review_model": {"name": "AI审查组调用的模型", "category": "ai"},
    }

    # 系统预定义角色。真正的超级管理员只由 User.is_admin 表示。
    SYSTEM_GROUPS: Dict[str, Dict[str, Any]] = {
        "system_admin": {
            "name": "系统管理员",
            "description": "管理系统设置、用户与角色",
            "is_system": True,
            "level": 300,
            "permissions": [
                "system:settings",
                "system:smtp",
                "system:logs",
                "system:role",
                "system:user",
            ],
        },
        "plugin_admin": {
            "name": "插件管理员",
            "description": "管理插件相关功能",
            "is_system": True,
            "level": 200,
            "permissions": [
                "plugin:review",
                "plugin:manage",
                "plugin:category",
                "plugin:zone",
                "plugin:signature",
                "plugin:submit_logs",
                "plugin:ai_review",
            ],
        },
        "ai_admin": {
            "name": "AI管理员",
            "description": "管理AI相关设置",
            "is_system": True,
            "level": 200,
            "permissions": [
                "ai:settings",
                "ai:api_uri",
                "ai:api_key",
                "ai:prompt",
                "ai:model",
                "ai:logs",
                "ai:stats",
                "ai:review_model",
            ],
        },
    }

    async def init_system_permissions(self, db: AsyncSession):
        """初始化系统权限和内置角色。"""
        for code, info in self.SYSTEM_PERMISSIONS.items():
            result = await db.execute(select(Permission).where(Permission.code == code))
            permission = result.scalar_one_or_none()
            if permission is None:
                permission = Permission(
                    code=code,
                    name=info["name"],
                    category=info["category"],
                    is_active=True,
                )
                db.add(permission)
            else:
                permission.name = info["name"]
                permission.category = info["category"]
                permission.is_active = True

        await self._retire_legacy_permission_codes(db)
        await db.commit()

        for code, info in self.SYSTEM_GROUPS.items():
            result = await db.execute(
                select(PermissionGroup)
                .options(selectinload(PermissionGroup.permissions))
                .where(PermissionGroup.code == code)
            )
            group = result.scalar_one_or_none()

            if group is None:
                group = PermissionGroup(
                    code=code,
                    name=info["name"],
                    description=info["description"],
                    group_type="system",
                    level=info["level"],
                    is_system=info["is_system"],
                    is_active=True,
                )
                db.add(group)
                await db.flush()
            else:
                group.name = info["name"]
                group.description = info["description"]
                group.group_type = "system"
                group.level = info["level"]
                group.is_system = info["is_system"]
                group.is_active = True

            await self._replace_group_permissions(db, group.id, info["permissions"])

        await self._retire_legacy_super_admin_role(db)
        await self._retire_legacy_permission_codes(db)
        await db.commit()

    async def _retire_legacy_permission_codes(self, db: AsyncSession):
        result = await db.execute(
            select(Permission).where(Permission.code.in_(self.RETIRED_PERMISSION_CODES))
        )
        for permission in result.scalars().all():
            permission.is_active = False

    async def _retire_legacy_super_admin_role(self, db: AsyncSession):
        result = await db.execute(
            select(PermissionGroup).where(PermissionGroup.code == "super_admin")
        )
        group = result.scalar_one_or_none()
        if group is None:
            return

        group.name = "超级管理员（已停用角色）"
        group.description = "超级管理员身份只由用户 is_admin 字段表示，此角色不再参与授权"
        group.group_type = "system"
        group.level = self.SUPER_ADMIN_LEVEL
        group.is_system = True
        group.is_active = False

    # ========== 权限管理 ==========

    async def create_permission(
        self,
        db: AsyncSession,
        code: str,
        name: str,
        category: str,
        operator: User,
        description: Optional[str] = None,
    ) -> Permission:
        """创建新权限。"""
        if operator is None or not operator.is_admin:
            raise PermissionError("只有超级管理员可以创建权限定义")
        if code in self.RETIRED_PERMISSION_CODES:
            raise ValueError(f"权限已停用: {code}")

        result = await db.execute(select(Permission).where(Permission.code == code))
        if result.scalar_one_or_none():
            raise ValueError(f"权限代码 '{code}' 已存在")

        permission = Permission(
            code=code,
            name=name,
            category=category,
            description=description,
            is_active=True,
        )
        db.add(permission)
        await db.flush()

        await self._log_action(
            db,
            "create",
            "permission",
            permission.id,
            None,
            operator_id=operator.id,
        )
        await db.commit()
        await db.refresh(permission)
        return permission

    async def ensure_permission_system(
        self,
        db: AsyncSession,
        code: str,
        name: Optional[str] = None,
        category: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Permission:
        """系统/测试引导路径：确保权限码存在，不经过管理员授权与审计。"""
        if code in self.RETIRED_PERMISSION_CODES:
            raise ValueError(f"权限已停用: {code}")

        result = await db.execute(select(Permission).where(Permission.code == code))
        permission = result.scalar_one_or_none()
        if permission is None:
            permission = Permission(
                code=code,
                name=name or code,
                category=category or code.split(":", 1)[0],
                description=description,
                is_active=True,
            )
            db.add(permission)
            await db.flush()
            return permission

        if name is not None:
            permission.name = name
        if category is not None:
            permission.category = category
        if description is not None:
            permission.description = description
        permission.is_active = True
        return permission

    async def grant_permissions_system(
        self,
        db: AsyncSession,
        user: User,
        permission_codes: List[str],
        *,
        level: int = DEFAULT_ROLE_LEVEL,
        code: Optional[str] = None,
        name: Optional[str] = None,
    ) -> PermissionGroup:
        """系统/测试引导路径：给用户挂载角色，不经过管理员授权与审计。"""
        if level >= self.SUPER_ADMIN_LEVEL:
            raise ValueError("普通角色等级不能达到超级管理员等级")

        unique_codes = list(dict.fromkeys(permission_codes))
        permissions = [
            await self.ensure_permission_system(db, permission_code)
            for permission_code in unique_codes
        ]
        group_code = code or f"system_grant_{user.id}_{'_'.join(c.replace(':', '_') for c in unique_codes)}"
        result = await db.execute(select(PermissionGroup).where(PermissionGroup.code == group_code))
        if result.scalar_one_or_none():
            group_code = f"{group_code}_{utc_now().timestamp()}"

        group = PermissionGroup(
            code=group_code,
            name=name or "system grant",
            group_type="custom",
            level=level,
            is_active=True,
            is_system=False,
        )
        db.add(group)
        await db.flush()
        if permissions:
            await db.execute(
                permission_group_items.insert(),
                [
                    {"group_id": group.id, "permission_id": permission.id}
                    for permission in permissions
                ],
            )
        await db.execute(
            user_permission_groups.insert().values(
                user_id=user.id,
                group_id=group.id,
            )
        )
        await db.commit()
        return group

    async def get_permission_by_code(
        self,
        db: AsyncSession,
        code: str,
    ) -> Optional[Permission]:
        """通过代码获取权限。"""
        result = await db.execute(select(Permission).where(Permission.code == code))
        return result.scalar_one_or_none()

    async def get_permissions_by_category(
        self,
        db: AsyncSession,
        category: str,
    ) -> List[Permission]:
        """获取分类下的所有权限。"""
        result = await db.execute(
            select(Permission).where(
                and_(
                    Permission.category == category,
                    Permission.is_active == True,
                    Permission.code.notin_(self.RETIRED_PERMISSION_CODES),
                )
            )
        )
        return list(result.scalars().all())

    async def get_all_permissions(self, db: AsyncSession) -> List[Permission]:
        """获取所有权限。"""
        result = await db.execute(
            select(Permission)
            .where(
                Permission.is_active == True,
                Permission.code.notin_(self.RETIRED_PERMISSION_CODES),
            )
            .order_by(Permission.category.asc(), Permission.code.asc())
        )
        return list(result.scalars().all())

    # ========== 角色管理 ==========

    def can_manage_user(self, operator: User, target: User) -> bool:
        """判断 operator 是否能管理 target。"""
        if operator is None:
            return False
        if operator.is_admin:
            return True
        if target.is_admin:
            return False
        return target.effective_level < operator.effective_level

    def assert_can_manage_user(self, operator: User, target: User):
        if self.can_manage_user(operator, target):
            return
        raise PermissionError("只能管理等级低于自己的用户")

    def can_manage_role(self, operator: User, role: PermissionGroup) -> bool:
        if operator is None:
            return False
        if role.code in self.RESERVED_ROLE_CODES:
            return False
        if operator.is_admin:
            return True
        return (role.level or 0) < operator.effective_level

    def assert_can_manage_role(self, operator: User, role: PermissionGroup):
        if self.can_manage_role(operator, role):
            return
        raise PermissionError("只能管理等级低于自己的角色")

    def assert_can_use_role_level(self, operator: User, level: int):
        if level >= self.SUPER_ADMIN_LEVEL:
            raise ValueError("普通角色等级不能达到超级管理员等级")
        if operator is None:
            raise PermissionError("需要明确的操作人")
        if operator.is_admin:
            return
        if level >= operator.effective_level:
            raise PermissionError("角色等级必须低于当前用户等级")

    def assert_can_grant_permissions(
        self,
        operator: User,
        permission_codes: List[str],
    ):
        # 权限码决定能不能进入角色管理模块；等级决定能管理多高的角色。
        # 角色管理员可以配置普通权限，但权限定义管理能力保留给超级管理员。
        if operator is None:
            raise PermissionError("需要明确的操作人")
        retired_codes = self.RETIRED_PERMISSION_CODES.intersection(permission_codes)
        if retired_codes:
            raise ValueError(f"权限已停用: {', '.join(sorted(retired_codes))}")
        if operator.is_admin:
            return
        reserved_codes = self.RESERVED_PERMISSION_CODES.intersection(permission_codes)
        if reserved_codes:
            raise PermissionError("只有超级管理员可以分配权限定义管理权限")

    async def get_all_permission_groups(self, db: AsyncSession) -> List[PermissionGroup]:
        """获取所有角色。"""
        result = await db.execute(
            select(PermissionGroup)
            .options(
                selectinload(PermissionGroup.permissions),
                selectinload(PermissionGroup.users),
            )
            .where(PermissionGroup.code.not_in(self.RESERVED_ROLE_CODES))
            .order_by(PermissionGroup.level.desc(), PermissionGroup.id.asc())
            .execution_options(populate_existing=True)
        )
        groups = list(result.scalars().unique().all())
        for group in groups:
            group.user_count = len(group.users)
        return groups

    async def create_permission_group(
        self,
        db: AsyncSession,
        code: str,
        name: str,
        description: Optional[str] = None,
        parent_id: Optional[int] = None,
        permission_codes: Optional[List[str]] = None,
        level: int = DEFAULT_ROLE_LEVEL,
        *,
        operator: User,
    ) -> PermissionGroup:
        """创建角色。"""
        self.assert_can_use_role_level(operator, level)

        if code in self.RESERVED_ROLE_CODES:
            raise ValueError(f"角色代码 '{code}' 是系统保留代码")

        permission_codes = list(dict.fromkeys(permission_codes or []))
        self.assert_can_grant_permissions(operator, permission_codes)

        result = await db.execute(select(PermissionGroup).where(PermissionGroup.code == code))
        if result.scalar_one_or_none():
            raise ValueError(f"角色代码 '{code}' 已存在")

        if parent_id:
            parent = await self.get_permission_group_by_id(db, parent_id)
            if not parent:
                raise ValueError("父级角色不存在")
            self.assert_can_manage_role(operator, parent)

        group = PermissionGroup(
            code=code,
            name=name,
            description=description,
            parent_id=parent_id,
            group_type="role",
            level=level,
            is_active=True,
            is_system=False,
        )
        db.add(group)
        await db.flush()

        await self._replace_group_permissions(db, group.id, permission_codes)

        await self._log_action(
            db,
            "create",
            "group",
            group.id,
            None,
            operator_id=operator.id,
        )
        await db.commit()
        return await self.get_permission_group_by_id(db, group.id) or group

    async def get_permission_group_by_code(
        self,
        db: AsyncSession,
        code: str,
    ) -> Optional[PermissionGroup]:
        """通过代码获取角色。"""
        result = await db.execute(select(PermissionGroup).where(PermissionGroup.code == code))
        return result.scalar_one_or_none()

    async def get_permission_group_by_id(
        self,
        db: AsyncSession,
        group_id: int,
    ) -> Optional[PermissionGroup]:
        """通过 ID 获取角色。"""
        result = await db.execute(
            select(PermissionGroup)
            .options(
                selectinload(PermissionGroup.permissions),
                selectinload(PermissionGroup.users),
                selectinload(PermissionGroup.inherited_groups).selectinload(
                    PermissionGroup.permissions
                ),
                selectinload(PermissionGroup.parent).selectinload(PermissionGroup.permissions),
            )
            .where(PermissionGroup.id == group_id)
            .execution_options(populate_existing=True)
        )
        group = result.scalar_one_or_none()
        if group is not None:
            group.user_count = len(group.users)
        return group

    async def update_permission_group(
        self,
        db: AsyncSession,
        group_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        level: Optional[int] = None,
        permission_codes: Optional[List[str]] = None,
        *,
        operator: User,
    ) -> PermissionGroup:
        """更新角色。"""
        group = await self.get_permission_group_by_id(db, group_id)
        if not group:
            raise ValueError("角色不存在")
        if group.is_system:
            raise ValueError("系统内置角色不能修改")

        self.assert_can_manage_role(operator, group)
        if level is not None:
            self.assert_can_use_role_level(operator, level)
        if permission_codes is not None:
            permission_codes = list(dict.fromkeys(permission_codes))
            self.assert_can_grant_permissions(operator, permission_codes)

        if name is not None:
            group.name = name
        if description is not None:
            group.description = description
        if is_active is not None:
            group.is_active = is_active
        if level is not None:
            group.level = level
        if permission_codes is not None:
            await self._replace_group_permissions(db, group.id, permission_codes)

        group.updated_at = utc_now()
        await self._log_action(
            db,
            "update",
            "group",
            group.id,
            None,
            operator_id=operator.id,
        )
        await db.commit()
        return await self.get_permission_group_by_id(db, group.id) or group

    async def delete_permission_group(
        self,
        db: AsyncSession,
        group_id: int,
        *,
        operator: User,
    ):
        """删除角色。"""
        group = await self.get_permission_group_by_id(db, group_id)
        if not group:
            raise ValueError("角色不存在")
        if group.is_system:
            raise ValueError("系统内置角色不能删除")

        self.assert_can_manage_role(operator, group)

        await self._log_action(
            db,
            "delete",
            "group",
            group.id,
            None,
            operator_id=operator.id,
        )
        await db.delete(group)
        await db.commit()

    async def add_permissions_to_group(
        self,
        db: AsyncSession,
        group_id: int,
        permission_codes: List[str],
        *,
        operator: User,
    ) -> PermissionGroup:
        """向角色添加权限。"""
        group = await self.get_permission_group_by_id(db, group_id)
        if not group:
            raise ValueError("角色不存在")
        if group.is_system:
            raise ValueError("系统内置角色不能修改")

        self.assert_can_manage_role(operator, group)
        self.assert_can_grant_permissions(operator, permission_codes)

        for permission in await self._resolve_permissions(db, permission_codes):
            if permission not in group.permissions:
                group.permissions.append(permission)

        await self._log_action(
            db,
            "grant",
            "group",
            group.id,
            f"添加权限: {', '.join(permission_codes)}",
            operator_id=operator.id,
        )
        await db.commit()
        return await self.get_permission_group_by_id(db, group.id) or group

    async def remove_permissions_from_group(
        self,
        db: AsyncSession,
        group_id: int,
        permission_codes: List[str],
        *,
        operator: User,
    ) -> PermissionGroup:
        """从角色移除权限。"""
        group = await self.get_permission_group_by_id(db, group_id)
        if not group:
            raise ValueError("角色不存在")
        if group.is_system:
            raise ValueError("系统内置角色不能修改")

        self.assert_can_manage_role(operator, group)

        for permission in await self._resolve_permissions(db, permission_codes):
            if permission in group.permissions:
                group.permissions.remove(permission)

        await self._log_action(
            db,
            "revoke",
            "group",
            group.id,
            f"移除权限: {', '.join(permission_codes)}",
            operator_id=operator.id,
        )
        await db.commit()
        return await self.get_permission_group_by_id(db, group.id) or group

    # ========== 权限继承 ==========

    async def set_group_inheritance(
        self,
        db: AsyncSession,
        group_id: int,
        inherit_from_ids: List[int],
        *,
        operator: User,
    ) -> PermissionGroup:
        """设置角色继承关系。"""
        group = await self.get_permission_group_by_id(db, group_id)
        if not group:
            raise ValueError("角色不存在")
        if group.is_system:
            raise ValueError("系统内置角色不能修改")

        self.assert_can_manage_role(operator, group)

        parents: List[PermissionGroup] = []
        for parent_id in inherit_from_ids:
            if parent_id == group_id:
                raise ValueError("角色不能继承自己")
            parent = await self.get_permission_group_by_id(db, parent_id)
            if parent:
                self.assert_can_manage_role(operator, parent)
                self.assert_can_grant_permissions(
                    operator,
                    list(parent.get_all_permission_codes()),
                )
                parents.append(parent)

        group.inherited_groups = parents
        await self._log_action(
            db,
            "update",
            "group",
            group.id,
            f"设置继承: {inherit_from_ids}",
            operator_id=operator.id,
        )
        await db.commit()
        return await self.get_permission_group_by_id(db, group.id) or group

    # ========== 用户权限管理 ==========

    async def assign_groups_to_user(
        self,
        db: AsyncSession,
        user_id: int,
        group_ids: List[int],
        *,
        operator: User,
    ) -> User:
        """为用户分配角色。"""
        user = await self._get_user_with_permissions(db, user_id)
        if not user:
            raise ValueError("用户不存在")

        if operator is not None and user.id == operator.id:
            raise ValueError("不能调整当前登录用户的角色")

        self.assert_can_manage_user(operator, user)

        requested_group_ids = list(dict.fromkeys(group_ids))
        groups: List[PermissionGroup] = []
        for group_id in requested_group_ids:
            group = await self.get_permission_group_by_id(db, group_id)
            if group is None:
                raise ValueError(f"角色不存在: {group_id}")
            if group.code == "super_admin":
                raise ValueError("超级管理员身份不能通过角色分配")
            if not group.is_active:
                raise ValueError(f"角色已停用: {group.name}")

            self.assert_can_manage_role(operator, group)
            self.assert_can_grant_permissions(operator, list(group.get_all_permission_codes()))
            groups.append(group)

        await db.execute(
            user_permission_groups.delete().where(
                user_permission_groups.c.user_id == user_id
            )
        )
        if groups:
            await db.execute(
                user_permission_groups.insert(),
                [{"user_id": user_id, "group_id": group.id} for group in groups],
            )
        db.sync_session.expire(user, ["permission_groups"])

        await self._log_action(
            db,
            "grant",
            "user",
            user_id,
            f"分配角色: {[group.id for group in groups]}",
            operator_id=operator.id,
        )
        await db.commit()
        return await self._get_user_with_permissions(db, user_id) or user

    async def get_user_permissions(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> Set[str]:
        """获取用户的所有权限代码。"""
        user = await self._get_user_with_permissions(db, user_id)
        if not user:
            return set()
        return user.get_all_permissions()

    async def check_user_permission(
        self,
        db: AsyncSession,
        user_id: int,
        permission_code: str,
    ) -> bool:
        """检查用户是否有指定权限。"""
        user = await self._get_user_with_permissions(db, user_id)
        if not user:
            return False
        return user.has_permission(permission_code)

    async def _get_user_with_permissions(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> Optional[User]:
        result = await db.execute(
            select(User)
            .options(
                selectinload(User.permission_groups).selectinload(PermissionGroup.permissions),
                selectinload(User.permission_groups).selectinload(
                    PermissionGroup.inherited_groups
                ).selectinload(PermissionGroup.permissions),
                selectinload(User.permission_groups).selectinload(PermissionGroup.parent),
            )
            .where(User.id == user_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def _resolve_permissions(
        self,
        db: AsyncSession,
        permission_codes: List[str],
    ) -> List[Permission]:
        unique_codes = list(dict.fromkeys(permission_codes))
        if not unique_codes:
            return []

        result = await db.execute(
            select(Permission).where(
                Permission.code.in_(unique_codes),
                Permission.is_active == True,
                Permission.code.notin_(self.RETIRED_PERMISSION_CODES),
            )
        )
        permissions = list(result.scalars().all())
        found_codes = {permission.code for permission in permissions}
        missing = sorted(set(unique_codes) - found_codes)
        if missing:
            raise ValueError(f"权限不存在: {', '.join(missing)}")
        return permissions

    async def _replace_group_permissions(
        self,
        db: AsyncSession,
        group_id: int,
        permission_codes: List[str],
    ):
        permissions = await self._resolve_permissions(db, permission_codes)
        await db.execute(
            permission_group_items.delete().where(
                permission_group_items.c.group_id == group_id
            )
        )
        if permissions:
            await db.execute(
                permission_group_items.insert(),
                [
                    {"group_id": group_id, "permission_id": permission.id}
                    for permission in permissions
                ],
            )

    # ========== 审计日志 ==========

    async def _log_action(
        self,
        db: AsyncSession,
        action: str,
        target_type: str,
        target_id: int,
        details: Optional[str],
        operator_id: Optional[int] = None,
    ):
        """记录权限操作审计日志。"""
        if operator_id is None:
            raise PermissionError("需要明确的操作人")
        log = PermissionAuditLog(
            action=action,
            target_type=target_type,
            target_id=target_id,
            operator_id=operator_id,
            details=details,
        )
        db.add(log)

    async def get_audit_logs(
        self,
        db: AsyncSession,
        target_type: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
    ) -> List[PermissionAuditLog]:
        """获取审计日志。"""
        query = select(PermissionAuditLog)

        if target_type:
            query = query.where(PermissionAuditLog.target_type == target_type)
        if action:
            query = query.where(PermissionAuditLog.action == action)

        query = query.order_by(PermissionAuditLog.created_at.desc()).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())
