"""
系统设置服务
管理后台配置，如 SMTP 设置
"""
import json
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.models.system_setting import SystemSetting, SMTPSettingKeys
from app.core.config import settings


class SystemSettingService:
    """系统设置服务"""
    
    # 默认设置值
    DEFAULT_SETTINGS = {
        # SMTP 默认设置
        SMTPSettingKeys.HOST: {'value': '', 'group': 'smtp', 'description': 'SMTP 服务器地址'},
        SMTPSettingKeys.PORT: {'value': '587', 'group': 'smtp', 'description': 'SMTP 端口'},
        SMTPSettingKeys.USER: {'value': '', 'group': 'smtp', 'description': 'SMTP 用户名'},
        SMTPSettingKeys.PASSWORD: {'value': '', 'group': 'smtp', 'description': 'SMTP 密码', 'is_encrypted': True},
        SMTPSettingKeys.TLS: {'value': 'true', 'group': 'smtp', 'description': '是否使用 TLS'},
        SMTPSettingKeys.FROM: {'value': '', 'group': 'smtp', 'description': '发件人邮箱'},
        SMTPSettingKeys.ENABLED: {'value': 'false', 'group': 'smtp', 'description': '是否启用邮件服务'},
    }
    
    async def init_default_settings(self, db: AsyncSession):
        """初始化默认设置"""
        for key, config in self.DEFAULT_SETTINGS.items():
            # 检查是否已存在
            result = await db.execute(
                select(SystemSetting).where(SystemSetting.key == key)
            )
            if not result.scalar_one_or_none():
                setting = SystemSetting(
                    key=key,
                    value=config['value'],
                    group=config['group'],
                    description=config.get('description'),
                    is_encrypted=config.get('is_encrypted', False)
                )
                db.add(setting)
        
        await db.commit()
    
    async def get_setting(self, db: AsyncSession, key: str) -> Optional[SystemSetting]:
        """获取设置"""
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        return result.scalar_one_or_none()
    
    async def get_setting_value(self, db: AsyncSession, key: str, default: Any = None) -> Any:
        """获取设置值"""
        setting = await self.get_setting(db, key)
        if setting:
            return setting.value
        # 返回默认值
        if key in self.DEFAULT_SETTINGS:
            return self.DEFAULT_SETTINGS[key]['value']
        return default
    
    async def set_setting(
        self,
        db: AsyncSession,
        key: str,
        value: str,
        updated_by: Optional[int] = None
    ) -> SystemSetting:
        """设置值"""
        setting = await self.get_setting(db, key)
        
        if setting:
            setting.value = value
            setting.updated_by = updated_by
        else:
            # 创建新设置
            default_config = self.DEFAULT_SETTINGS.get(key, {})
            setting = SystemSetting(
                key=key,
                value=value,
                group=default_config.get('group', 'general'),
                description=default_config.get('description'),
                is_encrypted=default_config.get('is_encrypted', False),
                updated_by=updated_by
            )
            db.add(setting)
        
        await db.commit()
        await db.refresh(setting)
        return setting
    
    async def get_settings_by_group(
        self,
        db: AsyncSession,
        group: str
    ) -> List[SystemSetting]:
        """获取分组下的所有设置"""
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.group == group)
        )
        return list(result.scalars().all())
    
    async def get_all_settings(
        self,
        db: AsyncSession,
        include_encrypted: bool = False
    ) -> Dict[str, Any]:
        """获取所有设置"""
        result = await db.execute(select(SystemSetting))
        settings_list = result.scalars().all()
        
        settings_dict = {}
        for setting in settings_list:
            if setting.is_encrypted and not include_encrypted:
                settings_dict[setting.key] = '********'  # 隐藏加密值
            else:
                settings_dict[setting.key] = setting.value
        
        return settings_dict

    async def get_all_setting_records(self, db: AsyncSession) -> List[SystemSetting]:
        """获取所有设置记录"""
        result = await db.execute(
            select(SystemSetting).order_by(SystemSetting.group, SystemSetting.key)
        )
        return list(result.scalars().all())
    
    # ========== SMTP 设置快捷方法 ==========
    
    async def get_smtp_settings(self, db: AsyncSession) -> Dict[str, Any]:
        """获取 SMTP 设置"""
        smtp_settings = {}
        
        for key in [
            SMTPSettingKeys.HOST,
            SMTPSettingKeys.PORT,
            SMTPSettingKeys.USER,
            SMTPSettingKeys.PASSWORD,
            SMTPSettingKeys.TLS,
            SMTPSettingKeys.FROM,
            SMTPSettingKeys.ENABLED
        ]:
            value = await self.get_setting_value(db, key)
            
            # 类型转换
            if key == SMTPSettingKeys.PORT:
                value = int(value) if value else 587
            elif key == SMTPSettingKeys.TLS:
                value = value.lower() == 'true'
            elif key == SMTPSettingKeys.ENABLED:
                value = value.lower() == 'true'
            
            smtp_settings[key] = value
        
        return smtp_settings
    
    async def update_smtp_settings(
        self,
        db: AsyncSession,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        tls: Optional[bool] = None,
        from_email: Optional[str] = None,
        enabled: Optional[bool] = None,
        updated_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """更新 SMTP 设置"""
        updates = {}
        
        if host is not None:
            await self.set_setting(db, SMTPSettingKeys.HOST, host, updated_by)
            updates['host'] = host
        
        if port is not None:
            await self.set_setting(db, SMTPSettingKeys.PORT, str(port), updated_by)
            updates['port'] = port
        
        if user is not None:
            await self.set_setting(db, SMTPSettingKeys.USER, user, updated_by)
            updates['user'] = user
        
        if password is not None:
            await self.set_setting(db, SMTPSettingKeys.PASSWORD, password, updated_by)
            updates['password'] = '********'
        
        if tls is not None:
            await self.set_setting(db, SMTPSettingKeys.TLS, str(tls).lower(), updated_by)
            updates['tls'] = tls
        
        if from_email is not None:
            await self.set_setting(db, SMTPSettingKeys.FROM, from_email, updated_by)
            updates['from'] = from_email
        
        if enabled is not None:
            await self.set_setting(db, SMTPSettingKeys.ENABLED, str(enabled).lower(), updated_by)
            updates['enabled'] = enabled
        
        return updates
    
    async def test_smtp_connection(self, db: AsyncSession) -> Dict[str, Any]:
        """测试 SMTP 连接"""
        smtp_settings = await self.get_smtp_settings(db)
        
        if not smtp_settings.get(SMTPSettingKeys.ENABLED):
            return {
                "success": False,
                "message": "SMTP 服务未启用"
            }
        
        if not smtp_settings.get(SMTPSettingKeys.HOST):
            return {
                "success": False,
                "message": "SMTP 服务器地址未配置"
            }
        
        try:
            import aiosmtplib
            
            # 尝试连接 SMTP 服务器
            await aiosmtplib.connect(
                hostname=smtp_settings[SMTPSettingKeys.HOST],
                port=smtp_settings[SMTPSettingKeys.PORT],
                start_tls=smtp_settings[SMTPSettingKeys.TLS]
            )
            
            return {
                "success": True,
                "message": "SMTP 连接测试成功"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"SMTP 连接失败: {str(e)}"
            }


# 全局设置服务实例
system_setting_service = SystemSettingService()
