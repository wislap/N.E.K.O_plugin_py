from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.routers import plugins, categories, users, reviews, versions, auth, plugin_reviews, signatures, zones, permissions, logs, notifications, admin_settings
from app.services.bootstrap_service import BootstrapService
from app.services.permission_service import PermissionService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        await BootstrapService.ensure_schema_compatibility(db)
        await BootstrapService.ensure_initial_admin(db)
        await PermissionService().init_system_permissions(db)
    
    yield
    
    # 关闭时清理资源
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="N.E.K.O 插件市场后端 API",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(plugins.router, prefix="/api/v1", tags=["plugins"])
app.include_router(categories.router, prefix="/api/v1", tags=["categories"])
app.include_router(zones.router, prefix="/api/v1", tags=["zones"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])
app.include_router(reviews.router, prefix="/api/v1", tags=["reviews"])
app.include_router(versions.router, prefix="/api/v1", tags=["versions"])
app.include_router(plugin_reviews.router, prefix="/api/v1", tags=["plugin_reviews"])
app.include_router(signatures.router, prefix="/api/v1/signatures", tags=["signatures"])
app.include_router(permissions.router, prefix="/api/v1", tags=["permissions"])
app.include_router(logs.router, prefix="/api/v1", tags=["logs"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(admin_settings.router, prefix="/api/v1/admin", tags=["admin-settings"])


@app.get("/")
async def root():
    return {
        "message": "Welcome to N.E.KO Plugin Market API",
        "version": settings.VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
