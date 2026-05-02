from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.core.security import PermissionChecker, get_current_user
from app.services.signature_service import SignatureService
from app.models.user import User
from app.schemas.common import MessageResponse

router = APIRouter()
signature_service = SignatureService()
require_signature_management = PermissionChecker("plugin:signature")


# ========== 公钥管理（管理员） ==========

@router.post("/admin/keys", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_keypair(
    name: str,
    set_as_default: bool = False,
    current_user: User = Depends(require_signature_management),
    db: AsyncSession = Depends(get_db)
):
    """
    创建新的签名密钥对（管理员）
    """
    try:
        keypair = await signature_service.create_keypair(db, name, set_as_default)
        return {
            "id": keypair.id,
            "name": keypair.name,
            "public_key": keypair.public_key,
            "is_default": keypair.is_default,
            "is_active": keypair.is_active,
            "created_at": keypair.created_at,
            "message": "密钥对创建成功"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/admin/keys", response_model=List[dict])
async def list_keypairs(
    current_user: User = Depends(require_signature_management),
    db: AsyncSession = Depends(get_db)
):
    """
    获取所有密钥对列表（管理员）
    """
    from app.models.plugin_signature import ServerKeyPair
    from sqlalchemy import select
    
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
            "deactivated_at": kp.deactivated_at
        }
        for kp in keypairs
    ]


@router.post("/admin/keys/{keypair_id}/deactivate", response_model=MessageResponse)
async def deactivate_keypair(
    keypair_id: int,
    current_user: User = Depends(require_signature_management),
    db: AsyncSession = Depends(get_db)
):
    """
    停用密钥对（管理员）
    """
    try:
        await signature_service.deactivate_keypair(db, keypair_id)
        return MessageResponse(message="密钥对已停用")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ========== 公钥查询（公开） ==========

@router.get("/public-keys", response_model=List[dict])
async def get_public_keys(
    db: AsyncSession = Depends(get_db)
):
    """
    获取所有公开的公钥（无需认证）
    """
    keys = await signature_service.get_all_public_keys(db)
    return keys


@router.get("/public-keys/default", response_model=dict)
async def get_default_public_key(
    db: AsyncSession = Depends(get_db)
):
    """
    获取默认公钥（无需认证）
    """
    keypair = await signature_service.get_default_keypair(db)
    if not keypair:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到默认公钥"
        )
    
    return {
        "id": keypair.id,
        "name": keypair.name,
        "public_key": keypair.public_key,
        "is_default": keypair.is_default,
        "created_at": keypair.created_at
    }


# ========== 插件签名（管理员） ==========

@router.post("/plugins/{plugin_id}/sign", response_model=dict)
async def sign_plugin(
    plugin_id: int,
    keypair_id: Optional[int] = None,
    current_user: User = Depends(require_signature_management),
    db: AsyncSession = Depends(get_db)
):
    """
    为插件生成代码签名（管理员）
    
    插件审核通过后，从 GitHub 拉取 Python 文件并生成 EC 签名
    """
    try:
        signature = await signature_service.sign_plugin_from_github(
            db, plugin_id, keypair_id
        )
        
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
            "message": "插件签名成功"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/plugins/{plugin_id}/signatures", response_model=List[dict])
async def get_plugin_signatures(
    plugin_id: int,
    valid_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取插件的所有签名记录
    """
    signatures = await signature_service.get_plugin_signatures(
        db, plugin_id, valid_only
    )
    
    return [
        {
            "id": sig.id,
            "version": sig.version,
            "signature": sig.signature[:50] + "..." if len(sig.signature) > 50 else sig.signature,
            "files_hash": sig.files_hash,
            "files_count": len(sig.files_md5),
            "keypair_id": sig.keypair_id,
            "is_valid": sig.is_valid,
            "created_at": sig.created_at,
            "verified_at": sig.verified_at
        }
        for sig in signatures
    ]


@router.get("/plugins/{plugin_id}/signatures/{version}", response_model=dict)
async def get_signature_by_version(
    plugin_id: int,
    version: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定版本的签名详情
    """
    signature = await signature_service.get_signature_by_version(
        db, plugin_id, version
    )
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到该版本的签名"
        )
    
    # 获取密钥对信息
    keypair = await signature_service.get_keypair_by_id(db, signature.keypair_id)
    
    return {
        "id": signature.id,
        "plugin_id": signature.plugin_id,
        "plugin_name": signature.plugin_name,
        "version": signature.version,
        "author": signature.author,
        "repo_url": signature.repo_url,
        "signature": signature.signature,
        "files_hash": signature.files_hash,
        "files_md5": signature.files_md5,
        "payload": signature.payload,
        "keypair_id": signature.keypair_id,
        "keypair_name": keypair.name if keypair else None,
        "public_key": keypair.public_key if keypair else None,
        "is_valid": signature.is_valid,
        "created_at": signature.created_at
    }


@router.post("/admin/signatures/{signature_id}/revoke", response_model=MessageResponse)
async def revoke_signature(
    signature_id: int,
    reason: str,
    current_user: User = Depends(require_signature_management),
    db: AsyncSession = Depends(get_db)
):
    """
    撤销签名（管理员）
    """
    try:
        await signature_service.revoke_signature(
            db, signature_id, reason, current_user.id
        )
        return MessageResponse(message="签名已撤销")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ========== 签名校验（公开 API） ==========

@router.post("/verify", response_model=dict)
async def verify_signature(
    plugin_name: str,
    version: str,
    author: str,
    repo_url: str,
    files: List[dict],
    signature: str,
    db: AsyncSession = Depends(get_db)
):
    """
    验证插件签名（公开 API，无需认证）
    
    请求体示例:
    {
        "plugin_name": "my-plugin",
        "version": "1.0.0",
        "author": "author_name",
        "repo_url": "https://github.com/xxx/neko_plugin_xxx",
        "files": [
            {"path": "main.py", "content": "..."},
            {"path": "utils.py", "content": "..."}
        ],
        "signature": "base64_encoded_signature"
    }
    """
    try:
        result = await signature_service.verify_signature(
            db,
            plugin_name=plugin_name,
            version=version,
            author=author,
            repo_url=repo_url,
            files=files,
            signature=signature
        )
        
        return {
            "valid": result["valid"],
            "message": result["message"],
            "files_hash": result["files_hash"],
            "expected_hash": result["expected_hash"],
            "hash_match": result["hash_match"],
            "signature_info": result["signature_info"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"验证失败: {str(e)}"
        )


@router.post("/verify-simple", response_model=dict)
async def verify_signature_simple(
    plugin_name: str,
    version: str,
    author: str,
    repo_url: str,
    files_hash: str,
    signature: str,
    db: AsyncSession = Depends(get_db)
):
    """
    简化版签名验证（仅验证文件哈希，不上传文件内容）
    
    适用于客户端已经计算好文件哈希的场景
    """
    try:
        # 查找签名记录
        from app.models.plugin_signature import PluginSignature
        from sqlalchemy import select, and_
        
        result = await db.execute(
            select(PluginSignature).where(
                and_(
                    PluginSignature.plugin_name == plugin_name,
                    PluginSignature.version == version,
                    PluginSignature.author == author,
                    PluginSignature.repo_url == repo_url,
                    PluginSignature.is_valid == True
                )
            )
        )
        sig_record = result.scalar_one_or_none()
        
        if not sig_record:
            return {
                "valid": False,
                "message": "未找到匹配的签名记录",
                "hash_match": False
            }
        
        # 比对哈希
        hash_match = files_hash == sig_record.files_hash
        
        return {
            "valid": hash_match,
            "message": "文件哈希匹配" if hash_match else "文件哈希不匹配",
            "provided_hash": files_hash,
            "expected_hash": sig_record.files_hash,
            "hash_match": hash_match,
            "signature": sig_record.signature[:50] + "..." if len(sig_record.signature) > 50 else sig_record.signature
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"验证失败: {str(e)}"
        )
