from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.plugin_signature import PluginSignature, ServerKeyPair
from app.models.plugin import Plugin
from app.core.crypto import CodeSignatureService, generate_server_keypair
from app.services.github_service import GitHubService


class SignatureService:
    """插件签名服务"""
    
    def __init__(self):
        self.crypto_service = CodeSignatureService()
        self.github_service = GitHubService()
    
    # ========== 服务器密钥管理 ==========
    
    async def create_keypair(
        self,
        db: AsyncSession,
        name: str,
        set_as_default: bool = False
    ) -> ServerKeyPair:
        """创建新的服务器密钥对"""
        # 检查名称是否已存在
        result = await db.execute(
            select(ServerKeyPair).where(ServerKeyPair.name == name)
        )
        if result.scalar_one_or_none():
            raise ValueError(f"密钥名称 '{name}' 已存在")
        
        # 生成密钥对
        private_key, public_key = generate_server_keypair()
        
        # TODO: 在实际生产环境中应该加密存储私钥
        # 这里简化处理，直接存储
        
        keypair = ServerKeyPair(
            name=name,
            public_key=public_key,
            private_key_encrypted=private_key,  # 应该加密
            is_active=True,
            is_default=set_as_default,
            activated_at=datetime.utcnow()
        )
        
        # 如果设置为默认，取消其他默认密钥
        if set_as_default:
            result = await db.execute(
                select(ServerKeyPair).where(ServerKeyPair.is_default == True)
            )
            existing_defaults = result.scalars().all()
            for kd in existing_defaults:
                kd.is_default = False
        
        db.add(keypair)
        await db.commit()
        await db.refresh(keypair)
        
        return keypair
    
    async def get_default_keypair(self, db: AsyncSession) -> Optional[ServerKeyPair]:
        """获取默认密钥对"""
        result = await db.execute(
            select(ServerKeyPair).where(
                and_(
                    ServerKeyPair.is_default == True,
                    ServerKeyPair.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_keypair_by_name(
        self,
        db: AsyncSession,
        name: str
    ) -> Optional[ServerKeyPair]:
        """通过名称获取密钥对"""
        result = await db.execute(
            select(ServerKeyPair).where(ServerKeyPair.name == name)
        )
        return result.scalar_one_or_none()
    
    async def get_keypair_by_id(
        self,
        db: AsyncSession,
        keypair_id: int
    ) -> Optional[ServerKeyPair]:
        """通过 ID 获取密钥对"""
        return await db.get(ServerKeyPair, keypair_id)
    
    async def get_all_public_keys(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """获取所有激活的公钥"""
        result = await db.execute(
            select(ServerKeyPair).where(ServerKeyPair.is_active == True)
        )
        keypairs = result.scalars().all()
        
        return [
            {
                "id": kp.id,
                "name": kp.name,
                "public_key": kp.public_key,
                "is_default": kp.is_default,
                "is_active": kp.is_active,
                "created_at": kp.created_at
            }
            for kp in keypairs
        ]
    
    async def deactivate_keypair(
        self,
        db: AsyncSession,
        keypair_id: int
    ) -> ServerKeyPair:
        """停用密钥对"""
        keypair = await self.get_keypair_by_id(db, keypair_id)
        if not keypair:
            raise ValueError("密钥对不存在")
        
        keypair.is_active = False
        keypair.deactivated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(keypair)
        return keypair
    
    # ========== 插件签名 ==========
    
    async def sign_plugin_from_github(
        self,
        db: AsyncSession,
        plugin_id: int,
        keypair_id: Optional[int] = None
    ) -> PluginSignature:
        """
        从 GitHub 拉取代码并签名
        
        Args:
            plugin_id: 插件 ID
            keypair_id: 使用的密钥对 ID，默认使用默认密钥
        """
        # 获取插件信息
        plugin = await db.get(Plugin, plugin_id)
        if not plugin:
            raise ValueError("插件不存在")
        
        if not plugin.repo_url:
            raise ValueError("插件未配置 GitHub 仓库地址")
        
        # 获取密钥对
        if keypair_id:
            keypair = await self.get_keypair_by_id(db, keypair_id)
        else:
            keypair = await self.get_default_keypair(db)
        
        if not keypair:
            raise ValueError("未找到可用的签名密钥")
        
        if not keypair.is_active:
            raise ValueError("密钥对已停用")
        
        # 从 GitHub 拉取 Python 文件
        try:
            tree = await self.github_service.get_repo_tree(
                plugin.repo_url,
                recursive=True,
                ref=plugin.repo_branch or "main"
            )
            
            # 筛选 Python 文件
            py_files = [
                item for item in tree
                if item['path'].endswith('.py') and item['type'] == 'blob'
            ]
            
            if not py_files:
                raise ValueError("仓库中没有找到 Python 文件")
            
            # 获取文件内容
            files = []
            for file_item in py_files:
                try:
                    content = await self.github_service.get_file_content(
                        plugin.repo_url,
                        file_item['path'],
                        plugin.repo_branch or "main"
                    )
                    files.append({
                        "path": file_item['path'],
                        "content": content
                    })
                except Exception:
                    continue
            
            # 执行签名
            sign_result = self.crypto_service.sign_plugin(
                private_key_pem=keypair.private_key_encrypted,
                plugin_name=plugin.name,
                version=plugin.version,
                author=plugin.author_name,
                repo_url=plugin.repo_url,
                files=files
            )
            
            # 创建签名记录
            signature_record = PluginSignature(
                plugin_id=plugin_id,
                keypair_id=keypair.id,
                signature=sign_result["signature"],
                files_hash=sign_result["files_hash"],
                files_md5=sign_result["files_md5"],
                payload=sign_result["payload"],
                plugin_name=plugin.name,
                version=plugin.version,
                author=plugin.author_name,
                repo_url=plugin.repo_url,
                is_valid=True
            )
            
            db.add(signature_record)
            await db.commit()
            await db.refresh(signature_record)
            
            return signature_record
            
        except Exception as e:
            raise ValueError(f"签名失败: {str(e)}")
    
    async def get_plugin_signatures(
        self,
        db: AsyncSession,
        plugin_id: int,
        valid_only: bool = True
    ) -> List[PluginSignature]:
        """获取插件的所有签名"""
        query = select(PluginSignature).where(
            PluginSignature.plugin_id == plugin_id
        )
        
        if valid_only:
            query = query.where(PluginSignature.is_valid == True)
        
        query = query.order_by(desc(PluginSignature.created_at))
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_signature_by_version(
        self,
        db: AsyncSession,
        plugin_id: int,
        version: str
    ) -> Optional[PluginSignature]:
        """获取指定版本的签名"""
        result = await db.execute(
            select(PluginSignature).where(
                and_(
                    PluginSignature.plugin_id == plugin_id,
                    PluginSignature.version == version,
                    PluginSignature.is_valid == True
                )
            )
        )
        return result.scalar_one_or_none()
    
    # ========== 签名验证 ==========
    
    async def verify_signature(
        self,
        db: AsyncSession,
        plugin_name: str,
        version: str,
        author: str,
        repo_url: str,
        files: List[Dict[str, str]],
        signature: str
    ) -> Dict[str, Any]:
        """
        验证插件签名
        
        Args:
            plugin_name: 插件名称
            version: 版本号
            author: 作者名
            repo_url: 仓库地址
            files: [{"path": "...", "content": "..."}]
            signature: Base64 签名
            
        Returns:
            {
                "valid": bool,
                "message": str,
                "files_hash": str,
                "signature_info": {...}
            }
        """
        # 查找对应的签名记录
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
                "files_hash": None,
                "signature_info": None
            }
        
        # 获取签名时使用的公钥
        keypair = await self.get_keypair_by_id(db, sig_record.keypair_id)
        if not keypair:
            return {
                "valid": False,
                "message": "签名使用的密钥对不存在",
                "files_hash": None,
                "signature_info": None
            }
        
        # 验证签名
        is_valid = self.crypto_service.verify_plugin(
            public_key_pem=keypair.public_key,
            plugin_name=plugin_name,
            version=version,
            author=author,
            repo_url=repo_url,
            files=files,
            signature=signature
        )
        
        # 更新验证时间
        sig_record.verified_at = datetime.utcnow()
        await db.commit()
        
        # 计算当前文件哈希
        files_md5 = []
        for file_info in files:
            md5 = self.crypto_service.calculate_file_md5(file_info["content"])
            files_md5.append({
                "path": file_info["path"],
                "md5": md5
            })
        files_hash = self.crypto_service.calculate_files_hash(files_md5)
        
        return {
            "valid": is_valid,
            "message": "签名验证成功" if is_valid else "签名验证失败",
            "files_hash": files_hash,
            "expected_hash": sig_record.files_hash,
            "hash_match": files_hash == sig_record.files_hash,
            "signature_info": {
                "created_at": sig_record.created_at,
                "keypair_name": keypair.name,
                "public_key": keypair.public_key
            }
        }
    
    async def revoke_signature(
        self,
        db: AsyncSession,
        signature_id: int,
        reason: str,
        revoked_by: int
    ) -> PluginSignature:
        """撤销签名"""
        sig = await db.get(PluginSignature, signature_id)
        if not sig:
            raise ValueError("签名记录不存在")
        
        sig.is_valid = False
        sig.revoked_at = datetime.utcnow()
        sig.revoke_reason = reason
        
        await db.commit()
        await db.refresh(sig)
        
        return sig
