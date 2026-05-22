# N.E.KO 插件市场后端

基于 FastAPI + SQLAlchemy + SQLite 构建的插件市场后端 API，支持 AI 自动审核和 EC 代码签名。

## 技术栈

- **FastAPI**: 现代、高性能的 Python Web 框架
- **SQLAlchemy 2.0**: ORM 数据库工具
- **SQLite**: 轻量级数据库（使用 aiosqlite 支持异步）
- **Pydantic**: 数据验证和序列化
- **JWT**: 身份认证
- **GitHub API**: 拉取仓库代码
- **OpenAI API**: AI 自动审核
- **ECDSA (P-256)**: 椭圆曲线数字签名

## 项目结构

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── core/                # 核心配置
│   │   ├── config.py        # 应用配置
│   │   ├── database.py      # 数据库连接
│   │   ├── security.py      # JWT 认证
│   │   └── crypto.py        # EC 签名加密
│   ├── models/              # 数据模型
│   │   ├── plugin.py        # 插件模型
│   │   ├── category.py      # 分类模型
│   │   ├── user.py          # 用户模型
│   │   ├── review.py        # 评论/评分模型
│   │   ├── version.py       # 版本模型
│   │   ├── plugin_category.py  # 插件-分类关联表
│   │   ├── plugin_review.py    # 插件审核记录
│   │   └── plugin_signature.py # 插件签名记录
│   ├── schemas/             # Pydantic 数据模型
│   ├── services/            # 业务逻辑层
│   │   ├── plugin_service.py
│   │   ├── category_service.py
│   │   ├── review_service.py
│   │   ├── version_service.py
│   │   ├── auth_service.py
│   │   ├── github_service.py
│   │   ├── ai_review_service.py
│   │   ├── plugin_review_service.py
│   │   └── signature_service.py  # 签名服务
│   └── routers/             # API 路由
│       ├── auth.py
│       ├── plugins.py
│       ├── categories.py
│       ├── users.py
│       ├── reviews.py
│       ├── versions.py
│       ├── plugin_reviews.py
│       └── signatures.py      # 签名路由
├── pyproject.toml       # Python 项目依赖和测试配置
├── uv.lock              # uv 锁文件
├── requirements.txt     # 旧 pip 工作流兼容文件
└── README.md
```

## 快速启动

项目分为后端 FastAPI 和前端 Vite/React 两部分。以下命令都从项目根目录执行，除非特别说明。

### 1. 准备后端环境

推荐使用 `uv`：

```bash
cd /home/yun_wan/python_programe/neko_plugin_market/N.E.K.O_plugin_py
uv sync --dev
```

也可以使用旧的 `pip + requirements.txt` 工作流：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置后端环境变量

复制模板：

```bash
cp .env.example .env
```

本地开发可保留：

```env
ENVIRONMENT=development
DATABASE_URL=sqlite+aiosqlite:///./plugin_market.db
```

生产环境必须设置高强度 `SECRET_KEY`，不能依赖开发模式自动生成。

### 3. 启动后端

```bash
ENVIRONMENT=development uv run uvicorn app.main:app --reload

# 如需局域网访问
ENVIRONMENT=development uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

注意：必须在项目根目录 `N.E.K.O_plugin_py` 执行，不要在 `app/` 目录里执行。

启动后访问：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health

### 4. 初始化默认分区

后端启动时会自动创建数据库表。如需初始化默认分区：

```bash
ENVIRONMENT=development uv run python init_data.py
```

### 5. 启动前端

```bash
cd NEKO_Plugins_Market
cp .env.example .env.local
npm install
npm run dev
```

前端默认地址：

- http://localhost:5173/
- 管理后台入口：http://localhost:5173/#/admin/login

### 6. 运行测试

后端测试使用内存 SQLite，不会修改本地 `plugin_market.db`：

```bash
cd /home/yun_wan/python_programe/neko_plugin_market/N.E.K.O_plugin_py
ENVIRONMENT=development uv run pytest
```

前端构建检查：

```bash
cd NEKO_Plugins_Market
npm run build
```

### 7. Docker Compose 开发环境

项目提供开发版 Compose，用于快速带走和本地联调：

```bash
cd /home/yun_wan/python_programe/neko_plugin_market/N.E.K.O_plugin_py
docker compose up --build
```

启动后访问：

- 前端：http://localhost:5173/
- 后端：http://localhost:8000/
- API 文档：http://localhost:8000/docs

Compose 会将 SQLite 数据库保存到 `backend_data` volume：

```env
DATABASE_URL=sqlite+aiosqlite:////data/plugin_market.db
```

前端容器内会使用：

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### 8. Docker Compose 生产环境

生产环境请使用 `docker-compose.prod.yml`，不要直接使用开发版 Compose：

```bash
cp .env.production.example .env.production
# 编辑 SECRET_KEY / INITIAL_ADMIN_PASSWORD / MARKET_SITE_ADDRESS / ALLOWED_HOSTS
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

生产版包含：

- Caddy 反向代理与 TLS；
- Vite 静态构建 + nginx；
- FastAPI 后端生产启动；
- Alembic 一次性迁移任务；
- SQLite `/data/plugin_market.db` 持久 volume；
- 在线备份 profile。

在线备份：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm backup
```

更多细节见 `docs/production-deploy.md`。

### 常见问题

#### `ModuleNotFoundError: No module named 'app'`

说明启动命令在错误目录执行。请回到项目根目录：

```bash
cd /home/yun_wan/python_programe/neko_plugin_market/N.E.K.O_plugin_py
ENVIRONMENT=development uv run uvicorn app.main:app --reload
```

#### `email-validator is not installed`

请重新安装依赖：

```bash
uv sync --dev
```

#### 前端无法访问后端 API

检查 `NEKO_Plugins_Market/.env.local`：

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## API 接口概览

### 认证

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/auth/register` | 用户注册 |
| POST | `/api/v1/auth/login` | 用户登录 |
| POST | `/api/v1/auth/refresh` | 刷新令牌 |
| GET | `/api/v1/auth/me` | 获取当前用户信息 |
| POST | `/api/v1/auth/logout` | 用户登出 |

### 插件管理

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | `/api/v1/plugins` | 获取插件列表 | 否 |
| GET | `/api/v1/plugins/featured` | 获取推荐插件 | 否 |
| GET | `/api/v1/plugins/popular` | 获取热门插件 | 否 |
| GET | `/api/v1/plugins/newest` | 获取最新插件 | 否 |
| GET | `/api/v1/plugins/{id}` | 获取插件详情 | 否 |
| GET | `/api/v1/plugins/slug/{slug}` | 通过 slug 获取插件 | 否 |
| POST | `/api/v1/plugins` | 创建插件 | 是 |
| PUT | `/api/v1/plugins/{id}` | 更新插件 | 是（所有者/管理员） |
| DELETE | `/api/v1/plugins/{id}` | 删除插件 | 是（所有者/管理员） |
| POST | `/api/v1/plugins/{id}/download` | 记录下载 | 否 |

### AI 审核流程

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | `/api/v1/plugins/{id}/submit-review` | 提交插件审核 | 是 |
| POST | `/api/v1/reviews/{id}/start-ai-review` | 开始 AI 审核 | 是 |
| POST | `/api/v1/reviews/{id}/submit-revision` | 提交修改 | 是 |
| POST | `/api/v1/reviews/{id}/manual-review` | 人工审核 | 是（管理员） |
| GET | `/api/v1/plugins/{id}/review-history` | 审核历史 | 是 |
| GET | `/api/v1/plugins/{id}/active-review` | 进行中的审核 | 是 |

### 代码签名

#### 公钥管理（管理员）

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | `/api/v1/signatures/admin/keys` | 创建密钥对 | 管理员 |

#### 公钥查询（公开）

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | `/api/v1/signatures/public-keys` | 获取所有公钥 | 否 |
| GET | `/api/v1/signatures/public-keys/default` | 获取默认公钥 | 否 |

#### 插件签名（管理员）

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | `/api/v1/signatures/plugins/{id}/sign` | 生成代码签名 | 管理员 |
| GET | `/api/v1/signatures/plugins/{id}/signatures` | 获取签名列表 | 是 |
| GET | `/api/v1/signatures/plugins/{id}/signatures/{version}` | 获取版本签名 | 是 |
| POST | `/api/v1/signatures/admin/signatures/{id}/revoke` | 撤销签名 | 管理员 |

#### 签名校验（公开）

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | `/api/v1/signatures/verify` | 完整签名验证 | 否 |
| POST | `/api/v1/signatures/verify-simple` | 简化哈希验证 | 否 |

## AI 审核流程

### 审核阶段

```
submitted → fetching → fetched → ai_reviewing → ai_reviewed
                                              ↓
                    ┌───────────────────────────────────────┐
                    ↓                                       ↓
            needs_revision ← revision_submitted      ai_approved → manual_reviewing → approved/rejected
                    ↑_______________________________________|
```

### 审核步骤

1. **提交审核** (`submit-review`)
   - 提供 GitHub 仓库 URL 和分支
   - 系统自动拉取代码

2. **AI 自动审核** (`start-ai-review`)
   - 拉取仓库代码和文件
   - 分析 manifest.json
   - 审核 README 文档
   - 代码安全扫描
   - 生成审核报告和评分

3. **审核结果处理**
   - **通过 (approve)**: AI 评分 ≥ 80 且无严重问题
   - **需要修改 (needs_revision)**: 返回修改建议
   - **拒绝 (reject)**: 存在严重安全问题
   - **转人工 (manual_review)**: AI 不确定的情况

4. **修改和重新审核** (`submit-revision`)
   - 开发者根据反馈修改代码
   - 重新提交进行 AI 审核

5. **人工审核** (`manual-review`)
   - 管理员进行最终审核
   - 可以批准、拒绝或要求修改

### AI 评分维度

- **安全性 (40%)**: 代码安全、依赖安全、权限检查
- **代码质量 (25%)**: 代码规范、可维护性、性能
- **文档完整性 (20%)**: README、注释、示例
- **功能性 (15%)**: 功能实现、兼容性

## 代码签名系统

### 签名流程

1. **创建密钥对**（管理员）
   ```bash
   POST /api/v1/signatures/admin/keys
   {
       "name": "production-key",
       "set_as_default": true
   }
   ```

2. **生成签名**（插件审核通过后）
   ```bash
   POST /api/v1/signatures/plugins/{plugin_id}/sign
   ```
   系统会自动：
   - 从 GitHub 拉取 Python 文件
   - 计算每个文件的 MD5
   - 生成 EC (P-256) 签名
   - 存储签名记录

3. **客户端验证**
   ```bash
   POST /api/v1/signatures/verify
   {
       "plugin_name": "my-plugin",
       "version": "1.0.0",
       "author": "author_name",
       "repo_url": "https://github.com/xxx/neko_plugin_xxx",
       "files": [
           {"path": "main.py", "content": "..."},
           {"path": "utils.py", "content": "..."}
       ],
       "signature": "base64_encoded_signature"
   }
   ```

### 签名格式

签名载荷格式：
```
plugin_name|version|author|repo_url|files_hash
```

其中 `files_hash` 是所有 Python 文件 MD5 的组合哈希。

### 获取公钥

客户端需要公钥来验证签名：
```bash
GET /api/v1/signatures/public-keys
```

返回：
```json
{
  "name": "production-key",
  "public_key": "-----BEGIN PUBLIC KEY-----\n...",
  "is_default": true,
  "created_at": "2024-01-01T00:00:00"
}
```

## 认证说明

所有需要认证的接口需要在请求头中添加：

```
Authorization: Bearer <access_token>
```

获取令牌：
1. 调用 `/api/v1/auth/login` 或 `/api/v1/auth/register`
2. 从响应中获取 `access_token`
3. 在后续请求中使用该令牌

## 环境配置

### 必需配置

- `SECRET_KEY`: JWT 签名密钥（生产环境必须修改）

### 可选配置

- `GITHUB_TOKEN`: GitHub Personal Access Token（用于私有仓库）
- `AI_API_KEY`: OpenAI API Key（用于 AI 审核）
- `AI_MODEL`: AI 模型名称（默认 gpt-4）
- `DATABASE_URL`: 数据库连接字符串（默认 SQLite）

## License

MIT
