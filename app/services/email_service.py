"""
邮件通知服务
用于发送审核结果通知
"""
import logging
import asyncio
from typing import Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from app.core.config import settings
from app.services.system_setting_service import system_setting_service

logger = logging.getLogger(__name__)


class EmailService:
    """
    邮件通知服务
    
    功能：
    1. 发送插件审核结果通知
    2. 支持从管理后台读取 SMTP 配置
    3. 异步发送邮件
    """
    
    def __init__(self):
        self._db_session = None
    
    async def _get_smtp_config(self) -> dict:
        """从数据库获取 SMTP 配置"""
        if self._db_session:
            return await system_setting_service.get_smtp_settings(self._db_session)
        
        # 如果没有数据库会话，使用环境变量配置
        return {
            'smtp_host': getattr(settings, 'SMTP_HOST', None),
            'smtp_port': getattr(settings, 'SMTP_PORT', 587),
            'smtp_user': getattr(settings, 'SMTP_USER', None),
            'smtp_password': getattr(settings, 'SMTP_PASSWORD', None),
            'smtp_tls': getattr(settings, 'SMTP_TLS', True),
            'smtp_from': getattr(settings, 'SMTP_FROM', None),
            'smtp_enabled': bool(getattr(settings, 'SMTP_HOST', None))
        }
    
    def set_db_session(self, db_session):
        """设置数据库会话（用于从管理后台读取配置）"""
        self._db_session = db_session
    
    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        发送邮件（使用标准库 smtplib）
        
        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            html_content: HTML 内容
            text_content: 纯文本内容（可选）
            
        Returns:
            是否发送成功
        """
        # 获取 SMTP 配置
        smtp_config = await self._get_smtp_config()
        
        # 检查是否启用
        if not smtp_config.get('smtp_enabled'):
            logger.warning("SMTP 服务未启用，无法发送邮件")
            return False
        
        # 检查必要配置
        required_fields = ['smtp_host', 'smtp_user', 'smtp_password', 'smtp_from']
        for field in required_fields:
            if not smtp_config.get(field):
                logger.warning(f"SMTP 配置不完整: 缺少 {field}")
                return False
        
        # 在后台线程中执行同步的 smtplib 操作
        def send_sync():
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            try:
                # 创建邮件
                message = MIMEMultipart("alternative")
                message["From"] = smtp_config['smtp_from']
                message["To"] = to_email
                message["Subject"] = subject
                
                # 添加纯文本内容
                if text_content:
                    message.attach(MIMEText(text_content, "plain", "utf-8"))
                
                # 添加 HTML 内容
                message.attach(MIMEText(html_content, "html", "utf-8"))
                
                # 连接 SMTP 服务器
                if smtp_config['smtp_tls']:
                    server = smtplib.SMTP(smtp_config['smtp_host'], smtp_config['smtp_port'])
                    server.starttls()
                else:
                    server = smtplib.SMTP(smtp_config['smtp_host'], smtp_config['smtp_port'])
                
                # 登录
                server.login(smtp_config['smtp_user'], smtp_config['smtp_password'])
                
                # 发送邮件
                server.send_message(message)
                server.quit()
                
                return True
                
            except Exception as e:
                logger.error(f"邮件发送失败: {e}")
                return False
        
        try:
            # 在线程池中执行同步操作
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, send_sync)
            
            if result:
                logger.info(f"邮件发送成功: {to_email}, 主题: {subject}")
            
            return result
            
        except Exception as e:
            logger.error(f"邮件发送失败: {to_email}, 错误: {e}")
            return False
    
    async def send_review_notification(
        self,
        to_email: str,
        plugin_name: str,
        plugin_version: str,
        review_status: str,
        review_result: Optional[dict] = None,
        feedback: Optional[str] = None
    ) -> bool:
        """
        发送审核结果通知
        
        Args:
            to_email: 用户邮箱
            plugin_name: 插件名称
            plugin_version: 插件版本
            review_status: 审核状态 (approved/rejected/needs_revision)
            review_result: 审核结果详情
            feedback: 审核反馈信息
        """
        # 根据状态确定主题和内容
        if review_status == "approved":
            subject = f"✅ 插件审核通过 - {plugin_name} v{plugin_version}"
            status_text = "审核通过"
            status_color = "#10B981"  # 绿色
            icon = "✅"
        elif review_status == "rejected":
            subject = f"❌ 插件审核未通过 - {plugin_name} v{plugin_version}"
            status_text = "审核未通过"
            status_color = "#EF4444"  # 红色
            icon = "❌"
        elif review_status == "needs_revision":
            subject = f"📝 插件需要修改 - {plugin_name} v{plugin_version}"
            status_text = "需要修改"
            status_color = "#F59E0B"  # 黄色
            icon = "📝"
        else:
            subject = f"📋 插件审核状态更新 - {plugin_name} v{plugin_version}"
            status_text = "状态更新"
            status_color = "#3B82F6"  # 蓝色
            icon = "📋"
        
        # 构建 HTML 邮件内容
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {status_color}; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
                .status {{ font-size: 24px; font-weight: bold; margin: 20px 0; color: {status_color}; }}
                .info {{ background-color: white; padding: 15px; border-radius: 6px; margin: 15px 0; }}
                .info-label {{ font-weight: bold; color: #6b7280; }}
                .feedback {{ background-color: #fef3c7; padding: 15px; border-radius: 6px; margin: 15px 0; border-left: 4px solid #f59e0b; }}
                .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 14px; }}
                .button {{ display: inline-block; background-color: {status_color}; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{icon} N.E.K.O 插件市场</h1>
                </div>
                <div class="content">
                    <div class="status">{status_text}</div>
                    
                    <div class="info">
                        <p><span class="info-label">插件名称:</span> {plugin_name}</p>
                        <p><span class="info-label">版本:</span> {plugin_version}</p>
                        <p><span class="info-label">审核时间:</span> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
        """
        
        # 添加评分信息
        if review_result and review_status != "needs_revision":
            final_score = review_result.get('final_score', 0)
            grading = review_result.get('grading', 'N/A')
            html_content += f"""
                    <div class="info">
                        <p><span class="info-label">综合评分:</span> {final_score}/100</p>
                        <p><span class="info-label">评级:</span> {grading}</p>
                    </div>
            """
        
        # 添加反馈信息
        if feedback:
            html_content += f"""
                    <div class="feedback">
                        <p><span class="info-label">审核反馈:</span></p>
                        <p>{feedback}</p>
                    </div>
            """
        
        # 添加操作指引
        if review_status == "approved":
            html_content += """
                    <p>恭喜！您的插件已通过审核，将在插件市场上线。</p>
                    <a href="https://plugins.neko.example.com" class="button">查看插件市场</a>
            """
        elif review_status == "rejected":
            html_content += """
                    <p>很抱歉，您的插件未通过审核。请根据反馈修改后重新提交。</p>
                    <a href="https://plugins.neko.example.com/upload" class="button">重新提交</a>
            """
        elif review_status == "needs_revision":
            html_content += """
                    <p>您的插件需要修改后才能通过审核。请根据反馈进行修改。</p>
                    <a href="https://plugins.neko.example.com/upload" class="button">修改插件</a>
            """
        
        html_content += """
                    <div class="footer">
                        <p>此邮件由 N.E.K.O 插件市场自动发送</p>
                        <p>如有疑问，请联系 support@neko.example.com</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        # 纯文本版本
        text_content = f"""
N.E.K.O 插件市场 - 审核通知

插件名称: {plugin_name}
版本: {plugin_version}
审核状态: {status_text}
审核时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{feedback if feedback else ''}

此邮件由 N.E.K.O 插件市场自动发送
        """
        
        return await self._send_email(to_email, subject, html_content, text_content)

    async def send_email_verification(
        self,
        to_email: str,
        username: str,
        verification_url: str,
        expires_minutes: int
    ) -> bool:
        subject = "验证你的 N.E.K.O 插件市场邮箱"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #e5e7eb; background: #0f0f1a; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 24px; }}
                .panel {{ background: #1a1a2e; border: 1px solid #334155; border-radius: 12px; padding: 28px; }}
                .button {{ display: inline-block; background: #8b5cf6; color: white; padding: 12px 20px; border-radius: 8px; text-decoration: none; font-weight: bold; }}
                .muted {{ color: #94a3b8; font-size: 13px; }}
                .link {{ word-break: break-all; color: #c4b5fd; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="panel">
                    <h1>N.E.K.O 邮箱验证</h1>
                    <p>你好，{username}。</p>
                    <p>点击下面的按钮完成邮箱验证，验证后可以更完整地使用插件提交、通知和账号安全功能。</p>
                    <p><a class="button" href="{verification_url}">验证邮箱</a></p>
                    <p class="muted">链接将在 {expires_minutes} 分钟后过期。如果按钮无法打开，请复制下面的链接到浏览器：</p>
                    <p class="link">{verification_url}</p>
                    <p class="muted">如果不是你发起的注册，请忽略这封邮件。</p>
                </div>
            </div>
        </body>
        </html>
        """
        text_content = f"""
N.E.K.O 邮箱验证

你好，{username}。

请打开下面的链接完成邮箱验证，链接将在 {expires_minutes} 分钟后过期：
{verification_url}

如果不是你发起的注册，请忽略这封邮件。
        """
        return await self._send_email(to_email, subject, html_content, text_content)
    
    async def send_manual_review_notification(
        self,
        to_email: str,
        plugin_name: str,
        plugin_version: str
    ) -> bool:
        """
        发送转人工审核通知
        
        Args:
            to_email: 用户邮箱
            plugin_name: 插件名称
            plugin_version: 插件版本
        """
        subject = f"👥 插件进入人工审核 - {plugin_name} v{plugin_version}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #8B5CF6; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
                .info {{ background-color: white; padding: 15px; border-radius: 6px; margin: 15px 0; }}
                .info-label {{ font-weight: bold; color: #6b7280; }}
                .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>👥 N.E.K.O 插件市场</h1>
                </div>
                <div class="content">
                    <h2>插件进入人工审核</h2>
                    
                    <div class="info">
                        <p><span class="info-label">插件名称:</span> {plugin_name}</p>
                        <p><span class="info-label">版本:</span> {plugin_version}</p>
                        <p><span class="info-label">提交时间:</span> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                    
                    <p>您的插件已进入人工审核阶段，我们的审核团队将尽快完成审核。</p>
                    <p>审核结果将通过邮件通知您，请耐心等待。</p>
                    
                    <div class="footer">
                        <p>此邮件由 N.E.K.O 插件市场自动发送</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
N.E.K.O 插件市场 - 人工审核通知

插件名称: {plugin_name}
版本: {plugin_version}
状态: 进入人工审核

您的插件已进入人工审核阶段，我们的审核团队将尽快完成审核。
审核结果将通过邮件通知您，请耐心等待。
        """
        
        return await self._send_email(to_email, subject, html_content, text_content)
    
    async def send_bulk_notification(
        self,
        notifications: List[dict]
    ) -> dict:
        """
        批量发送通知
        
        Args:
            notifications: 通知列表，每个元素包含 to_email, plugin_name, plugin_version, review_status 等
            
        Returns:
            发送统计信息
        """
        results = {
            "total": len(notifications),
            "success": 0,
            "failed": 0,
            "errors": []
        }
        
        for notification in notifications:
            try:
                success = await self.send_review_notification(**notification)
                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"{notification.get('to_email')}: 发送失败")
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"{notification.get('to_email')}: {str(e)}")
        
        return results


# 全局邮件服务实例
email_service = EmailService()
