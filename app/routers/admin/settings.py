"""
管理后台设置路由
提供 SMTP 等系统设置管理接口
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.system_setting_service import system_setting_service
from app.services.email_service import email_service

router = APIRouter(tags=["admin-settings"])


class SMTPSettingsRequest(BaseModel):
    """SMTP 设置请求"""
    host: str = Field(..., description="SMTP 服务器地址")
    port: int = Field(default=587, description="SMTP 端口")
    user: str = Field(..., description="SMTP 用户名")
    password: Optional[str] = Field(None, description="SMTP 密码（留空表示不修改）")
    tls: bool = Field(default=True, description="是否使用 TLS")
    from_email: EmailStr = Field(..., description="发件人邮箱")
    enabled: bool = Field(default=True, description="是否启用")


class SMTPSettingsResponse(BaseModel):
    """SMTP 设置响应"""
    host: str
    port: int
    user: str
    tls: bool
    from_email: str
    enabled: bool


class TestEmailRequest(BaseModel):
    """测试邮件请求"""
    to_email: EmailStr = Field(..., description="测试收件人邮箱")


class SystemSettingUpdateRequest(BaseModel):
    """通用系统设置更新请求"""
    value: Any = Field(..., description="设置值")


# ========== SMTP 设置管理 ==========

@router.get("/settings/smtp", response_model=SMTPSettingsResponse)
async def get_smtp_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取 SMTP 设置（需要 system:smtp 权限）
    """
    if not current_user.has_permission("system:smtp"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要 system:smtp 权限"
        )
    
    settings = await system_setting_service.get_smtp_settings(db)
    
    return SMTPSettingsResponse(
        host=settings.get('smtp_host', ''),
        port=settings.get('smtp_port', 587),
        user=settings.get('smtp_user', ''),
        tls=settings.get('smtp_tls', True),
        from_email=settings.get('smtp_from', ''),
        enabled=settings.get('smtp_enabled', False)
    )


@router.put("/settings/smtp")
async def update_smtp_settings(
    data: SMTPSettingsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新 SMTP 设置（需要 system:smtp 权限）
    """
    if not current_user.has_permission("system:smtp"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要 system:smtp 权限"
        )
    
    # 更新设置
    updates = await system_setting_service.update_smtp_settings(
        db,
        host=data.host,
        port=data.port,
        user=data.user,
        password=data.password,  # 如果为 None 则不修改
        tls=data.tls,
        from_email=data.from_email,
        enabled=data.enabled,
        updated_by=current_user.id
    )
    
    return {
        "message": "SMTP 设置已更新",
        "updated_fields": list(updates.keys())
    }


@router.post("/settings/smtp/test")
async def test_smtp_connection(
    data: TestEmailRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    测试 SMTP 连接和发送测试邮件（需要 system:smtp 权限）
    """
    if not current_user.has_permission("system:smtp"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要 system:smtp 权限"
        )
    
    # 首先测试 SMTP 连接
    connection_test = await system_setting_service.test_smtp_connection(db)
    
    if not connection_test["success"]:
        return {
            "success": False,
            "message": connection_test["message"],
            "stage": "connection"
        }
    
    # 发送测试邮件
    email_service.set_db_session(db)
    
    html_content = f"""
    <html>
    <body>
        <h1>SMTP 测试邮件</h1>
        <p>这是一封测试邮件，用于验证 SMTP 配置是否正确。</p>
        <p>发送时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>发送者: {current_user.username}</p>
    </body>
    </html>
    """
    
    success = await email_service._send_email(
        to_email=data.to_email,
        subject="N.E.K.O 插件市场 - SMTP 测试",
        html_content=html_content,
        text_content="这是一封测试邮件，用于验证 SMTP 配置是否正确。"
    )
    
    if success:
        return {
            "success": True,
            "message": "SMTP 连接成功，测试邮件已发送",
            "stage": "email_sent",
            "to": data.to_email
        }
    else:
        return {
            "success": False,
            "message": "SMTP 连接成功，但邮件发送失败",
            "stage": "email_send"
        }


@router.get("/settings/smtp/status")
async def get_smtp_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取 SMTP 服务状态（需要 system:smtp 权限）
    """
    if not current_user.has_permission("system:smtp"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要 system:smtp 权限"
        )
    
    settings = await system_setting_service.get_smtp_settings(db)
    
    # 检查配置完整性
    required_fields = ['smtp_host', 'smtp_user', 'smtp_password', 'smtp_from']
    missing_fields = [f for f in required_fields if not settings.get(f)]
    
    return {
        "enabled": settings.get('smtp_enabled', False),
        "configured": len(missing_fields) == 0,
        "missing_fields": missing_fields if missing_fields else None,
        "host": settings.get('smtp_host'),
        "port": settings.get('smtp_port'),
        "user": settings.get('smtp_user'),
        "from_email": settings.get('smtp_from'),
        "tls": settings.get('smtp_tls', True)
    }


# ========== 通用设置管理 ==========

@router.get("/settings")
async def get_all_settings(
    group: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取所有系统设置（需要 system:settings 权限）
    """
    if not current_user.has_permission("system:settings"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要 system:settings 权限"
        )
    
    if group:
        settings_list = await system_setting_service.get_settings_by_group(db, group)
        return {
            "group": group,
            "settings": [
                {
                    "key": s.key,
                    "value": s.value if not s.is_encrypted else "********",
                    "description": s.description,
                    "is_encrypted": s.is_encrypted,
                    "updated_at": s.updated_at
                }
                for s in settings_list
            ]
        }
    else:
        settings_list = await system_setting_service.get_all_setting_records(db)
        return {
            "settings": [
                {
                    "key": s.key,
                    "value": s.value if not s.is_encrypted else "********",
                    "description": s.description,
                    "group": s.group,
                    "is_encrypted": s.is_encrypted,
                    "updated_at": s.updated_at
                }
                for s in settings_list
            ]
        }


@router.put("/settings/{key}")
async def update_setting(
    key: str,
    data: SystemSettingUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新单个系统设置（需要 system:settings 权限）
    """
    if not current_user.has_permission("system:settings"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要 system:settings 权限"
        )

    setting = await system_setting_service.get_setting(db, key)
    if not setting and key not in system_setting_service.DEFAULT_SETTINGS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="设置项不存在"
        )

    default_config = system_setting_service.DEFAULT_SETTINGS.get(key, {})
    is_encrypted = setting.is_encrypted if setting else default_config.get("is_encrypted", False)
    value = "" if data.value is None else str(data.value)

    if is_encrypted and value == "********":
        return {"message": "敏感设置未修改", "key": key}

    updated = await system_setting_service.set_setting(
        db,
        key,
        value,
        updated_by=current_user.id
    )
    return {
        "message": "设置已更新",
        "key": updated.key,
        "value": updated.value if not updated.is_encrypted else "********"
    }


@router.post("/settings/init")
async def init_default_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    初始化默认设置（需要 system:settings 权限）
    通常在首次部署时调用
    """
    if not current_user.has_permission("system:settings"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要 system:settings 权限"
        )
    
    await system_setting_service.init_default_settings(db)
    
    return {"message": "默认设置已初始化"}
