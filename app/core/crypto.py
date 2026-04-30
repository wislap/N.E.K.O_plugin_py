import hashlib
import base64
from typing import Tuple, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend

from app.core.config import settings


class ECSignatureManager:
    """EC (椭圆曲线) 签名管理器"""
    
    def __init__(self):
        self._private_key: Optional[ec.EllipticCurvePrivateKey] = None
        self._public_key: Optional[ec.EllipticCurvePublicKey] = None
    
    def generate_keypair(self) -> Tuple[str, str]:
        """
        生成新的 EC 密钥对 (P-256 曲线)
        
        Returns:
            (private_key_pem, public_key_pem)
        """
        self._private_key = ec.generate_private_key(
            ec.SECP256R1(),  # P-256 曲线
            default_backend()
        )
        self._public_key = self._private_key.public_key()
        
        # 序列化私钥
        private_pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        # 序列化公钥
        public_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        return private_pem, public_pem
    
    def load_private_key(self, private_key_pem: str):
        """加载私钥"""
        self._private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None,
            backend=default_backend()
        )
        self._public_key = self._private_key.public_key()
    
    def load_public_key(self, public_key_pem: str):
        """加载公钥"""
        self._public_key = serialization.load_pem_public_key(
            public_key_pem.encode('utf-8'),
            backend=default_backend()
        )
    
    def sign(self, data: bytes) -> str:
        """
        使用私钥对数据进行签名
        
        Args:
            data: 待签名的数据
            
        Returns:
            base64 编码的签名
        """
        if not self._private_key:
            raise ValueError("私钥未加载")
        
        # 计算 SHA256 哈希
        digest = hashlib.sha256(data).digest()
        
        # 使用 ECDSA 签名
        signature = self._private_key.sign(
            digest,
            ec.ECDSA(Prehashed(hashes.SHA256()))
        )
        
        return base64.b64encode(signature).decode('utf-8')
    
    def verify(self, data: bytes, signature_b64: str) -> bool:
        """
        使用公钥验证签名
        
        Args:
            data: 原始数据
            signature_b64: base64 编码的签名
            
        Returns:
            签名是否有效
        """
        if not self._public_key:
            raise ValueError("公钥未加载")
        
        try:
            # 解码签名
            signature = base64.b64decode(signature_b64)
            
            # 计算 SHA256 哈希
            digest = hashlib.sha256(data).digest()
            
            # 验证签名
            self._public_key.verify(
                signature,
                digest,
                ec.ECDSA(Prehashed(hashes.SHA256()))
            )
            return True
        except InvalidSignature:
            return False
        except Exception:
            return False
    
    def get_public_key_pem(self) -> str:
        """获取公钥 PEM 格式"""
        if not self._public_key:
            raise ValueError("公钥未加载")
        
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')


class CodeSignatureService:
    """代码签名服务"""
    
    def __init__(self):
        self.ec_manager = ECSignatureManager()
    
    def calculate_file_md5(self, content: str) -> str:
        """计算文件内容的 MD5 哈希"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def calculate_files_hash(self, files: list) -> str:
        """
        计算多个文件的组合哈希
        
        Args:
            files: [{"path": "...", "md5": "..."}, ...]
            
        Returns:
            组合哈希值
        """
        # 按路径排序确保一致性
        sorted_files = sorted(files, key=lambda x: x['path'])
        
        # 拼接所有 MD5
        combined = ''.join(f["md5"] for f in sorted_files)
        
        # 计算最终 MD5
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def create_signature_payload(
        self,
        plugin_name: str,
        version: str,
        author: str,
        repo_url: str,
        files_hash: str
    ) -> str:
        """
        创建签名载荷
        
        格式: plugin_name|version|author|repo_url|files_hash
        """
        return f"{plugin_name}|{version}|{author}|{repo_url}|{files_hash}"
    
    def parse_signature_payload(self, payload: str) -> dict:
        """解析签名载荷"""
        parts = payload.split('|')
        if len(parts) != 5:
            raise ValueError("无效的签名载荷格式")
        
        return {
            "plugin_name": parts[0],
            "version": parts[1],
            "author": parts[2],
            "repo_url": parts[3],
            "files_hash": parts[4]
        }
    
    def sign_plugin(
        self,
        private_key_pem: str,
        plugin_name: str,
        version: str,
        author: str,
        repo_url: str,
        files: list
    ) -> dict:
        """
        对插件进行签名
        
        Args:
            private_key_pem: 私钥 PEM
            plugin_name: 插件名称
            version: 版本号
            author: 作者名
            repo_url: 仓库地址
            files: [{"path": "...", "content": "..."}, ...]
            
        Returns:
            {
                "signature": "base64签名",
                "files_hash": "文件哈希",
                "files_md5": [{"path": "...", "md5": "..."}],
                "payload": "签名载荷"
            }
        """
        # 加载私钥
        self.ec_manager.load_private_key(private_key_pem)
        
        # 计算每个文件的 MD5
        files_md5 = []
        for file_info in files:
            md5 = self.calculate_file_md5(file_info["content"])
            files_md5.append({
                "path": file_info["path"],
                "md5": md5
            })
        
        # 计算文件组合哈希
        files_hash = self.calculate_files_hash(files_md5)
        
        # 创建签名载荷
        payload = self.create_signature_payload(
            plugin_name, version, author, repo_url, files_hash
        )
        
        # 签名
        signature = self.ec_manager.sign(payload.encode('utf-8'))
        
        return {
            "signature": signature,
            "files_hash": files_hash,
            "files_md5": files_md5,
            "payload": payload
        }
    
    def verify_plugin(
        self,
        public_key_pem: str,
        plugin_name: str,
        version: str,
        author: str,
        repo_url: str,
        files: list,
        signature: str
    ) -> bool:
        """
        验证插件签名
        
        Args:
            public_key_pem: 公钥 PEM
            plugin_name: 插件名称
            version: 版本号
            author: 作者名
            repo_url: 仓库地址
            files: [{"path": "...", "content": "..."}, ...]
            signature: base64 签名
            
        Returns:
            签名是否有效
        """
        # 加载公钥
        self.ec_manager.load_public_key(public_key_pem)
        
        # 计算文件哈希
        files_md5 = []
        for file_info in files:
            md5 = self.calculate_file_md5(file_info["content"])
            files_md5.append({
                "path": file_info["path"],
                "md5": md5
            })
        
        files_hash = self.calculate_files_hash(files_md5)
        
        # 重建载荷
        payload = self.create_signature_payload(
            plugin_name, version, author, repo_url, files_hash
        )
        
        # 验证签名
        return self.ec_manager.verify(payload.encode('utf-8'), signature)


# 全局签名管理器实例
signature_manager = CodeSignatureService()


def generate_server_keypair() -> Tuple[str, str]:
    """生成服务器密钥对"""
    ec_manager = ECSignatureManager()
    return ec_manager.generate_keypair()


# 统一签名密钥管理类
class UnifiedSigningKey:
    """统一签名密钥管理 - 从配置读取"""
    
    _instance = None
    _private_key: Optional[str] = None
    _public_key: Optional[str] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_keys()
        return cls._instance
    
    def _load_keys(self):
        """从配置加载密钥"""
        # 优先从环境变量/配置文件读取
        if settings.SIGNING_PRIVATE_KEY:
            self._private_key = settings.SIGNING_PRIVATE_KEY
            # 从私钥推导公钥
            ec_manager = ECSignatureManager()
            ec_manager.load_private_key(self._private_key)
            self._public_key = ec_manager.get_public_key_pem()
        elif settings.SIGNING_PUBLIC_KEY:
            self._public_key = settings.SIGNING_PUBLIC_KEY
    
    @property
    def private_key(self) -> Optional[str]:
        return self._private_key
    
    @property
    def public_key(self) -> Optional[str]:
        return self._public_key
    
    @property
    def is_configured(self) -> bool:
        """检查是否配置了统一私钥"""
        return self._private_key is not None
    
    def sign(self, data: bytes) -> str:
        """使用统一私钥签名"""
        if not self._private_key:
            raise ValueError("统一签名私钥未配置")
        
        ec_manager = ECSignatureManager()
        ec_manager.load_private_key(self._private_key)
        return ec_manager.sign(data)
    
    def verify(self, data: bytes, signature_b64: str) -> bool:
        """使用统一公钥验证"""
        if not self._public_key:
            raise ValueError("统一签名公钥未配置")
        
        ec_manager = ECSignatureManager()
        ec_manager.load_public_key(self._public_key)
        return ec_manager.verify(data, signature_b64)


# 统一签名密钥实例
unified_signing_key = UnifiedSigningKey()
