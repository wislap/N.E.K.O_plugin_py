from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import PermissionChecker
from app.models.user import User
from app.schemas.common import MessageResponse
from app.services.zone_service import ZoneService

router = APIRouter(prefix="/zones", tags=["admin-zones"])
require_zone_management = PermissionChecker("plugin:zone")


class ZoneCreateRequest(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0


class ZoneUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None


def serialize_zone(zone):
    return {
        "id": zone.id,
        "name": zone.name,
        "slug": zone.slug,
        "description": zone.description,
        "icon": zone.icon,
        "color": zone.color,
        "sort_order": zone.sort_order,
        "created_at": zone.created_at,
        "updated_at": zone.updated_at,
    }


@router.get("", response_model=List[dict])
async def list_zones(
    current_user: User = Depends(require_zone_management),
    db: AsyncSession = Depends(get_db),
):
    zones = await ZoneService.get_zones(db)
    return [serialize_zone(zone) for zone in zones]


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_zone(
    data: ZoneCreateRequest,
    current_user: User = Depends(require_zone_management),
    db: AsyncSession = Depends(get_db),
):
    try:
        zone = await ZoneService.create_zone(
            db,
            data.name,
            data.slug,
            data.description,
            data.icon,
            data.color,
            data.sort_order,
        )
        return {**serialize_zone(zone), "message": "区域创建成功"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{zone_id}", response_model=dict)
async def update_zone(
    zone_id: int,
    data: ZoneUpdateRequest,
    current_user: User = Depends(require_zone_management),
    db: AsyncSession = Depends(get_db),
):
    zone = await ZoneService.get_zone_by_id(db, zone_id)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="区域不存在")
    updated_zone = await ZoneService.update_zone(
        db,
        zone,
        data.name,
        data.description,
        data.icon,
        data.color,
        data.sort_order,
    )
    return {**serialize_zone(updated_zone), "message": "区域更新成功"}


@router.delete("/{zone_id}", response_model=MessageResponse)
async def delete_zone(
    zone_id: int,
    current_user: User = Depends(require_zone_management),
    db: AsyncSession = Depends(get_db),
):
    zone = await ZoneService.get_zone_by_id(db, zone_id)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="区域不存在")
    await ZoneService.delete_zone(db, zone)
    return MessageResponse(message="区域已删除")
