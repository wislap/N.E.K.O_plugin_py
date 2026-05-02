"""Shared helpers for demo data scripts."""
from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEMO_EMAIL_DOMAIN = "neko-demo.com"
LEGACY_DEMO_EMAIL_DOMAINS = ["demo.local"]
DEMO_PASSWORD = "password123"
DEMO_PLUGIN_SLUG_PREFIX = "demo-"
DEMO_REPO_OWNER = "neko-plugin-demo"


def assert_demo_seed_allowed() -> None:
    """Require an explicit opt-in before mutating local demo data."""
    if os.getenv("DEMO_SEED_ENABLED", "").lower() in {"1", "true", "yes", "on"}:
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            raise SystemExit("Demo seed is blocked while ENVIRONMENT=production.")
        return

    raise SystemExit(
        "DEMO_SEED_ENABLED is not enabled.\n"
        "Run with: DEMO_SEED_ENABLED=true uv run python scripts/seed_demo_data.py"
    )


def demo_email(username: str) -> str:
    return f"{username}@{DEMO_EMAIL_DOMAIN}"


def demo_repo(name: str) -> str:
    return f"https://github.com/{DEMO_REPO_OWNER}/n.e.k.o_plugin_{name}"


DEMO_USERS = [
    {
        "username": "alice",
        "email": demo_email("alice"),
        "display_name": "Alice Demo",
        "is_admin": False,
        "bio": "普通提交者，用于测试上传、我的插件和审核反馈。",
    },
    {
        "username": "bob",
        "email": demo_email("bob"),
        "display_name": "Bob Demo",
        "is_admin": False,
        "bio": "第二个普通用户，用于测试多作者数据。",
    },
    {
        "username": "reviewer",
        "email": demo_email("reviewer"),
        "display_name": "Reviewer Demo",
        "is_admin": True,
        "bio": "演示审核员账号，可进入管理员面板。",
    },
]


DEFAULT_ZONES = [
    {
        "name": "游戏区",
        "slug": "game",
        "description": "游戏辅助、数据查询、攻略工具",
        "icon": "Gamepad2",
        "color": "#EF4444",
        "sort_order": 1,
    },
    {
        "name": "陪玩区",
        "slug": "companion",
        "description": "陪玩匹配、语音互动、社交工具",
        "icon": "Heart",
        "color": "#EC4899",
        "sort_order": 2,
    },
    {
        "name": "功能区",
        "slug": "function",
        "description": "实用工具、效率提升、系统增强",
        "icon": "Settings",
        "color": "#3B82F6",
        "sort_order": 3,
    },
    {
        "name": "娱乐区",
        "slug": "entertainment",
        "description": "趣味插件、休闲娱乐、互动玩法",
        "icon": "Sparkles",
        "color": "#8B5CF6",
        "sort_order": 4,
    },
    {
        "name": "工具区",
        "slug": "tool",
        "description": "开发工具、调试助手、管理工具",
        "icon": "Wrench",
        "color": "#10B981",
        "sort_order": 5,
    },
]


DEFAULT_CATEGORIES = [
    {
        "name": "效率工具",
        "slug": "productivity",
        "description": "提升日常使用效率的插件",
        "icon": "Zap",
        "sort_order": 1,
    },
    {
        "name": "游戏辅助",
        "slug": "game-helper",
        "description": "游戏资料、攻略和辅助查询",
        "icon": "Gamepad2",
        "sort_order": 2,
    },
    {
        "name": "开发调试",
        "slug": "developer-tools",
        "description": "面向插件作者的开发工具",
        "icon": "Code",
        "sort_order": 3,
    },
]


DEMO_PLUGINS = [
    {
        "name": "天气提醒助手",
        "slug": "demo-weather-helper",
        "author": "alice",
        "status": "approved",
        "zone": "function",
        "categories": ["productivity"],
        "repo": demo_repo("weather_helper"),
        "short_description": "根据城市和关键词推送天气提醒。",
        "description": "一个结构完整的半真实插件样本，用于测试已上架插件的展示、详情和下载链路。",
        "tags": ["天气", "提醒", "效率"],
        "download_count": 128,
        "likes": 34,
        "rating_average": 4.7,
        "rating_count": 18,
        "review_note": "结构清晰，README 和安装说明完整，允许上架。",
        "ai_score": 91,
        "ai_recommendation": "approve",
    },
    {
        "name": "音乐点歌面板",
        "slug": "demo-music-panel",
        "author": "alice",
        "status": "pending",
        "zone": "entertainment",
        "categories": ["productivity"],
        "repo": demo_repo("music_panel"),
        "short_description": "房间点歌和歌单管理面板。",
        "description": "待审核插件样本，用于测试管理员面板的审核通过/拒绝闭环。",
        "tags": ["音乐", "面板", "娱乐"],
        "download_count": 0,
        "likes": 0,
        "rating_average": 0,
        "rating_count": 0,
        "review_note": "",
        "ai_score": 76,
        "ai_recommendation": "manual_review",
    },
    {
        "name": "不安全命令执行测试",
        "slug": "demo-unsafe-exec",
        "author": "bob",
        "status": "rejected",
        "zone": "tool",
        "categories": ["developer-tools"],
        "repo": demo_repo("unsafe_exec"),
        "short_description": "包含高风险命令执行逻辑的拒绝样本。",
        "description": "拒绝状态插件样本，用于测试用户侧拒绝原因展示和管理员筛选。",
        "tags": ["安全", "测试", "拒绝"],
        "download_count": 0,
        "likes": 0,
        "rating_average": 0,
        "rating_count": 0,
        "review_note": "检测到高风险命令执行入口，请移除 shell 调用并补充权限说明后重新提交。",
        "ai_score": 38,
        "ai_recommendation": "reject",
    },
    {
        "name": "游戏资料查询",
        "slug": "demo-game-lookup",
        "author": "bob",
        "status": "approved",
        "zone": "game",
        "categories": ["game-helper"],
        "repo": demo_repo("game_lookup"),
        "short_description": "查询角色、装备和攻略资料。",
        "description": "第二个已上架样本，用于测试首页列表、热门排序和多作者数据。",
        "tags": ["游戏", "查询", "攻略"],
        "download_count": 356,
        "likes": 81,
        "rating_average": 4.9,
        "rating_count": 42,
        "review_note": "功能边界明确，权限申请合理，准许上架。",
        "ai_score": 94,
        "ai_recommendation": "approve",
    },
    {
        "name": "旧版翻译助手",
        "slug": "demo-disabled-translator",
        "author": "alice",
        "status": "disabled",
        "zone": "function",
        "categories": ["productivity"],
        "repo": demo_repo("translator_legacy"),
        "short_description": "已禁用的历史版本样本。",
        "description": "禁用状态插件样本，用于测试管理员能看见、市场不展示的场景。",
        "tags": ["翻译", "旧版", "禁用"],
        "download_count": 88,
        "likes": 12,
        "rating_average": 3.8,
        "rating_count": 9,
        "review_note": "依赖接口已失效，暂时禁用展示。",
        "ai_score": 66,
        "ai_recommendation": "manual_review",
    },
]


DEMO_REVIEWS = [
    {
        "plugin": "demo-weather-helper",
        "author": "bob",
        "rating": 5,
        "title": "提醒稳定",
        "content": "城市配置和关键词提醒都能跑通，适合测试详情页评论展示。",
    },
    {
        "plugin": "demo-game-lookup",
        "author": "alice",
        "rating": 5,
        "title": "资料很全",
        "content": "搜索结果和 README 内容足够完整，适合用来测试热门插件。",
    },
]


DEMO_NOTIFICATIONS = [
    {
        "user": "alice",
        "plugin": "demo-weather-helper",
        "type": "plugin_review",
        "title": "天气提醒助手已通过审核",
        "content": "结构清晰，README 和安装说明完整，允许上架。",
        "target_url": "/my/plugins",
        "is_read": False,
    },
    {
        "user": "alice",
        "plugin": "demo-music-panel",
        "type": "plugin_review",
        "title": "音乐点歌面板正在等待审核",
        "content": "管理员可以在插件审核面板中处理这个待审核样本。",
        "target_url": "/my/plugins",
        "is_read": False,
    },
    {
        "user": "bob",
        "plugin": "demo-unsafe-exec",
        "type": "plugin_review",
        "title": "不安全命令执行测试未通过审核",
        "content": "检测到高风险命令执行入口，请移除 shell 调用并补充权限说明后重新提交。",
        "target_url": "/my/plugins",
        "is_read": False,
    },
]
