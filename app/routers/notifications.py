"""
通知管理路由
提供邮件通知测试和配置接口
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.email_service import email_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


class TestEmailRequest(BaseModel):
    """测试邮件请求"""
    to_email: EmailStr
    subject: str = "测试邮件"
    content: str = "这是一封测试邮件"


class ReviewNotificationRequest(BaseModel):
    """审核通知请求"""
    to_email: EmailStr
    plugin_name: str
    plugin_version: str
    review_status: str  # approved/rejected/needs_revision
    feedback: Optional[str] = None


@router.post("/test")
async def send_test_email(
    data: TestEmailRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    发送测试邮件（需要 system:smtp 权限）
    """
    if not current_user.has_permission("system:smtp"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要 system:smtp 权限"
        )
    
    # 设置数据库会话以读取 SMTP 配置
    email_service.set_db_session(db)
    
    # 构建简单的 HTML 内容
    html_content = f"""
    <html>
    <body>
        <h1>测试邮件</h1>
        <p>{data.content}</p>
        <p>发送时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </body>
    </html>
    """
    
    success = await email_service._send_email(
        to_email=data.to_email,
        subject=data.subject,
        html_content=html_content,
        text_content=data.content
    )
    
    if success:
        return {"message": "测试邮件已发送", "to": data.to_email}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="邮件发送失败，请检查 SMTP 配置"
        )


@router.post("/review-result")
async def send_review_notification(
    data: ReviewNotificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    发送审核结果通知（需要 plugin:review 权限）
    """
    if not current_user.has_permission("plugin:review"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要 plugin:review 权限"
        )
    
    # 设置数据库会话以读取 SMTP 配置
    email_service.set_db_session(db)
    
    success = await email_service.send_review_notification(
        to_email=data.to_email,
        plugin_name=data.plugin_name,
        plugin_version=data.plugin_version,
        review_status=data.review_status,
        feedback=data.feedback
    )
    
    if success:
        return {
            "message": "审核通知已发送",
            "to": data.to_email,
            "plugin": data.plugin_name,
            "status": data.review_status
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="邮件发送失败"
        )


@router.get("/email-status")
async def get_email_service_status(
    current_user: User = Depends(get_current_user)
):
    """
    获取邮件服务状态（需要 system:smtp 权限）
    """
    if not current_user.has_permission("system:smtp"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要 system:smtp 权限"
        )
    
    from app.core.config import settings
    
    return {
        "enabled": email_service.enabled,
        "smtp_host": settings.SMTP_HOST,
        "smtp_port": settings.SMTP_PORT,
        "smtp_user": settings.SMTP_USER,
        "smtp_from": settings.SMTP_FROM,
        "smtp_tls": settings.SMTP_TLS
    }
