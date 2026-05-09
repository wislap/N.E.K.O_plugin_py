from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.routers import plugins, categories, users, reviews, versions, auth, signatures, zones, notifications, submissions
from app.routers.oauth import router as oauth_router
from app.routers.admin import categories as admin_categories
from app.routers.admin import dashboard as admin_dashboard
from app.routers.admin import logs as admin_logs
from app.routers.admin import permissions as admin_permissions
from app.routers.admin import review as admin_review
from app.routers.admin import settings as admin_settings
from app.routers.admin import signatures as admin_signatures
from app.routers.admin import users as admin_users
from app.routers.admin import zones as admin_zones
from app.middleware.request_id import REQUEST_ID_HEADER, request_id_middleware
from app.services.bootstrap_service import BootstrapService
from app.services.permission_service import PermissionService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 开发环境可自动补表；生产环境应通过 Alembic 管理数据库结构。
    if settings.ENVIRONMENT == "development" and settings.DEV_AUTO_CREATE_TABLES:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
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

app.middleware("http")(request_id_middleware)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[REQUEST_ID_HEADER],
)

# 注册路由
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(plugins.router, prefix="/api/v1", tags=["plugins"])
app.include_router(categories.router, prefix="/api/v1", tags=["categories"])
app.include_router(zones.router, prefix="/api/v1", tags=["zones"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])
app.include_router(reviews.router, prefix="/api/v1", tags=["reviews"])
app.include_router(versions.router, prefix="/api/v1", tags=["versions"])
app.include_router(signatures.router, prefix="/api/v1/signatures", tags=["signatures"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(submissions.router, prefix="/api/v1", tags=["review-submissions"])
app.include_router(oauth_router, prefix="/api/v1", tags=["oauth"])
app.include_router(admin_dashboard.router, prefix="/api/v1/admin", tags=["admin-dashboard"])
app.include_router(admin_review.router, prefix="/api/v1/admin", tags=["admin-review"])
app.include_router(admin_users.router, prefix="/api/v1/admin", tags=["admin-users"])
app.include_router(admin_permissions.router, prefix="/api/v1/admin", tags=["admin-permissions"])
app.include_router(admin_categories.router, prefix="/api/v1/admin", tags=["admin-categories"])
app.include_router(admin_zones.router, prefix="/api/v1/admin", tags=["admin-zones"])
app.include_router(admin_signatures.router, prefix="/api/v1/admin", tags=["admin-signatures"])
app.include_router(admin_settings.router, prefix="/api/v1/admin", tags=["admin-settings"])
app.include_router(admin_logs.router, prefix="/api/v1/admin", tags=["admin-logs"])


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
