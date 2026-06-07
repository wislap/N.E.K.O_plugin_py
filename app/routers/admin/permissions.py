"""
权限管理路由
提供权限和角色的 CRUD 接口
"""
from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Type

from app.core.database import get_db
from app.core.security import PermissionChecker, get_current_user
from app.models.user import User
from app.services.permission_service import PermissionService
from app.schemas.permission import (
    PermissionCreate, PermissionResponse,
    PermissionGroupCreate, PermissionGroupUpdate, PermissionGroupResponse,
    PermissionAssignRequest, UserPermissionsResponse
)

router = APIRouter(prefix="/permissions", tags=["permissions"])
require_role_management = PermissionChecker("system:role")


def _map_service_error(error: Exception) -> HTTPException:
    if isinstance(error, PermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _parse_request_model(model: Type, data: dict):
    try:
        return model.model_validate(data)
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error.errors(include_url=False, include_context=False),
        )


def _user_permissions_payload(user: User) -> dict:
    permissions = user.get_all_permissions()
    roles = user.role_summaries
    return {
        "user_id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
        "is_super_admin": user.is_admin,
        "level": user.effective_level,
        "permissions": list(permissions),
        "groups": [role.code for role in roles],
        "roles": roles,
    }


# ========== 权限管理 ==========

@router.get("/list", response_model=List[PermissionResponse])
async def list_permissions(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role_management)
):
    """获取权限列表"""
    service = PermissionService()
    
    if category:
        return await service.get_permissions_by_category(db, category)
    return await service.get_all_permissions(db)


@router.post("/create", response_model=PermissionResponse)
async def create_permission(
    data: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新权限（需要权限管理权限）"""
    service = PermissionService()
    try:
        return await service.create_permission(
            db,
            code=data.code,
            name=data.name,
            category=data.category,
            description=data.description,
            operator=current_user,
        )
    except (PermissionError, ValueError) as e:
        raise _map_service_error(e)


# ========== 角色管理 ==========

@router.get("/groups", response_model=List[PermissionGroupResponse])
async def list_permission_groups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role_management)
):
    """获取角色列表"""
    service = PermissionService()
    return await service.get_all_permission_groups(db)


@router.post("/groups/create", response_model=PermissionGroupResponse)
async def create_permission_group(
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role_management)
):
    """创建角色"""
    service = PermissionService()
    payload = _parse_request_model(PermissionGroupCreate, data)
    try:
        return await service.create_permission_group(
            db,
            code=payload.code,
            name=payload.name,
            description=payload.description,
            parent_id=payload.parent_id,
            permission_codes=payload.permission_codes,
            level=payload.level,
            operator=current_user,
        )
    except (PermissionError, ValueError) as e:
        raise _map_service_error(e)


@router.put("/groups/{group_id}", response_model=PermissionGroupResponse)
async def update_permission_group(
    group_id: int,
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role_management)
):
    """更新角色"""
    service = PermissionService()
    payload = _parse_request_model(PermissionGroupUpdate, data)
    try:
        return await service.update_permission_group(
            db,
            group_id=group_id,
            name=payload.name,
            description=payload.description,
            is_active=payload.is_active,
            level=payload.level,
            permission_codes=payload.permission_codes,
            operator=current_user,
        )
    except (PermissionError, ValueError) as e:
        raise _map_service_error(e)


@router.delete("/groups/{group_id}")
async def delete_permission_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role_management)
):
    """删除角色"""
    service = PermissionService()
    try:
        await service.delete_permission_group(db, group_id, operator=current_user)
        return {"message": "角色已删除"}
    except (PermissionError, ValueError) as e:
        raise _map_service_error(e)


@router.post("/groups/{group_id}/permissions")
async def add_permissions_to_group(
    group_id: int,
    permission_codes: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role_management)
):
    """向角色添加权限"""
    service = PermissionService()
    try:
        group = await service.add_permissions_to_group(
            db,
            group_id,
            permission_codes,
            operator=current_user,
        )
        return {"message": "权限已添加", "role": group.code, "group": group.code}
    except (PermissionError, ValueError) as e:
        raise _map_service_error(e)


@router.delete("/groups/{group_id}/permissions")
async def remove_permissions_from_group(
    group_id: int,
    permission_codes: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role_management)
):
    """从角色移除权限"""
    service = PermissionService()
    try:
        group = await service.remove_permissions_from_group(
            db,
            group_id,
            permission_codes,
            operator=current_user,
        )
        return {"message": "权限已移除", "role": group.code, "group": group.code}
    except (PermissionError, ValueError) as e:
        raise _map_service_error(e)


@router.post("/groups/{group_id}/inherit")
async def set_group_inheritance(
    group_id: int,
    inherit_from_ids: List[int],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role_management)
):
    """设置角色继承关系"""
    service = PermissionService()
    try:
        group = await service.set_group_inheritance(
            db,
            group_id,
            inherit_from_ids,
            operator=current_user,
        )
        return {
            "message": "继承关系已设置",
            "role": group.code,
            "group": group.code,
            "inherited_groups": [g.code for g in group.inherited_groups]
        }
    except (PermissionError, ValueError) as e:
        raise _map_service_error(e)


# ========== 用户权限管理 ==========

@router.post("/users/{user_id}/assign")
async def assign_groups_to_user(
    user_id: int,
    data: PermissionAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role_management)
):
    """为用户分配角色"""
    service = PermissionService()
    try:
        user = await service.assign_groups_to_user(
            db,
            user_id,
            data.group_ids,
            operator=current_user,
        )
        return {
            "message": "角色已分配",
            "user": user.username,
            "groups": [g.code for g in user.permission_groups],
            "roles": [g.code for g in user.permission_groups],
        }
    except (PermissionError, ValueError) as e:
        raise _map_service_error(e)


@router.get("/users/me", response_model=UserPermissionsResponse)
async def get_my_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的权限"""
    return _user_permissions_payload(current_user)


@router.get("/users/{user_id}", response_model=UserPermissionsResponse)
async def get_user_permissions(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role_management)
):
    """获取指定用户的权限（需要管理员权限）"""
    service = PermissionService()
    user = await service._get_user_with_permissions(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    try:
        service.assert_can_manage_user(current_user, user)
    except PermissionError as e:
        raise _map_service_error(e)

    return _user_permissions_payload(user)


@router.get("/check/{permission_code}")
async def check_permission(
    permission_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """检查当前用户是否有指定权限"""
    has_permission = current_user.has_permission(permission_code)
    return {
        "permission": permission_code,
        "has_permission": has_permission
    }
