from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.version import Version, VersionCreate
from app.schemas.common import MessageResponse
from app.services.version_service import VersionService
from app.services.plugin_service import PluginService

router = APIRouter()


@router.get("/plugins/{plugin_id}/versions", response_model=List[Version])
async def list_plugin_versions(
    plugin_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取插件的所有版本
    """
    # 检查插件是否存在
    plugin = await PluginService.get_plugin_by_id(db, plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="插件不存在"
        )
    
    versions = await VersionService.get_plugin_versions(db, plugin_id)
    return versions


@router.get("/plugins/{plugin_id}/versions/latest", response_model=Version)
async def get_latest_version(
    plugin_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取插件的最新版本
    """
    plugin = await PluginService.get_plugin_by_id(db, plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="插件不存在"
        )
    
    version = await VersionService.get_latest_version(db, plugin_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该插件暂无版本"
        )
    
    return version


@router.post("/plugins/{plugin_id}/versions", response_model=Version, status_code=status.HTTP_201_CREATED)
async def create_version(
    plugin_id: int,
    version_data: VersionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    为插件创建新版本（需要插件所有者权限）
    """
    # 检查插件是否存在
    plugin = await PluginService.get_plugin_by_id(db, plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="插件不存在"
        )
    
    if plugin.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限为此插件创建版本"
        )
    
    # 检查版本是否已存在
    exists = await VersionService.version_exists(db, plugin_id, version_data.version)
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"版本 {version_data.version} 已存在"
        )
    
    version = await VersionService.create_version(
        db,
        plugin_id=plugin_id,
        version=version_data.version,
        changelog=version_data.changelog,
        download_url=version_data.download_url,
        min_app_version=version_data.min_app_version,
        max_app_version=version_data.max_app_version,
        plugin=plugin
    )

    return version


@router.delete("/plugins/{plugin_id}/versions/{version_id}", response_model=MessageResponse)
async def delete_version(
    plugin_id: int,
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除插件版本（需要插件所有者或管理员权限）
    """
    # 检查插件是否存在
    plugin = await PluginService.get_plugin_by_id(db, plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="插件不存在"
        )
    
    # 检查版本是否存在
    version = await VersionService.get_version_by_id(db, version_id)
    if not version or version.plugin_id != plugin_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="版本不存在"
        )
    
    if plugin.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限删除此插件版本"
        )
    
    await VersionService.delete_version(db, version)
    return MessageResponse(message="版本已删除")
