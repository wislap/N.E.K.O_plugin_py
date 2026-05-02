from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import secrets


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "production"
    PROJECT_NAME: str = "N.E.K.O Plugin Market"
    VERSION: str = "1.0.0"
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./plugin_market.db"
    DEV_AUTO_CREATE_TABLES: bool = True
    
    # CORS 配置
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # 安全配置 - 生产环境必须从环境变量读取
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Debug auth. Development only; keep disabled in production.
    DEBUG_AUTH_ENABLED: bool = False
    DEBUG_AUTH_USERNAME: str = "debug_user"
    DEBUG_AUTH_EMAIL: str = "debug@example.com"
    DEBUG_AUTH_IS_ADMIN: bool = False

    # Initial administrator bootstrap. Used only when no admin user exists.
    INITIAL_ADMIN_USERNAME: str = "root"
    INITIAL_ADMIN_EMAIL: str = "root@example.com"
    INITIAL_ADMIN_PASSWORD: str = "password"
    
    # 分页配置
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # 签名配置 - 统一私钥（从环境变量或配置文件读取）
    # 如果设置了 SIGNING_PRIVATE_KEY，则使用统一的私钥
    # 否则使用数据库存储的密钥对
    SIGNING_PRIVATE_KEY: Optional[str] = None  # EC 私钥 PEM 格式
    SIGNING_PUBLIC_KEY: Optional[str] = None   # EC 公钥 PEM 格式（可选，可以从私钥推导）
    
    # GitHub 配置
    GITHUB_TOKEN: Optional[str] = None
    
    # AI 审核配置
    AI_API_KEY: Optional[str] = None
    AI_API_BASE: str = "https://api.openai.com/v1"
    AI_MODEL: str = "gpt-4"
    
    # JWT 密钥轮换配置
    JWT_KEY_ROTATION_DAYS: int = 30  # 密钥轮换周期（天）
    JWT_KEY_KEEP_COUNT: int = 3  # 保留的密钥数量
    
    # AI 沙箱配置
    AI_SANDBOX_TIMEOUT: int = 300  # 沙箱执行超时（秒）
    AI_MAX_CONCURRENT: int = 3  # 最大并发任务数
    AI_MAX_CALLS_PER_DAY: int = 1000  # 每日最大调用次数
    
    # 日志保留配置
    REVIEW_LOG_RETENTION_DAYS: int = 90  # 审核日志保留天数
    SANDBOX_LOG_RETENTION_DAYS: int = 30  # 沙箱日志保留天数
    PERMISSION_AUDIT_RETENTION_DAYS: int = 180  # 权限审计日志保留天数
    LOG_CLEANUP_INTERVAL_HOURS: int = 24  # 自动清理间隔（小时）
    
    # SMTP 邮件配置
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    SMTP_FROM: Optional[str] = None  # 发件人地址
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 如果没有设置 SECRET_KEY，生成一个随机密钥（仅用于开发环境）
        if not self.SECRET_KEY:
            import os
            # 检查是否在开发环境
            if self.ENVIRONMENT == "development":
                self.SECRET_KEY = secrets.token_urlsafe(32)
            else:
                raise ValueError(
                    "生产环境必须设置 SECRET_KEY 环境变量！"
                    "请运行: export SECRET_KEY=$(openssl rand -hex 32)"
                )

    @property
    def debug_auth_enabled(self) -> bool:
        return self.ENVIRONMENT == "development" and self.DEBUG_AUTH_ENABLED


settings = Settings()
