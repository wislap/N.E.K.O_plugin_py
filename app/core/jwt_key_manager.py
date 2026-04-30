"""
JWT 密钥管理器
支持密钥自动轮换、多密钥兼容验证
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.core.config import settings
from app.models.jwt_key import JWTKeyRecord


class JWTKeyManager:
    """JWT 密钥管理器"""
    
    def __init__(self):
        self._current_key: Optional[str] = None
        self._key_id: Optional[str] = None
    
    async def initialize(self, db: AsyncSession):
        """初始化密钥管理器"""
        # 检查是否需要轮换密钥
        await self._check_and_rotate_keys(db)
        
        # 加载当前主密钥
        await self._load_primary_key(db)
    
    def _generate_key(self) -> tuple:
        """生成新密钥和密钥ID"""
        # 生成 256 位随机密钥
        secret = secrets.token_urlsafe(32)
        # 生成密钥ID（基于密钥的哈希）
        key_id = hashlib.sha256(secret.encode()).hexdigest()[:16]
        return key_id, secret
    
    async def _check_and_rotate_keys(self, db: AsyncSession):
        """检查并轮换密钥"""
        # 获取当前主密钥
        result = await db.execute(
            select(JWTKeyRecord).where(
                and_(
                    JWTKeyRecord.is_primary == True,
                    JWTKeyRecord.is_active == True
                )
            )
        )
        primary_key = result.scalar_one_or_none()
        
        # 如果没有主密钥，创建新密钥
        if not primary_key:
            await self._create_new_key(db, set_as_primary=True)
            return
        
        # 检查密钥是否需要轮换（默认 30 天）
        rotation_days = getattr(settings, 'JWT_KEY_ROTATION_DAYS', 30)
        rotation_threshold = datetime.utcnow() - timedelta(days=rotation_days)
        
        if primary_key.created_at < rotation_threshold:
            await self._rotate_key(db)
    
    async def _create_new_key(
        self,
        db: AsyncSession,
        set_as_primary: bool = False
    ) -> JWTKeyRecord:
        """创建新密钥"""
        key_id, secret = self._generate_key()
        
        key_record = JWTKeyRecord(
            key_id=key_id,
            secret_key=secret,
            is_active=True,
            is_primary=set_as_primary,
            activated_at=datetime.utcnow() if set_as_primary else None
        )
        
        db.add(key_record)
        await db.commit()
        await db.refresh(key_record)
        
        return key_record
    
    async def _rotate_key(self, db: AsyncSession):
        """轮换密钥"""
        # 1. 将当前主密钥降级为普通密钥
        result = await db.execute(
            select(JWTKeyRecord).where(
                and_(
                    JWTKeyRecord.is_primary == True,
                    JWTKeyRecord.is_active == True
                )
            )
        )
        current_primary = result.scalar_one_or_none()
        
        if current_primary:
            current_primary.is_primary = False
        
        # 2. 创建新主密钥
        new_key = await self._create_new_key(db, set_as_primary=True)
        
        # 3. 清理过期密钥（保留最近 3 个）
        await self._cleanup_old_keys(db)
        
        await db.commit()
        
        # 更新内存中的密钥
        self._current_key = new_key.secret_key
        self._key_id = new_key.key_id
    
    async def _cleanup_old_keys(self, db: AsyncSession, keep_count: int = 3):
        """清理旧密钥，只保留最近的几个"""
        result = await db.execute(
            select(JWTKeyRecord).where(
                JWTKeyRecord.is_active == True
            ).order_by(desc(JWTKeyRecord.created_at))
        )
        all_keys = list(result.scalars().all())
        
        # 保留主密钥和最近的几个密钥
        keys_to_keep = set()
        for key in all_keys:
            if key.is_primary:
                keys_to_keep.add(key.id)
        
        # 添加最近的几个密钥
        for key in all_keys:
            if len(keys_to_keep) < keep_count + 1:  # +1 因为主密钥已经包含
                keys_to_keep.add(key.id)
        
        # 停用其他密钥
        for key in all_keys:
            if key.id not in keys_to_keep:
                key.is_active = False
                key.deactivated_at = datetime.utcnow()
    
    async def _load_primary_key(self, db: AsyncSession):
        """加载主密钥到内存"""
        result = await db.execute(
            select(JWTKeyRecord).where(
                and_(
                    JWTKeyRecord.is_primary == True,
                    JWTKeyRecord.is_active == True
                )
            )
        )
        primary_key = result.scalar_one_or_none()
        
        if primary_key:
            self._current_key = primary_key.secret_key
            self._key_id = primary_key.key_id
        else:
            # 如果没有主密钥，创建一个
            new_key = await self._create_new_key(db, set_as_primary=True)
            self._current_key = new_key.secret_key
            self._key_id = new_key.key_id
    
    def get_current_key(self) -> str:
        """获取当前主密钥"""
        if not self._current_key:
            # 如果内存中没有密钥，使用配置中的密钥（向后兼容）
            return settings.SECRET_KEY
        return self._current_key
    
    def get_key_id(self) -> Optional[str]:
        """获取当前密钥ID"""
        return self._key_id
    
    async def get_key_by_id(self, db: AsyncSession, key_id: str) -> Optional[str]:
        """通过密钥ID获取密钥（用于验证旧令牌）"""
        result = await db.execute(
            select(JWTKeyRecord).where(
                and_(
                    JWTKeyRecord.key_id == key_id,
                    JWTKeyRecord.is_active == True
                )
            )
        )
        key_record = result.scalar_one_or_none()
        
        if key_record:
            return key_record.secret_key
        return None
    
    async def verify_token_with_key_id(
        self,
        db: AsyncSession,
        token: str,
        key_id: str
    ) -> Optional[dict]:
        """使用指定密钥ID验证令牌"""
        from jose import jwt as jose_jwt, JWTError
        
        secret = await self.get_key_by_id(db, key_id)
        if not secret:
            return None
        
        try:
            payload = jose_jwt.decode(
                token,
                secret,
                algorithms=[settings.ALGORITHM]
            )
            return payload
        except JWTError:
            return None
    
    async def force_rotate_key(self, db: AsyncSession) -> JWTKeyRecord:
        """强制轮换密钥（管理员操作）"""
        return await self._rotate_key(db)
    
    async def get_all_active_keys(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """获取所有激活的密钥信息（不包含密钥值）"""
        result = await db.execute(
            select(JWTKeyRecord).where(
                JWTKeyRecord.is_active == True
            ).order_by(desc(JWTKeyRecord.created_at))
        )
        keys = result.scalars().all()
        
        return [
            {
                "key_id": key.key_id,
                "is_primary": key.is_primary,
                "created_at": key.created_at,
                "activated_at": key.activated_at
            }
            for key in keys
        ]


# 全局密钥管理器实例
jwt_key_manager = JWTKeyManager()
