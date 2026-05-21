from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.time import utc_now
from app.models.plugin import Plugin, PluginStatus
from app.models.user import User
from app.models.user_plugin_install import UserPluginInstall

router = APIRouter(prefix="/me/installs", tags=["me-installs"])


class UserPluginInstallCreate(BaseModel):
    plugin_id: int
    version: str | None = Field(default=None, max_length=50)
    channel: str | None = Field(default=None, max_length=16)
    package_sha256: str | None = Field(default=None, max_length=64)
    payload_hash: str | None = Field(default=None, max_length=128)
    installed_plugin_id: str | None = Field(default=None, max_length=100)
    client_id: str = Field(default="neko-desktop", max_length=50)


class UserPluginInstallResponse(BaseModel):
    id: int
    plugin_id: int
    version: str | None
    channel: str | None
    package_sha256: str | None
    payload_hash: str | None
    installed_plugin_id: str | None
    client_id: str
    installed_at: datetime
    last_seen_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[UserPluginInstallResponse])
async def list_my_installs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List plugins this Market account has installed through N.E.K.O."""
    result = await db.execute(
        select(UserPluginInstall)
        .where(UserPluginInstall.user_id == current_user.id)
        .order_by(UserPluginInstall.last_seen_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=UserPluginInstallResponse, status_code=status.HTTP_201_CREATED)
async def record_my_install(
    payload: UserPluginInstallCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upsert a verified user install record reported by the desktop client."""
    plugin = await db.get(Plugin, payload.plugin_id)
    if not plugin or plugin.status != PluginStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="插件不存在或尚未发布",
        )

    result = await db.execute(
        select(UserPluginInstall).where(
            UserPluginInstall.user_id == current_user.id,
            UserPluginInstall.plugin_id == payload.plugin_id,
        )
    )
    record = result.scalar_one_or_none()
    now = utc_now()
    if record is None:
        record = UserPluginInstall(
            user_id=current_user.id,
            plugin_id=payload.plugin_id,
            installed_at=now,
        )
        db.add(record)

    record.version = payload.version
    record.channel = payload.channel
    record.package_sha256 = payload.package_sha256
    record.payload_hash = payload.payload_hash
    record.installed_plugin_id = payload.installed_plugin_id
    record.client_id = payload.client_id
    record.last_seen_at = now
    record.updated_at = now

    await db.commit()
    await db.refresh(record)
    return record
