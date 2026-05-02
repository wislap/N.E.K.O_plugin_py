from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import PermissionChecker
from app.models.plugin_signature import ServerKeyPair
from app.models.user import User
from app.schemas.common import MessageResponse
from app.services.signature_service import SignatureService

router = APIRouter(prefix="/signatures", tags=["admin-signatures"])
signature_service = SignatureService()
require_signature_management = PermissionChecker("plugin:signature")


class KeyCreateRequest(BaseModel):
    name: str
    set_as_default: bool = False


class SignatureRevokeRequest(BaseModel):
    reason: str


@router.post("/keys", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_keypair(
    data: KeyCreateRequest,
    current_user: User = Depends(require_signature_management),
    db: AsyncSession = Depends(get_db),
):
    try:
        keypair = await signature_service.create_keypair(db, data.name, data.set_as_default)
        return {
            "id": keypair.id,
            "name": keypair.name,
            "public_key": keypair.public_key,
            "is_default": keypair.is_default,
            "is_active": keypair.is_active,
            "created_at": keypair.created_at,
            "activated_at": keypair.activated_at,
            "deactivated_at": keypair.deactivated_at,
            "message": "密钥对创建成功",
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/keys", response_model=list[dict])
async def list_keypairs(
    current_user: User = Depends(require_signature_management),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ServerKeyPair))
    keypairs = result.scalars().all()
    return [
        {
            "id": kp.id,
            "name": kp.name,
            "public_key": kp.public_key,
            "is_default": kp.is_default,
            "is_active": kp.is_active,
            "created_at": kp.created_at,
            "activated_at": kp.activated_at,
            "deactivated_at": kp.deactivated_at,
        }
        for kp in keypairs
    ]


@router.post("/keys/{keypair_id}/deactivate", response_model=MessageResponse)
async def deactivate_keypair(
    keypair_id: int,
    current_user: User = Depends(require_signature_management),
    db: AsyncSession = Depends(get_db),
):
    try:
        await signature_service.deactivate_keypair(db, keypair_id)
        return MessageResponse(message="密钥对已停用")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/plugins/{plugin_id}/sign", response_model=dict)
async def sign_plugin(
    plugin_id: int,
    keypair_id: Optional[int] = None,
    current_user: User = Depends(require_signature_management),
    db: AsyncSession = Depends(get_db),
):
    try:
        signature = await signature_service.sign_plugin_from_github(db, plugin_id, keypair_id)
        return {
            "signature_id": signature.id,
            "plugin_id": signature.plugin_id,
            "plugin_name": signature.plugin_name,
            "version": signature.version,
            "signature": signature.signature,
            "files_hash": signature.files_hash,
            "files_count": len(signature.files_md5),
            "payload": signature.payload,
            "keypair_id": signature.keypair_id,
            "created_at": signature.created_at,
            "message": "插件签名成功",
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{signature_id}/revoke", response_model=MessageResponse)
async def revoke_signature(
    signature_id: int,
    data: SignatureRevokeRequest,
    current_user: User = Depends(require_signature_management),
    db: AsyncSession = Depends(get_db),
):
    try:
        await signature_service.revoke_signature(db, signature_id, data.reason, current_user.id)
        return MessageResponse(message="签名已撤销")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
