# Implementation Plan — Market 插件版本管理

## Overview

按"错误类型 → 数据迁移 / ORM → Release_Fetcher → VersionService → 投影 → 路由 → 后端测试 → 前端类型 / 组件 / 页面 → 端到端"的顺序实施，全程保持每个任务可独立开 PR 并独立验收。**带 `*` 的子任务为可选测试任务，可在 MVP 阶段跳过**。任务 1–12 为必做，13 为可选打磨。

实现栈：

- 后端：Python 3.11 + FastAPI + SQLAlchemy 2.x + aiosqlite + httpx；测试用 pytest-asyncio + Hypothesis + respx。
- 前端：React 19 + TypeScript + react-hook-form + zod + sonner + @tanstack/react-query；e2e 用 Playwright。
- 部署假设：FastAPI + uvicorn 单 worker + SQLite，partial unique index 兜底并发。

> 跨任务约定：所有错误响应统一返回 `{"detail": "...", "code": "<error_code>"}`；前端 `getErrorMessage` 优先按 `code` 查中文文案表，找不到回退 `detail`。

---

## Tasks

- [x] 1. 错误类型与全局 exception handler
  在 `app/errors/version_errors.py` 定义 `VersionDomainError` / `ReleaseFetchError`（继承前者）与 `ERROR_CODE_TO_HTTP` 映射；在 `app/main.py` 注册 `@app.exception_handler(VersionDomainError)`，把异常转成统一 JSON 结构。是后续 service / 路由层抛错的基础。
  - 创建 `app/errors/__init__.py` 与 `app/errors/version_errors.py`，包含 9 个错误码常量与到 HTTP 状态码的映射（403/400/400/413/502/409/409/404/400）
  - `app/main.py` 注册全局 handler，命中时返回 `JSONResponse({"detail": exc.message, "code": exc.code}, status_code=...)`
  - 验收：在临时路由内 `raise VersionDomainError("forbidden", "no")` 调用 `curl` 返回 HTTP 403 + `{"detail":"no","code":"forbidden"}`
  - _Requirements: R9.1, R9.2_

- [x] 2. Release_Fetcher 模块
  在 `app/services/release_fetcher.py` 实现 `ReleaseFetcher.fetch_and_resolve(release_url, plugin_repo_url) -> ResolvedRelease`，覆盖 release_url 解析 / owner-repo 校验 / GitHub release 元数据获取 / 资产流式下载 / sha256 计算 / metadata.toml 解析 / commit sha 解析 / 1 次重试。本任务依赖任务 1 的错误类型。
  - [x] 2.1 实现 `_parse_release_url` 与 `_check_repo_match`
    解析 `https://github.com/{owner}/{repo}/releases/tag/{tag}` 与 `releases/{id}` 两种形式，与 plugin.repo_url 做 casefold 比较，不一致抛 `ReleaseFetchError("release_repo_mismatch", ...)`
    - _Requirements: R3.3_
  - [x] 2.2 实现 `_fetch_release_metadata` 与 `_pick_asset`
    GET `/repos/{o}/{r}/releases/tags/{tag}`（404 → `release_publish_failed`）；遍历 `assets`，选第一个 `name.lower().endswith(".neko-plugin"/".neko-bundle")`，未命中抛 `release_asset_not_found`
    - _Requirements: R3.5, R3.6_
  - [x] 2.3 实现 `_stream_download_asset`
    `httpx.AsyncClient(follow_redirects=True)` + `headers={"Accept-Encoding": "identity"}`；按 64KB chunk 同步喂 `hashlib.sha256` 与 `io.BytesIO`；累计字节超过 200 MiB 抛 `release_asset_too_large`；返回 `(asset_bytes, package_sha256)`
    - _Requirements: R3.7, R3.8_
  - [x] 2.4 实现 `_parse_metadata_toml` 与 `_resolve_commit_sha`
    用 `zipfile.ZipFile(io.BytesIO(asset_bytes))` 打开，`tomllib.loads(...)` 取 `[payload].hash`；`zipfile.BadZipFile` / `KeyError` / `tomllib.TOMLDecodeError` / `UnicodeDecodeError` 全部吞掉返 `None`，永不让 publish 整体失败。`target_commitish` 是 40-hex 直接用，否则 GET `/commits/{ref}` 取 `sha`
    - _Requirements: R3.9, R3.10, R3.11_
  - [x] 2.5 实现 1 次重试与错误归一化
    对 `httpx.ConnectError` / `httpx.ReadTimeout` / `httpx.RemoteProtocolError` / 5xx / 429，`asyncio.sleep(0.5)` 后重试一次；仍失败抛 `release_publish_failed`
    - _Requirements: R9.3_
  - [ ]* 2.6 单元测试 `tests/unit/test_release_fetcher_parsing.py`
    覆盖 release_url 解析边界、owner/repo 大小写不敏感比较、metadata.toml 损坏 / 缺字段 / 非法 hex 各种坏形式（**Property P4：metadata.toml 解析鲁棒性**），断言 `payload_hash` 要么是 64-hex 要么是 None，永不抛
    - _Requirements: R3.3, R3.9_
    - _Properties: P4_

- [x] 3. Alembic 迁移脚本与数据搬运
  在 `alembic/versions/` 新增迁移文件（`down_revision = '20260505_0001'`），按 design 7 步骨架完成：加新列 → backfill `channel`/`is_latest` → 为有 `download_url` 但无 version 行的 plugin 补 legacy version 行 → 强制 NOT NULL + CHECK + FK → 建 partial unique index 与 (plugin_id, version) 唯一索引 → 删 `plugins.version` / `plugins.download_url`。
  - [x] 3.1 编写 `upgrade()`
    `batch_alter_table("versions", recreate="auto")` 加 6 列；执行 backfill SQL（含 `ROW_NUMBER() OVER (PARTITION BY plugin_id ORDER BY created_at DESC, id DESC)` 标记 `is_latest`）；对 `plugins.download_url IS NOT NULL` 但 `versions` 表无对应行的插入 legacy `version` 行（`verification_status='legacy_unverified'`、`package_sha256=''` 占位）；改 `channel`/`is_latest` 为 NOT NULL，加 `ck_versions_channel`、`fk_versions_yanked_by_users`、`fk_versions_published_by_users`、补 `plugin_id` 的 `ondelete='CASCADE'`；用 `op.create_index(..., sqlite_where=sa.text("is_latest = 1"))` 建 partial unique index；最后 `batch_alter_table("plugins")` 删两列
    - _Requirements: R1.1, R1.2, R1.3, R1.4, R1.5, R1.6, R1.7, R1.8, R2.1, R2.2, R2.3, R2.4, R2.5_
  - [x] 3.2 编写 `downgrade()`
    drop 索引 / 约束 / FK / 6 列；恢复 `plugins.version`（NOT NULL DEFAULT '0.0.0'）与 `plugins.download_url`（nullable）。明确不还原数据搬运
    - _Requirements: R1.9_
  - [ ]* 3.3 迁移集成测试 `tests/integration/test_migration.py`
    在临时 SQLite 上 seed `plugins(download_url='https://x/pkg.neko-plugin', version='1.0.0')` 但无 versions、以及 `plugins+versions` 双表都有的两种 fixture；运行 `alembic upgrade head`；断言：
    - 第一种 plugin 在 versions 表多出 1 行 `is_latest=true, channel='stable', verification_status='legacy_unverified'`
    - 第二种 plugin 的 versions 表 `created_at desc` 第一条 `is_latest=true`
    - `plugins` 表已无 `version` / `download_url` 列（`PRAGMA table_info(plugins)` 校验）
    - _Requirements: R2.1, R2.2, R2.3, R2.4, R2.5_

- [ ] 4. ORM 模型与 Pydantic Schema 更新
  把 `app/models/version.py` 加上 6 个新字段 + `CheckConstraint`；从 `app/models/plugin.py` 删除 `version` / `download_url` 列引用与 `to_frontend_dict` 内分支；重写 `app/schemas/version.py`（删 `VersionCreate`，新增 `VersionPublishRequest` / `VersionYankRequest` / `Version` / `VersionYankResponse`）；在 `app/schemas/plugin.py` 加 `LatestVersionPublic` 与 `Plugin.latest_version`。本任务必须与任务 3 的迁移同 PR 或紧邻 PR，避免代码与 schema 漂移。
  - [x] 4.1 修改 `app/models/version.py`
    加 `channel` / `is_latest` / `yanked_at` / `yanked_reason` / `yanked_by` / `published_by` 列与对应 FK；`__table_args__` 添加 `CheckConstraint("channel IN ('stable','beta')", name="ck_versions_channel")`
    - _Requirements: R1.1, R1.2, R1.3, R1.4, R1.5, R1.6_
  - [x] 4.2 修改 `app/models/plugin.py`
    删除 `version` 列、`download_url` 列；从 `to_frontend_dict()` 中移除对这两列的读取；保留 `versions` relationship
    - _Requirements: R2.6, R6.5_
  - [x] 4.3 重写 `app/schemas/version.py`
    删除 `VersionCreate`；新增 `VersionPublishRequest`（`release_url: str`、`channel: Literal["stable","beta"]="stable"`、`changelog: str | None`）、`VersionYankRequest`（`reason: str = Field(..., min_length=1, max_length=500)`）、`Version`（含全部新字段）、`VersionYankResponse`
    - _Requirements: R3.1, R4.1, R5.8, R8.1_
  - [x] 4.4 修改 `app/schemas/plugin.py`
    新增 `LatestVersionPublic`（version / channel / package_url / package_sha256 / payload_hash / created_at）；从 `Plugin` / `PluginList` / `PluginDetail` 移除 `version` 与 `download_url`，加 `latest_version: LatestVersionPublic | None = None`
    - _Requirements: R6.1, R6.2_

- [x] 5. VersionService 重写
  把 `app/services/version_service.py` 删除旧 `create_version` / `delete_version` / `_sync_plugin_current_version`；新增 `publish_from_release` / `yank` / `list_versions` / `get_latest`，所有写操作都在 `commit_or_rollback(db)` 内执行，捕获 `IntegrityError` 转成 `version_already_exists`。本任务依赖任务 1（错误类型）、任务 2（ReleaseFetcher）、任务 4（新模型 / schema）。
  - [x] 5.1 实现 `publish_from_release`
    校验 `channel ∈ {"stable","beta"}`（否则 `invalid_channel`）→ 校验权限（非作者非 admin → `forbidden`）→ 调 `ReleaseFetcher.fetch_and_resolve` → 事务内：`UPDATE versions SET is_latest=false WHERE plugin_id=? AND channel=? AND is_latest=true` + `INSERT new Version(is_latest=true, channel=?, package_sha256=resolved.package_sha256, payload_hash=resolved.payload_hash, ...)` → `IntegrityError` 转 `version_already_exists` → 写结构化日志 `version.publish_from_release`
    - _Requirements: R3.1, R3.2, R3.4, R3.13, R3.14, R3.15, R3.16, R9.1_
  - [x] 5.2 实现 `yank`
    校验权限 + `version.plugin_id == plugin.id` + `version.yanked_at is None`（否则 `version_already_yanked`）→ 事务内设 `yanked_at` / `yanked_reason` / `yanked_by`；如该版本 `is_latest`，置 false 并 SELECT 同 (plugin_id, channel) 中 `yanked_at IS NULL` 且 `created_at desc, id desc` 第一条置 `is_latest=true` → 提交后调 `NotificationService.add(user_id=plugin.author_id, type="version.yanked", ...)` 与 audit log → 返回 `(yanked, promoted)`
    - _Requirements: R4.1, R4.2, R4.3, R4.4, R4.5, R4.6, R4.7_
  - [x] 5.3 实现 `list_versions` 与 `get_latest`
    `list_versions(plugin_id, channel?, include_yanked=False)` 按 `created_at desc` 返回；`include_yanked=False` 时过滤 `yanked_at IS NULL`。`get_latest(plugin_id, channel="stable")` 仅返回 `is_latest=true AND yanked_at IS NULL`，找不到由调用方抛 `latest_version_not_found`
    - _Requirements: R5.3, R5.4, R5.6, R5.7_
  - [ ]* 5.4 单元测试 `tests/unit/test_version_service.py`
    覆盖：channel 非法 → `invalid_channel`；非作者非 admin → `forbidden`；release owner/repo 不匹配 → `release_repo_mismatch`；同 (plugin, version) 二次插入 → `version_already_exists`；yank 已 yanked → `version_already_yanked`；yank latest 后晋级到次新 / 无候选时 latest 为空
    - _Requirements: R3.2, R3.4, R3.12, R4.2, R4.3, R4.4_

- [x] 6. Plugin 投影集成 attach_latest_version
  新增 `app/services/plugin_projection.py` 实现 `attach_latest_version(db, plugins, channel="stable")`，按 `plugin_id IN (...)` + `channel=? AND is_latest=true AND yanked_at IS NULL` 单次 SELECT 批量挂载到 `plugin.__dict__["latest_version"]`；在 `app/services/plugin_service.py` 与 `app/routers/plugins.py` 所有暴露 plugin 对象的入口处调用一次。
  - [x] 6.1 创建 `app/services/plugin_projection.py`
    签名 `async def attach_latest_version(db, plugins: list[Plugin], *, channel: str = "stable") -> None`；空列表早返回；用一次 `select(Version).where(Version.plugin_id.in_(...))` 批量取
    - _Requirements: R6.3, R6.4_
  - [x] 6.2 集成到 `plugin_service.py` 与 `routers/plugins.py`
    在 `get_plugins` / `get_plugin_by_id` / `get_by_slug` / 任何返回 Plugin / list[Plugin] 的方法返回前调一次；`Pydantic` 序列化时 `from_attributes=True` 会读 `latest_version` 临时属性
    - _Requirements: R6.1, R6.2, R6.5_
  - [ ]* 6.3 单元测试 `tests/unit/test_plugin_projection.py`
    fixture 准备 plugin A 在 stable 有非 yanked latest、plugin B 仅 beta 有 latest、plugin C 唯一 stable 被 yanked；调 `attach_latest_version(channel="stable")` 后断言：A.latest_version 非空、B.latest_version 为 None、C.latest_version 为 None
    - _Requirements: R6.3, R6.4_

- [x] 7. 版本路由层重写
  改写 `app/routers/versions.py`：删除旧 `POST /plugins/{id}/versions`、`DELETE /plugins/{id}/versions/{version_id}`、`PATCH` 路由；新增 `POST /plugins/{id}/versions/publish-from-release`、`POST /plugins/{id}/versions/{version_id}/yank`；重写 `GET /plugins/{id}/versions`（支持 `channel` / `include_yanked`）与 `GET /plugins/{id}/versions/latest`（仅返回 is_latest=true AND yanked_at IS NULL，未命中抛 `latest_version_not_found`）。本任务依赖任务 4（schema）、任务 5（service）。
  - [x] 7.1 删除旧路由
    从 `app/routers/versions.py` 物理删除 `create_version` / `delete_version` / `update_version` 三个 handler 及其装饰器；FastAPI 自动 404
    - _Requirements: R8.1, R8.2, R8.3_
  - [x] 7.2 实现 publish-from-release 与 yank
    `publish_from_release` 路由：依赖 `get_current_user`，调 `VersionService.publish_from_release`，返回 201 + `Version`；`yank` 路由：先 `_ensure_plugin` + `get_version_by_id` 校验归属 (404)，再调 service 返 `VersionYankResponse`
    - _Requirements: R3.1, R3.2, R3.16, R4.1, R4.2_
  - [x] 7.3 重写 list 与 latest
    `list_plugin_versions(channel: Literal["stable","beta"] | None = None, include_yanked: bool = False)`；`get_latest_version(channel: Literal["stable","beta"] = "stable")`，service 返 None 时抛 `VersionDomainError("latest_version_not_found", ...)`
    - _Requirements: R5.1, R5.2, R5.3, R5.4, R5.5, R5.6, R5.7, R5.8_
  - [ ]* 7.4 路由级测试 `tests/unit/test_versions_router.py`
    断言：旧 POST/DELETE/PATCH 端点返 404；未登录调 publish/yank 返 401；非作者非 admin 调返 403 `forbidden`
    - _Requirements: R3.2, R4.2, R8.1, R8.2, R8.3_

- [x] 8. PBT 测试套件 P0–P4
  在 `tests/properties/conftest.py` 实现 fixture `mock_github_release` / `make_plugin` / `build_zip_with_metadata` / `auth_headers`；在 `tests/properties/test_version_management.py` 实现 P0–P3 四条性质（P4 已并入任务 2.6）。每条性质至少 100 次 Hypothesis 迭代，状态机式探索使用 `RuleBasedStateMachine`。
  - [x] 8.1 实现 PBT fixtures `tests/properties/conftest.py`
    `mock_github_release(asset_bytes, tag, owner, repo, target_commitish)` 用 `respx_mock` 注册 `releases/tags/{tag}` 与 asset URL；`make_plugin` 用 SQLAlchemy session 插一条 APPROVED plugin；`build_zip_with_metadata(asset_bytes, payload_hash)` 用 `zipfile.ZipFile` 写出含 `metadata.toml` 与 payload 的最小 zip；`auth_headers(author_id)` 签 JWT
    - _Requirements: R0.1, R3.5_
  - [x]* 8.2 P0 — 下载链路 sha256 严格一致
    `@given(asset_bytes=st.binary(min_size=4, max_size=10*1024)) @settings(max_examples=200)` → `publish-from-release` → 断言响应 `package_sha256 == hashlib.sha256(asset_bytes_in_zip).hexdigest()`、64-hex lowercase；GET `package_url` 再算 sha256 严格相等
    - **Property P0: 发版后下载链路 sha256 严格一致**
    - _Requirements: R0.1, R0.2, R0.3, R0.4, R3.8_
    - _Properties: P0_
  - [ ]* 8.3 P1+P2 — VersionStateMachine
    `RuleBasedStateMachine`：`@rule publish(channel)` / `@rule yank(version)`；`@invariant at_most_one_latest_per_channel`（每个 (plugin, channel) 满足 `is_latest=true AND yanked_at IS NULL` 的行数 ≤ 1）+ `@invariant latest_is_max_non_yanked`（若存在非 yanked 版本则 latest 是 created_at 最大那条，否则 latest 行数 = 0）；至少 50 步 / 例
    - **Property P1: (plugin_id, channel) is_latest 唯一性**
    - **Property P2: yank latest 后 latest 永远指向最大非 yanked 版本**
    - _Requirements: R1.8, R3.13, R4.4, R5.6, R6.3_
    - _Properties: P1, P2_
  - [ ]* 8.4 P3 — 并发同 release_url 唯一获胜者
    `asyncio.gather(*[client.post(publish-from-release, json={release_url})] * 10)`；断言 `len(success)==1`、`len(conflicts)==9`，所有 conflict 响应 `code == "version_already_exists"`，DB 中该 (plugin_id, version) 行数恰好 1
    - **Property P3: (plugin_id, version) 唯一约束在并发下成立**
    - _Requirements: R3.12, R3.13_
    - _Properties: P3_

- [ ] 9. 后端集成测试覆盖矩阵
  在 `tests/integration/test_publish_from_release.py` 与 `tests/integration/test_yank.py` 用 example-based 测试覆盖 design 错误码矩阵的 11 行用例。本任务复用任务 8.1 的 fixtures。
  - [x] 9.1 publish-from-release 矩阵
    覆盖：作者 201 成功、非作者非 admin 403 `forbidden`、release owner/repo 不匹配 400 `release_repo_mismatch`、release 中无 .neko-plugin / .neko-bundle 400 `release_asset_not_found`、asset 超 200 MiB 413 `release_asset_too_large`、GitHub 5xx 重试后仍失败 502 `release_publish_failed`、重复 (plugin, version) 409 `version_already_exists`、非法 channel 400 `invalid_channel`
    - _Requirements: R3.2, R3.3, R3.6, R3.7, R3.12, R3.14, R9.1, R9.2_
  - [x] 9.2 yank 与 latest 矩阵
    覆盖：yank 已 yanked 409 `version_already_yanked`、yank latest 后查 latest 返回次新 (200) / 无次新返 404 `latest_version_not_found`、`latest` 在无版本时 404 `latest_version_not_found`、yank latest 触发 `NotificationService.add` 写一行通知
    - _Requirements: R4.3, R4.4, R4.5, R5.7_

- [x] 10. 前端类型 / service / mappers 重构
  修改 `NEKO_Plugins_Market/src/services/types.ts`：移除 `Plugin.version` / `Plugin.download_url`，新增 `LatestVersion` 与 `Plugin.latest_version`，扩展 `PluginVersion` 字段；重写 `services/versions.ts`（`list` / `latest` / `publishFromRelease` / `yank`，删除 `create`）；改造 `services/mappers.ts` 让 `toMarketPlugin` 改读 `plugin.latest_version.package_url`，**移除 fallback 到 `repo_url`** 的旧逻辑。
  - [x] 10.1 修改 `services/types.ts`
    新增 `LatestVersion` / `VersionPublishRequest` / `VersionYankRequest` / `VersionYankResponse`；扩展 `PluginVersion` 含 `channel` / `is_latest` / `yanked_at` / `yanked_reason` / `yanked_by` / `published_by` / `payload_hash`；从 `Plugin` 删除 `version` / `download_url`、加 `latest_version: LatestVersion | null`
    - _Requirements: R6.1, R6.2_
  - [x] 10.2 重写 `services/versions.ts`
    `versionsApi.list(pluginId, {channel?, includeYanked?})` / `latest(pluginId, channel?="stable")` / `publishFromRelease(pluginId, body)` / `yank(pluginId, versionId, body)`；删除旧 `create`；导出错误码 → 中文文案表（9 项）
    - _Requirements: R3.1, R4.1, R5.1, R5.2, R5.5, R7.9, R9.2_
  - [x] 10.3 改造 `services/mappers.ts`
    `toMarketPlugin` 改读 `plugin.latest_version?.package_url ?? ""` 与 `plugin.latest_version?.version ?? ""`；**删除 `download_url ?? repo_url` 的 fallback**
    - _Requirements: R6.1, R6.2, R6.4_
  - [ ]* 10.4 mappers 单元测试
    断言：`plugin.latest_version === null` 时 `mapped.version === ""` 且 `mapped.downloadUrl === ""`，**不再** fallback 到 `repo_url`
    - _Requirements: R6.4_

- [x] 11. 前端版本管理组件
  在 `NEKO_Plugins_Market/src/components/versions/` 新增三个组件：`VersionList.tsx`（详情页 Versions tab 主体）、`PublishFromReleaseDialog.tsx`（react-hook-form + zod URL 校验 + 错误码 toast 映射）、`YankDialog.tsx`（撤回原因表单 + 晋级提示 toast）。
  - [x] 11.1 实现 `VersionList.tsx`
    `useQuery(["plugin", pluginId, "versions", {channel, includeYanked}])` 调 `versionsApi.list`；channel filter（按钮组：全部 / stable / beta，默认全部）+ `<Switch>` 包含已撤回（默认 true）；每行渲染版本号 / channel 徽章（stable=绿，beta=橙）/ sha256 前 12 位（点击展开）/ created_at 本地时间 / changelog（marked 渲染）/ latest 徽章 / 已撤回灰阶 + reason hover；当 `isAuthor || isAdmin` 显示"发布新版本"与"撤回"按钮；`isAdmin && !isAuthor` 时按钮文案改为"管理员撤回"
    - _Requirements: R7.1, R7.2, R7.3, R7.4, R7.5, R7.6, R7.7_
  - [x] 11.2 实现 `PublishFromReleaseDialog.tsx`
    `useForm` + zod schema：`release_url: z.string().url()` / `channel: z.enum(["stable","beta"]).default("stable")` / `changelog: z.string().optional()`；`onSubmit` 调 `versionsApi.publishFromRelease`；提交中按钮 disabled + "拉取 release 中..."；失败按 `error.code` 查错误码表 `toast.error(message)`，成功 `toast.success("v{version} ({channel}) 已发布")` 并 `onSuccess()`
    - _Requirements: R7.8, R7.9, R9.1, R9.2_
  - [x] 11.3 实现 `YankDialog.tsx`
    `useForm` + zod `reason: z.string().min(1).max(500)`；标题文案 `isAdminAction ? "管理员撤回 v{version}" : "撤回 v{version}"`；`onSubmit` 调 `versionsApi.yank` 成功后 `toast.success("已撤回 v{version}")`，`resp.promoted != null` 时再 `toast.info("已自动晋级 v{promoted.version} 为最新")`，最后 `onSuccess()` 触发列表 invalidate
    - _Requirements: R4.1, R4.4, R7.10_

- [x] 12. 前端页面集成 PluginDetail + MyPlugins
  把版本组件挂到 `pages/PluginDetail.tsx`（新增 Versions tab + URL query 自动开 Dialog），在 `pages/MyPlugins.tsx` 已发布插件卡片新增"发布新版本"按钮 + "尚未发布版本"空态。
  - [x] 12.1 修改 `pages/PluginDetail.tsx`
    Tabs 新增 `<TabsTrigger value="versions">版本</TabsTrigger>`；挂载 `<VersionList pluginId={...} plugin={plugin} />`；`useEffect` 监听 `searchParams.get("tab")==="versions"` + `searchParams.get("action")==="publish"`，组件 mount 时自动打开 `<PublishFromReleaseDialog>`
    - _Requirements: R7.1, R7.11_
  - [x] 12.2 修改 `pages/MyPlugins.tsx`
    每张已发布插件卡片右下角加 `<Button onClick={() => navigate(`/plugin/${id}?tab=versions&action=publish`)}>发布新版本</Button>`；当 `plugin.latest_version === null` 时卡片上显示灰色徽章"尚未发布版本"，详情页版本 tab 显示"该插件尚未发布任何版本"提示
    - _Requirements: R7.11, R7.12_

- [ ] 13. Playwright e2e
  在 `NEKO_Plugins_Market/tests/` 新增 `versions.spec.ts` 与 `versions-yank.spec.ts`，覆盖端到端发版与撤回两条核心路径。GitHub API 在 backend 进程内通过 respx 或 dev_reset 数据兜底（不要打真 GitHub）。本任务依赖任务 1–12 全部就绪。
  - [ ] 13.1 编写 `tests/versions.spec.ts`
    作者登录 → 访问 `/plugin/{id}` → 切到 Versions tab → 点"发布新版本" → 填 `release_url`（指向 mock 数据）+ channel=stable + changelog → 断言 `toast.success` 出现 + 列表新增一行 + 该行带 latest 徽章
    - _Requirements: R3.1, R7.1, R7.6, R7.8, R7.9_
  - [ ] 13.2 编写 `tests/versions-yank.spec.ts`
    fixture 预置至少两个 stable 版本 → 作者点击 latest 行的"撤回"按钮 → 填理由 → 断言被撤回行变灰 + "已撤回"徽章 + reason hover 显示 + 次新版本出现"最新"徽章
    - _Requirements: R4.1, R4.4, R5.6, R7.10_
  - [ ] 13.3 在 `scripts/dev_reset.py` 增加 e2e 数据
    预置一个作者账号 + 一个 APPROVED 插件 + 至少两条 stable channel 的 version（用于晋级断言）；预置一个可被 mock 的 release_url（或在 backend 测试模式下注入 respx route）
    - _Requirements: R0.1, R3.1_

- [ ] 14. 依赖与文档（可选）
  收尾任务：在 `pyproject.toml` 加 PBT 依赖、更新 `uv.lock`、在 `README.md` 写"版本管理 / 发版流程"小节。
  - [ ]* 14.1 更新 `pyproject.toml` 与 `uv.lock`
    `[dependency-groups].dev` 增加 `hypothesis==6.108.5` 与 `respx==0.21.1`；运行 `uv lock` 刷新 lock
    - _Requirements: -_
  - [ ]* 14.2 更新 `README.md`
    新增"版本管理"小节：`publish-from-release` 用法（含 curl 示例）、channel 语义、yank 行为、9 项错误码表、并附"待客户端 spec 适配的 breaking change"提示（plugin 顶层 `version` / `download_url` 移除 + `latest` 不再 fallback）
    - _Requirements: R6.1, R6.2_

---

## Notes

- 顶层任务从底层基础设施往上层 UI 推进；测试任务（2.6 / 3.3 / 5.4 / 6.3 / 7.4 / 8 / 9 / 10.4 / 13）紧贴被测代码任务摆放，遵循"每完成一片实现立即可验证"。
- 标 `*` 的子任务为可选测试任务，MVP 阶段允许跳过；但任务 8 的 P0 / P1+P2 / P3 三个性质强烈建议保留，因为它们是发版正确性的灵魂条款。
- 任务 1–13 是必做；任务 14 是收尾打磨，可在主线落地后补完。
- 每个任务通过 `_Requirements` 引用具体子条款保证 traceability；PBT 任务额外通过 `_Properties` 引用 design 中的 P 编号。
- 单 worker + SQLite partial unique index 是并发安全的最后一道兜底；多 worker 升级路径在 design "并发安全证明" 一节有讨论，不在本 spec 范围。
