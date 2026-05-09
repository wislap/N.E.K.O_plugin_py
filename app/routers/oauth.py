"""OAuth 2.0 端点 — 供 N.E.K.O 桌面客户端登录 Market。

实现 Authorization Code + PKCE 流程：
1. 客户端打开浏览器访问 /oauth/authorize
2. 用户在 Market 网页登录并授权
3. Market 重定向到 neko://auth/callback?code=xxx&state=yyy
4. 客户端用 code + code_verifier 调用 /oauth/token 换取 access_token
"""

from __future__ import annotations

import hashlib
import base64
import secrets
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, get_current_user
from app.models.user import User

router = APIRouter(prefix="/oauth", tags=["oauth"])

# ─── 内存存储（生产环境应使用 Redis）─────────────────────────────

# 授权码存储: code -> {user_id, code_challenge, redirect_uri, expires_at, state}
_auth_codes: dict[str, dict] = {}

# 已注册的客户端
_KNOWN_CLIENTS = {
    "neko-desktop": {
        "name": "N.E.K.O Desktop",
        "allowed_redirect_prefixes": ["neko://", "http://127.0.0.1:", "http://localhost:"],
    },
}

# 授权码有效期（秒）
_CODE_TTL = 300  # 5 分钟

# 定期清理过期码的阈值
_MAX_STORED_CODES = 1000


# ─── 请求/响应模型 ─────────────────────────────────────────────────


class OAuthTokenRequest(BaseModel):
    grant_type: str = Field(default="authorization_code")
    code: str
    code_verifier: str
    client_id: str = "neko-desktop"
    redirect_uri: str = "neko://auth/callback"


class OAuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    scope: str = "read write"


class OAuthErrorResponse(BaseModel):
    error: str
    error_description: str


# ─── 端点 ──────────────────────────────────────────────────────────


@router.get("/authorize")
async def oauth_authorize(
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    state: str = Query(...),
    code_challenge: str = Query(...),
    code_challenge_method: str = Query(default="S256"),
    response_type: str = Query(default="code"),
    scope: str = Query(default="read write"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """OAuth 授权端点。

    用户已登录时直接发放授权码并重定向。
    未登录时返回 401（前端应引导用户先登录再重新访问）。

    注意：此端点需要用户已通过 Market 网页登录（Bearer token）。
    实际使用中，N.E.K.O 客户端打开浏览器访问 Market 登录页，
    登录后自动跳转到此授权端点。
    """
    # 验证客户端
    client = _KNOWN_CLIENTS.get(client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未知的客户端"
        )

    # 验证 redirect_uri
    if not _validate_redirect_uri(redirect_uri, client):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不允许的 redirect_uri"
        )

    # 验证 code_challenge_method
    if code_challenge_method != "S256":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 S256 code_challenge_method"
        )

    if response_type != "code":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 response_type=code"
        )

    # 生成授权码
    code = secrets.token_urlsafe(32)

    # 存储（带过期时间）
    _cleanup_expired_codes()
    _auth_codes[code] = {
        "user_id": current_user.id,
        "code_challenge": code_challenge,
        "redirect_uri": redirect_uri,
        "state": state,
        "client_id": client_id,
        "scope": scope,
        "expires_at": time.time() + _CODE_TTL,
    }

    # 重定向到客户端
    separator = "&" if "?" in redirect_uri else "?"
    redirect_url = f"{redirect_uri}{separator}code={code}&state={state}"

    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/token", response_model=OAuthTokenResponse)
async def oauth_token(
    payload: OAuthTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """OAuth Token 端点。

    用授权码 + PKCE code_verifier 换取 access_token。
    """
    if payload.grant_type != "authorization_code":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 grant_type=authorization_code"
        )

    # 查找并消费授权码
    code_data = _auth_codes.pop(payload.code, None)
    if not code_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效或已过期的授权码"
        )

    # 检查过期
    if time.time() > code_data["expires_at"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="授权码已过期"
        )

    # 验证 client_id
    if payload.client_id != code_data["client_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_id 不匹配"
        )

    # 验证 redirect_uri
    if payload.redirect_uri != code_data["redirect_uri"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="redirect_uri 不匹配"
        )

    # 验证 PKCE
    if not _verify_pkce(payload.code_verifier, code_data["code_challenge"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PKCE 验证失败"
        )

    # 发放 token
    user_id = code_data["user_id"]
    access_token = create_access_token(data={"sub": str(user_id)})
    refresh_token = create_refresh_token(data={"sub": str(user_id)})

    return OAuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600,
    )


@router.get("/clients")
async def list_oauth_clients():
    """列出已注册的 OAuth 客户端（公开信息）。"""
    return [
        {"client_id": cid, "name": info["name"]}
        for cid, info in _KNOWN_CLIENTS.items()
    ]


# ─── 内部工具 ──────────────────────────────────────────────────────


def _validate_redirect_uri(uri: str, client: dict) -> bool:
    """验证 redirect_uri 是否在客户端允许的前缀列表中。"""
    prefixes = client.get("allowed_redirect_prefixes", [])
    return any(uri.startswith(prefix) for prefix in prefixes)


def _verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """验证 PKCE S256。

    code_challenge = BASE64URL(SHA256(code_verifier))
    """
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    computed_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return secrets.compare_digest(computed_challenge, code_challenge)


def _cleanup_expired_codes() -> None:
    """清理过期的授权码。"""
    if len(_auth_codes) < _MAX_STORED_CODES:
        return
    now = time.time()
    expired = [k for k, v in _auth_codes.items() if now > v["expires_at"]]
    for k in expired:
        del _auth_codes[k]
