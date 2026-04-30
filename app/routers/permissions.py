"""
权限管理路由
提供权限和权限组的 CRUD 接口
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.models.user import User
from app.services.permission_service import PermissionService
from app.schemas.permission import (
    PermissionCreate, PermissionResponse,
    PermissionGroupCreate, PermissionGroupUpdate, PermissionGroupResponse,
    PermissionAssignRequest, UserPermissionsResponse
)

router = APIRouter(prefix="/permissions", tags=["permissions"])


# ========== 权限管理 ==========

@router.get("/list", response_model=List[PermissionResponse])
async def list_permissions(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_admin_user)
):
    """创建新权限（需要权限管理权限）"""
    service = PermissionService()
    try:
        return await service.create_permission(
            db,
            code=data.code,
            name=data.name,
            category=data.category,
            description=data.description
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== 权限组管理 ==========

@router.get("/groups", response_model=List[PermissionGroupResponse])
async def list_permission_groups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取权限组列表"""
    service = PermissionService()
    # TODO: 添加服务方法获取所有权限组
    from sqlalchemy import select
    from app.models.permission import PermissionGroup
    result = await db.execute(select(PermissionGroup))
    return list(result.scalars().all())


@router.post("/groups/create", response_model=PermissionGroupResponse)
async def create_permission_group(
    data: PermissionGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """创建权限组"""
    service = PermissionService()
    try:
        return await service.create_permission_group(
            db,
            code=data.code,
            name=data.name,
            description=data.description,
            parent_id=data.parent_id,
            permission_codes=data.permission_codes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/groups/{group_id}", response_model=PermissionGroupResponse)
async def update_permission_group(
    group_id: int,
    data: PermissionGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """更新权限组"""
    service = PermissionService()
    try:
        return await service.update_permission_group(
            db,
            group_id=group_id,
            name=data.name,
            description=data.description,
            is_active=data.is_active
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/groups/{group_id}")
async def delete_permission_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """删除权限组"""
    service = PermissionService()
    try:
        await service.delete_permission_group(db, group_id)
        return {"message": "权限组已删除"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/groups/{group_id}/permissions")
async def add_permissions_to_group(
    group_id: int,
    permission_codes: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """向权限组添加权限"""
    service = PermissionService()
    try:
        group = await service.add_permissions_to_group(db, group_id, permission_codes)
        return {"message": "权限已添加", "group": group.code}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/groups/{group_id}/permissions")
async def remove_permissions_from_group(
    group_id: int,
    permission_codes: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """从权限组移除权限"""
    service = PermissionService()
    try:
        group = await service.remove_permissions_from_group(db, group_id, permission_codes)
        return {"message": "权限已移除", "group": group.code}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/groups/{group_id}/inherit")
async def set_group_inheritance(
    group_id: int,
    inherit_from_ids: List[int],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """设置权限组继承关系"""
    service = PermissionService()
    try:
        group = await service.set_group_inheritance(db, group_id, inherit_from_ids)
        return {
            "message": "继承关系已设置",
            "group": group.code,
            "inherited_groups": [g.code for g in group.inherited_groups]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== 用户权限管理 ==========

@router.post("/users/{user_id}/assign")
async def assign_groups_to_user(
    user_id: int,
    data: PermissionAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """为用户分配权限组"""
    service = PermissionService()
    try:
        user = await service.assign_groups_to_user(db, user_id, data.group_ids)
        return {
            "message": "权限组已分配",
            "user": user.username,
            "groups": [g.code for g in user.permission_groups]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users/me", response_model=UserPermissionsResponse)
async def get_my_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的权限"""
    permissions = current_user.get_all_permissions()
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "is_admin": current_user.is_admin,
        "permissions": list(permissions),
        "groups": [g.code for g in current_user.permission_groups if g.is_active]
    }


@router.get("/users/{user_id}", response_model=UserPermissionsResponse)
async def get_user_permissions(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """获取指定用户的权限（需要管理员权限）"""
    from sqlalchemy import select
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    permissions = user.get_all_permissions()
    return {
        "user_id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
        "permissions": list(permissions),
        "groups": [g.code for g in user.permission_groups if g.is_active]
    }


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
