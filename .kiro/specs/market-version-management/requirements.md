# Requirements Document — Market 插件版本管理

## Introduction

本特性的**第一目标是打通 Plugin Market 的下载链路**，**版本管理（channel / is_latest / yank）是同步要做的能力**，但范围严格克制。

### 当前下载链路是断的（三个具体断点）

1. **审核通过不创建 Version**：`app/services/submission_review_service.py` 的 `_ensure_approved_plugin` 在审核通过时只插入一条 `Plugin` 行，不写入任何 `Version`，因此插件即便已 `APPROVED`，`versions` 表里也没有对应记录。
2. **`Plugin.download_url` 从来没人写**：表上有这一列，但代码路径中找不到任何写入处；前端表单亦不收集该字段。
3. **客户端 fallback 到 `repo_url`**：`N.E.K.O/frontend/plugin-manager/src/api/market.ts` 的 `normalizeMarketPlugin` 对 `download_url` 取值 `raw.download_url ?? raw.repo_url`，因此当后端没有 `download_url` 时，客户端会拿到 GitHub 仓库主页地址（不是 `.neko-plugin` 包），下载必然失败。

本特性首先把这条链路修通：作者通过表单提供 GitHub release URL → 后端拉取 release asset → 后端字节级算 sha256 → 落库为 Version 行 → 客户端 `latest` 接口拿到的 `package_url` + `package_sha256` 一定指向真实可下载的 `.neko-plugin` / `.neko-bundle` 文件。

### 这是重构，不是增量改进

本特性会做以下不留向后兼容的变更：

- 删除 `plugins.version` 列、删除 `plugins.download_url` 列（数据迁移到 `versions` 表）。
- 删除旧的 `POST /api/v1/plugins/{id}/versions`（手填 sha256 的版本创建接口）。
- 删除旧的 `DELETE /api/v1/plugins/{id}/versions/{version_id}`（用 yank 替代）。
- 重写 `GET /api/v1/plugins/{id}/versions/latest`：仅返回 `is_latest=true AND yanked_at IS NULL` 的版本，找不到返回 404，**不再 fallback**。
- 重写 `Plugin` 列表 / 详情接口的返回 JSON：移除顶层的 `version` 与 `download_url`，改为嵌套 `latest_version: { version, channel, package_url, package_sha256, payload_hash, created_at } | null`。

### N.E.K.O 客户端不在本 spec 范围内

- 本 spec 只改 **Market 后端 + Market 前端**（`app/` 与 `NEKO_Plugins_Market/`）。
- N.E.K.O 客户端代码（`N.E.K.O/frontend/plugin-manager/src/api/market.ts` 等）**本 spec 不动**，留给后续客户端 spec 适配。
- 但有两处 breaking change 必须告知客户端 spec（见文末"待客户端 spec 适配的 breaking change"）。

### 范围划界

**本 spec 必做（MVP）：**

- 下载链路打通（作者自助发版 → 后端冻结 hash → 客户端可下载真实包文件）。
- channel：仅 `stable` / `beta` 两种。
- `is_latest` 显式标记：每个 (plugin, channel) 至多一条 `is_latest=true AND yanked_at IS NULL`。
- yank 单向撤回（不做 unyank）：作者或 admin 都能撤回；yank latest 时自动晋级 + 给作者发 notification。
- Market 前端：插件详情页版本 tab、`MyPlugins` 发版按钮、yank 按钮（作者和 admin 共用，admin 多一个"管理员撤回"权限）。

**本 spec 明确不做：**

- 包级 ECDSA 签名（下一个 spec）。
- `nightly` / `lts` channel。
- channel 切换 / 版本元数据 PATCH（要"晋升"就重新发版）。
- unyank。
- `min_app_version` / `max_app_version` 强校验。
- 独立的 `release_publish_attempt` 日志表（直接打 logger 即可）。
- 独立的 admin 版本管理页（yank 按钮放在插件详情页同一处，作者和 admin 共用 UI，admin 看到多一个"管理员撤回"按钮）。
- 依赖图、托管型存储。

## Glossary

- **Market_Backend**：FastAPI 后端服务（`Plugin Market (Backend + Frontend)/app/`）。
- **Market_Frontend**：React + TypeScript 前端（`Plugin Market (Backend + Frontend)/NEKO_Plugins_Market/`）。
- **NEKO_Client**：用户本地的 N.E.K.O 桌面客户端（不在本 spec 范围内）。
- **Plugin**：`plugins` 表中的一条记录，代表一个插件。
- **Version**：`versions` 表中的一条记录，代表 Plugin 的一次发布。
- **Channel**：版本所属的发布渠道，本 spec 仅枚举 `stable` / `beta`。
- **Release**：GitHub Release，由作者在仓库上发布，包含一个或多个 release asset。
- **Release_Asset**：GitHub Release 上的可下载文件，期望后缀为 `.neko-plugin` 或 `.neko-bundle`。
- **package_url**：Release_Asset 的 `browser_download_url`，可被 HTTP GET 拿到字节流。
- **package_sha256**：Release_Asset 整个文件字节的 SHA-256 十六进制小写哈希（64 字符）。
- **payload_hash**：Release_Asset 内 `metadata.toml` 中 `[payload].hash` 的值，对 payload 目录规范化内容计算的 SHA-256；asset 内无该文件或字段则为 `NULL`。
- **is_latest**：Version 表上的布尔字段，标记该版本是否为所属 (Plugin, Channel) 的当前最新版。
- **yanked**：一个 Version 被作者或 admin 撤回，新用户不再分发。`yanked_at` 非空即视为已 yank。本 spec 不提供 unyank。
- **Frozen_Fact**：由后端在发布时刻计算并写入数据库、之后不可修改的字段，包括 `package_url` / `package_sha256` / `payload_hash` / `release_url` / `release_tag` / `source_commit` / `version` / `channel`。
- **Release_Fetcher**：本特性新增的服务模块，封装"调 GitHub API 拿 release → 找 asset → 流式下载 → 算 sha256 → 解析 metadata.toml"。
- **Author**：拥有 Plugin（`plugin.author_id == user.id`）的用户。
- **Admin**：`current_user.is_admin == True` 或拥有 `plugin_management` 权限的用户。

---

## Requirements

### Requirement 0：下载链路端到端完整性

**User Story:** As a NEKO_Client 用户, I want 通过 Market `latest` 接口拿到的 `package_url` 一定能下载到真实 `.neko-plugin` / `.neko-bundle` 文件且 sha256 与响应一致, so that 客户端无需再 fallback 到 `repo_url` 也能装上插件。

#### Acceptance Criteria

1. THE Market_Backend SHALL 保证：对任何 `GET /api/v1/plugins/{id}/versions/latest?channel=stable` 返回 HTTP 200 的响应，响应体中 `package_url` 字段是合法 HTTP/HTTPS URL，对该 URL 发起 HTTP GET 能在 5xx 之外的状态下返回 HTTP 200 + 字节流。
2. THE Market_Backend SHALL 保证：对任何成功返回的 `latest` 响应，对 `package_url` 下载到的字节流计算 SHA-256（小写十六进制）必定等于响应体中 `package_sha256` 字段。
3. THE Market_Backend SHALL 保证：对任何成功返回的 `latest` 响应，`package_url` 下载到的字节流前 4 字节为 ZIP magic number `50 4B 03 04`。
4. THE Market_Backend SHALL 保证：对任何成功返回的 `latest` 响应，`package_sha256` 是 64 字符 lowercase hex string，且 `package_url` 与 `package_sha256` 不为空字符串、不为 `NULL`。
5. IF 一个 plugin 在指定 channel 下没有满足 `is_latest=true AND yanked_at IS NULL` 的 Version，THEN THE Market_Backend SHALL 返回 HTTP 404，**不得 fallback 到 `repo_url` 或任何其他字段**。

> **Property P0** 在 design 阶段映射到具体测试：通过 mock GitHub API 返回固定字节，端到端验证"发版后 latest 接口的 package_sha256 与 package_url 字节流的 sha256 严格一致"。

### Requirement 1：Version 表结构扩展

**User Story:** As a Market_Backend 维护者, I want `versions` 表拥有 `channel` / `is_latest` / `yanked_*` / `published_by` 等字段并附带正确索引, so that 后续业务逻辑有可落地的数据模型且不变量能由数据库强约束。

#### Acceptance Criteria

1. THE Market_Backend SHALL 在 `versions` 表上新增 `channel` 字段，`VARCHAR(16) NOT NULL DEFAULT 'stable'`，附 CHECK 约束 `channel IN ('stable', 'beta')`。
2. THE Market_Backend SHALL 在 `versions` 表上新增 `is_latest` 字段，`BOOLEAN NOT NULL DEFAULT FALSE`。
3. THE Market_Backend SHALL 在 `versions` 表上新增 `yanked_at` 字段，`DATETIME NULL DEFAULT NULL`。
4. THE Market_Backend SHALL 在 `versions` 表上新增 `yanked_reason` 字段，`TEXT NULL`。
5. THE Market_Backend SHALL 在 `versions` 表上新增 `yanked_by` 字段，`INTEGER NULL`，外键指向 `users.id`，删除时 `ON DELETE SET NULL`。
6. THE Market_Backend SHALL 在 `versions` 表上新增 `published_by` 字段，`INTEGER NULL`，外键指向 `users.id`，删除时 `ON DELETE SET NULL`，记录发版操作者。
7. THE Market_Backend SHALL 在 `versions` 表上为 `(plugin_id, version)` 建立唯一索引。
8. THE Market_Backend SHALL 在 `versions` 表上为 `(plugin_id, channel)` 建立**部分唯一索引**，仅在 `is_latest = TRUE` 时生效（SQLite partial index 写法），用于强制"每个 (plugin, channel) 至多一条 is_latest"。
9. THE Market_Backend SHALL 通过 alembic 迁移脚本变更上述结构；迁移可前进，downgrade 不强制完美，可在失败时由维护者手动处理。

### Requirement 2：数据迁移与字段下线

**User Story:** As a Market_Backend 维护者, I want 在迁移脚本中将存量数据搬运到新模型并删除 `plugins.version` / `plugins.download_url`, so that 上线后没有"两处都写当前版本"的双写麻烦。

#### Acceptance Criteria

1. WHEN alembic `upgrade()` 执行，THE Market_Backend SHALL 将所有现存 `versions` 行的 `channel` 设置为 `'stable'`。
2. WHEN alembic `upgrade()` 执行，THE Market_Backend SHALL 对每个 `plugin_id`，按 `created_at` 降序选取该 plugin 的第一条 version 置 `is_latest = TRUE`，其余 `is_latest = FALSE`。
3. IF 一个 plugin 在 `versions` 表中没有任何记录但在 `plugins` 表中存在 `download_url` 非空值，THEN THE Market_Backend SHALL 在迁移中为该 plugin 补一条"legacy" Version 行：`version = plugin.version`、`channel = 'stable'`、`is_latest = TRUE`、`package_url = plugin.download_url`、`download_url = plugin.download_url`、`package_sha256 = ''`（空字符串占位）、`verification_status = 'legacy_unverified'`、`published_by = plugin.author_id`、`created_at = plugin.published_at OR plugin.created_at`。这是为了避免现有部署数据丢失。
4. IF 一个 plugin 在 `versions` 表与 `plugins.download_url` 都没有可用数据（`download_url` 为 NULL 或空），THEN THE Market_Backend SHALL 不为该 plugin 创建占位 Version 行，保留空版本列表。
5. WHEN 完成上述数据搬运，THE Market_Backend SHALL 在同一 alembic upgrade 中删除 `plugins.version` 列、删除 `plugins.download_url` 列。
6. THE Market_Backend SHALL 在 `Plugin` ORM 模型与 `PluginBase` / `PluginUpdate` / `Plugin` 等 Pydantic schema 中同步删除 `version` 与 `download_url` 字段。

### Requirement 3：作者自助发版（从 GitHub Release）

**User Story:** As an Author, I want 通过提供 GitHub release URL 让 Market_Backend 自动拉取资产并冻结指纹, so that 我不需要手动算 sha256，且 Market 不需要每次发版都走管理员审核。

#### Acceptance Criteria

1. THE Market_Backend SHALL 提供 `POST /api/v1/plugins/{plugin_id}/versions/publish-from-release`，请求体含 `release_url`（必填）、`channel`（可选，默认 `'stable'`，仅允许 `'stable'` 或 `'beta'`）、`changelog`（可选，文本）。
2. WHEN 请求 `current_user.id == plugin.author_id` 或 `current_user` 是 Admin，THE Market_Backend SHALL 接受请求；否则返回 HTTP 403，错误码 `forbidden`。
3. THE Market_Backend SHALL 校验：`release_url` 解析出的 GitHub `owner/repo` 必须等于 `plugin.repo_url` 解析出的 `owner/repo`（大小写不敏感比较）；不一致时返回 HTTP 400，错误码 `release_repo_mismatch`，且不写入任何记录。
4. IF 请求 `channel` 不是 `'stable'` 或 `'beta'`，THEN THE Market_Backend SHALL 返回 HTTP 400，错误码 `invalid_channel`。
5. WHEN 校验通过，THE Release_Fetcher SHALL 调用 GitHub API 获取 release 元数据，遍历 `assets` 数组，选取**第一个**后缀为 `.neko-plugin` 或 `.neko-bundle` 的 asset 作为 Release_Asset。
6. IF release 中找不到符合后缀的 asset，THEN THE Market_Backend SHALL 返回 HTTP 400，错误码 `release_asset_not_found`，不写入任何记录。
7. WHEN 找到 Release_Asset，THE Release_Fetcher SHALL 流式下载该 asset 的全部字节，下载上限为 200 MiB；超过则返回 HTTP 413，错误码 `release_asset_too_large`，不写入任何记录。
8. WHEN 下载完成，THE Release_Fetcher SHALL 计算下载字节的 SHA-256 小写十六进制作为 `package_sha256`；作者不能在请求体中提供 `package_sha256`，请求体即便包含也忽略。
9. WHEN 下载完成，THE Release_Fetcher SHALL 解析 asset（按 ZIP 解压）内 `metadata.toml` 中 `[payload].hash` 字段作为 `payload_hash` 写入；asset 内无该文件、无该字段、或字段格式非法时，`payload_hash` 写为 `NULL`（不视为错误）。
10. THE Market_Backend SHALL 从 release 元数据中提取 `tag_name` 作为 `release_tag`、release 页 URL 作为 `release_url`、asset 的 `browser_download_url` 作为 `package_url` 并同时写入 `download_url`、`target_commitish` 解析后的 commit sha 作为 `source_commit`、`plugin.repo_url` 写入 `source_repo_url`。
11. THE Market_Backend SHALL 使用 release `tag_name` 去除前导 `v` 或 `V` 后作为新 Version 的 `version` 字段（例如 `v1.2.0` → `1.2.0`、`V0.3.1` → `0.3.1`）。
12. IF `(plugin_id, version)` 已存在于 `versions` 表，THEN THE Market_Backend SHALL 返回 HTTP 409，错误码 `version_already_exists`，不写入任何记录。
13. WHEN 上述步骤全部成功，THE Market_Backend SHALL 在单个数据库事务中：
    - 将该 plugin 上 `channel == 请求 channel` 且 `is_latest == TRUE` 的所有现存 Version 置为 `is_latest = FALSE`；
    - 插入新 Version 行，`is_latest = TRUE`、`channel = 请求 channel`、`yanked_at = NULL`、`published_by = current_user.id`、`verification_status = 'passed'`。
14. IF 上述任一步骤失败（GitHub API 网络错误、超时、5xx、429、下载中断、ZIP 解析失败、数据库异常），THEN THE Market_Backend SHALL 回滚事务并返回 HTTP 502 错误码 `release_publish_failed`，不留任何半成品 Version 行。
15. THE Market_Backend SHALL 在每次 `publish-from-release` 调用（无论成败）通过 logger 输出结构化日志，字段包括 `plugin_id` / `actor_id` / `release_url` / `channel` / `outcome`（`success` / `failed`）/ `error_kind` / `error_message`。
16. THE Market_Backend SHALL 在响应体中返回新建 Version 的完整字段（含 `id` / `version` / `channel` / `is_latest` / `package_url` / `package_sha256` / `payload_hash` / `release_url` / `release_tag` / `source_commit` / `created_at`）。

### Requirement 4：撤回版本（yank，单向）

**User Story:** As an Author or Admin, I want 撤回某个版本并在它是当前 latest 时自动晋级, so that 当版本有严重问题时新用户不会再装上而当前 channel 仍有可用 latest。

#### Acceptance Criteria

1. THE Market_Backend SHALL 提供 `POST /api/v1/plugins/{plugin_id}/versions/{version_id}/yank`，请求体含 `reason`，`string` 类型，长度 1-500 字符，必填。
2. WHEN 请求者是 plugin 作者或 Admin，THE Market_Backend SHALL 接受请求；否则返回 HTTP 403，错误码 `forbidden`。
3. IF 请求版本 `yanked_at IS NOT NULL`，THEN THE Market_Backend SHALL 返回 HTTP 409，错误码 `version_already_yanked`。
4. WHEN 请求被接受，THE Market_Backend SHALL 在单个事务中：
    - 设置 `yanked_at = utc_now()`、`yanked_reason = reason`、`yanked_by = current_user.id`；
    - 如果该版本 `is_latest == TRUE`，则将其 `is_latest` 置为 `FALSE`，并在该 (plugin_id, channel) 内选取 `yanked_at IS NULL` 且 `created_at` 最大的版本置为 `is_latest = TRUE`；若不存在这样的候选则该 channel 暂无 latest。
5. WHEN yank 操作导致 latest 发生变化（无论是切换到次新版还是变为"该 channel 暂无 latest"），THE Market_Backend SHALL 通过现有 notification system 给 `plugin.author_id` 发一条通知，标题包含被 yank 的版本号、channel、操作者身份（作者本人或 admin）。
6. THE Market_Backend SHALL 不提供 unyank 接口；本 spec 内 yank 是单向操作。
7. THE Market_Backend SHALL 在 yank 操作完成后通过现有审计日志机制（`app.routers.admin.logs`）记录一条 audit log，含 `actor_id` / `plugin_id` / `version_id` / `action='yank'` / `reason` / `at`。

### Requirement 5：版本列表与最新版查询 API

**User Story:** As a Market_Frontend 或 NEKO_Client 开发者, I want 查询 versions 时支持按 channel 与 yank 状态过滤、查 latest 时严格按 is_latest 标记返回, so that 不同消费方拿到自己想要的子集且永远不会拿到 yanked 版本作为 latest。

#### Acceptance Criteria

1. THE Market_Backend SHALL 在 `GET /api/v1/plugins/{plugin_id}/versions` 上支持查询参数 `channel`（可选，取值 `'stable'` 或 `'beta'`），未传时返回所有 channel。
2. THE Market_Backend SHALL 在 `GET /api/v1/plugins/{plugin_id}/versions` 上支持查询参数 `include_yanked`（可选，`true` / `false`，默认 `false`）。
3. WHEN `include_yanked` 为 `false` 或未传，THE Market_Backend SHALL 仅返回 `yanked_at IS NULL` 的版本。
4. THE Market_Backend SHALL 按 `created_at` 降序返回版本列表。
5. THE Market_Backend SHALL 在 `GET /api/v1/plugins/{plugin_id}/versions/latest` 上支持查询参数 `channel`（可选，默认 `'stable'`）。
6. WHEN 查询 latest 时，THE Market_Backend SHALL 仅返回该 (plugin_id, channel) 中 `is_latest = TRUE AND yanked_at IS NULL` 的版本，且至多一条。
7. IF latest 查询找不到符合条件的版本（包括"存在 yanked 但没有 is_latest"的情况），THEN THE Market_Backend SHALL 返回 HTTP 404，错误码 `latest_version_not_found`。
8. THE Market_Backend SHALL 保证 versions 列表项与 latest 响应的 JSON 字段集相同，至少包含 `id` / `plugin_id` / `version` / `channel` / `is_latest` / `yanked_at` / `yanked_reason` / `changelog` / `package_url` / `download_url` / `package_sha256` / `payload_hash` / `release_url` / `release_tag` / `source_commit` / `source_repo_url` / `published_by` / `verification_status` / `created_at`。

### Requirement 6：Plugin 列表 / 详情 JSON 结构重构

**User Story:** As a Market_Frontend 或 NEKO_Client 开发者, I want plugin 对象不再在顶层冗余 `version` 与 `download_url`、改为嵌套 `latest_version` 子对象, so that "哪个包是当前版"的语义统一从 versions 表读，避免双写漂移。

#### Acceptance Criteria

1. THE Market_Backend SHALL 在 `GET /api/v1/plugins`、`GET /api/v1/plugins/{id}`、以及 `Plugin.to_frontend_dict` 等所有暴露 plugin 对象的接口的响应中，**移除**顶层的 `version` 字段、**移除**顶层的 `download_url` 字段。
2. THE Market_Backend SHALL 在上述每个 plugin 对象上**新增**字段 `latest_version`，类型为 `object | null`，结构如下：
    - `version: string`（如 `"1.2.0"`）
    - `channel: 'stable' | 'beta'`
    - `package_url: string`
    - `package_sha256: string`（64 字符小写 hex）
    - `payload_hash: string | null`
    - `created_at: string`（ISO8601）
3. WHEN 一个 plugin 在 `stable` channel 上存在 `is_latest = TRUE AND yanked_at IS NULL` 的 Version，THE Market_Backend SHALL 把该 Version 投影为 `latest_version` 子对象。
4. WHEN 一个 plugin 在 `stable` channel 上**没有**满足上述条件的 Version（即便 `beta` 上有），THE Market_Backend SHALL 把 `latest_version` 设置为 `null`。
5. THE Market_Backend SHALL 不再读取 `Plugin.version` 或 `Plugin.download_url`（这两列已在 Requirement 2 中删除），所有"当前版"语义都从 versions 表 join 派生。

### Requirement 7：Market 前端 — 插件详情页版本管理 + 作者发版入口

**User Story:** As an Author or Market 访客, I want 在插件详情页看到版本列表并能（作者或 admin）从同一处发版 / yank, so that 我不需要打开 Postman 也能完成版本管理且无需额外的管理员后台页面。

#### Acceptance Criteria

1. THE Market_Frontend SHALL 在 `pages/PluginDetail.tsx` 增加"版本"标签页，调用 `GET /api/v1/plugins/{plugin_id}/versions?include_yanked=true` 获取列表。
2. THE Market_Frontend SHALL 为每条 version 渲染：版本号、channel 徽章（stable=绿色 / beta=橙色）、`package_sha256` 前 12 位（点击展开完整哈希）、`created_at` 本地时间、`changelog`（markdown 渲染）、latest 标记、yanked 标记。
3. WHEN 一条 version `yanked_at != NULL`，THE Market_Frontend SHALL 把该行视觉置为灰阶并附"已撤回"徽章，hover 显示 `yanked_reason`。
4. WHEN 一条 version `is_latest == TRUE` 且 `yanked_at IS NULL`，THE Market_Frontend SHALL 显示"最新"徽章。
5. THE Market_Frontend SHALL 提供 channel 过滤器（按钮组：全部 / stable / beta），默认"全部"；显示"包含已撤回版本"开关，默认开启。
6. WHEN 当前登录用户是该 plugin 的作者或 Admin，THE Market_Frontend SHALL 在版本 tab 顶部显示"发布新版本"按钮、并在每条非 yanked 的版本行显示"撤回"按钮。
7. WHEN 当前登录用户是 Admin 但不是作者，THE Market_Frontend SHALL 在每条非 yanked 版本行额外显示"管理员撤回"按钮（与作者撤回共用同一接口，仅按钮文案区分操作者身份）。
8. WHEN 用户点击"发布新版本"，THE Market_Frontend SHALL 弹出表单，字段含：
    - `release_url`（必填，URL 格式校验）；
    - `channel`（下拉，可选 `stable` / `beta`，**默认 stable**，作者可改 beta）；
    - `changelog`（多行文本，可空）。
9. WHEN 用户提交"发布新版本"表单，THE Market_Frontend SHALL 调用 `POST /api/v1/plugins/{plugin_id}/versions/publish-from-release`，展示进度态（pending / success / error），并在响应错误码为 `release_repo_mismatch` / `release_asset_not_found` / `release_asset_too_large` / `version_already_exists` / `release_publish_failed` / `invalid_channel` 时显示对应中文文案。
10. WHEN 用户点击"撤回"或"管理员撤回"，THE Market_Frontend SHALL 弹出对话框要求填写撤回原因（1-500 字），调用 `POST /api/v1/plugins/{plugin_id}/versions/{version_id}/yank`；成功后刷新版本列表（不依赖乐观更新）。
11. THE Market_Frontend SHALL 在 `pages/MyPlugins.tsx` 中为每个属于当前用户的已发布插件提供"发布新版本"按钮，点击后跳转到对应 plugin 详情页的版本 tab 并自动打开发版表单。
12. WHEN 一个 plugin 在 versions 表中没有任何记录，THE Market_Frontend SHALL 在 `MyPlugins.tsx` 与详情页版本 tab 显示"该插件尚未发布任何版本"提示，引导作者发第一个版本。

### Requirement 8：删除旧的版本 CRUD 路由

**User Story:** As a Market_Backend 维护者, I want 删除旧的"手填 sha256"版本创建接口与 DELETE 接口, so that 所有写入路径都满足 hash 由后端冻结的新约束、所有撤回路径都走 yank。

#### Acceptance Criteria

1. THE Market_Backend SHALL 删除 `POST /api/v1/plugins/{plugin_id}/versions` 路由及其相关 schema（`VersionCreate`）；任何调用该路由的请求 SHALL 返回 HTTP 404。
2. THE Market_Backend SHALL 删除 `DELETE /api/v1/plugins/{plugin_id}/versions/{version_id}` 路由；撤回统一走 yank 接口。
3. THE Market_Backend SHALL 不再暴露 `PATCH /api/v1/plugins/{plugin_id}/versions/{version_id}` 接口（本 spec 不提供版本元数据修改能力）；任何调用 SHALL 返回 HTTP 404。

### Requirement 9：错误码与可观察性

**User Story:** As a Market_Backend 运维者, I want 发版与 yank 相关错误集中可查、错误码稳定且文档化, so that 前端能精确映射文案、运维能快速诊断根因。

#### Acceptance Criteria

1. THE Market_Backend SHALL 在所有错误响应 JSON 中统一返回 `{"detail": "...", "code": "<error_code>"}` 结构。
2. THE Market_Backend SHALL 定义并使用以下错误码（不增不减）：`forbidden` / `release_repo_mismatch` / `release_asset_not_found` / `release_asset_too_large` / `release_publish_failed` / `version_already_exists` / `version_already_yanked` / `latest_version_not_found` / `invalid_channel`。
3. WHEN 拉取 GitHub release 时发生网络错误（连接超时、5xx、429），THE Release_Fetcher SHALL 在抛出异常前重试 1 次（指数退避 0.5s），仍失败则按 Requirement 3.14 处理。
4. THE Market_Backend SHALL 通过现有 logger（`app.core.logging` 或等价模块）输出 `publish-from-release` 与 `yank` 操作的结构化日志，不引入额外的 `release_publish_attempt` 表。

---

## Property-Based Testing — Correctness Properties

下列性质应在 design 阶段映射到 Hypothesis（后端）测试用例，集中存放在 `tests/properties/test_version_management.py`。

### P0：下载链路完整性（灵魂条款）

**输入空间**：任意通过 `publish-from-release` 成功创建的 Version 行（mock GitHub API 返回任意合法字节流，含空文件、1 字节、含 NUL、含 UTF-8 BOM、含 ZIP magic 但 payload 任意、最多 200 MiB-1 字节）。

**性质**：

1. `Version.package_sha256 == sha256(GET Version.package_url).hexdigest().lower()`
2. `Version.package_sha256` 是合法的 64 字符 lowercase hex string，不为空字符串。

**实现提示**：在 CI 测试中通过 mock GitHub API（`respx` / `responses`）返回 Hypothesis 生成的字节，端到端验证写入 DB 的 `package_sha256` 与字节的 SHA-256 严格一致。

**为什么是 PBT**：流式下载的 chunk 边界、超大文件、HTTP gzip 解压（不应启用）都可能让算 hash 偏离真实字节。

### P1：(plugin, channel) is_latest 唯一性

**输入空间**：任意 `publish-from-release` + `yank` 操作序列（含失败回滚、并发提交）。

**性质**：操作序列结束后，对所有 (plugin_id, channel) 二元组，满足 `is_latest = TRUE AND yanked_at IS NULL` 的 versions 行数恰好 ≤ 1。

**为什么是 PBT**：状态机式探索能找到事务竞态、错误回滚后状态错乱等 corner case；2-3 个例子无法覆盖。

### P2：yank latest 后自动晋级一致性

**输入空间**：任意发版顺序 + 任意子集被 yank 的序列。

**性质**：任意时刻，对每个 (plugin_id, channel)，若存在 `yanked_at IS NULL` 的版本，则 latest 必然指向其中 `created_at` 最大的那一条；若不存在，则该 (plugin_id, channel) 没有 latest（即 `is_latest = TRUE` 的行数为 0）。

**为什么是 PBT**：yank 与 publish 交叉执行时，latest 晋级逻辑必须始终满足"指向当前 channel 最新非 yanked 版本"。

### P3：(plugin_id, version) 唯一约束在并发下成立

**输入空间**：同一 (plugin_id, version) 的并发 `publish-from-release` 请求（用 `asyncio.gather` 模拟）。

**性质**：N 个并发同 release_url 的 publish 请求中，恰好 1 个返回 HTTP 200/201 写入新 Version，其余返回 HTTP 409 `version_already_exists`；事后 `versions` 表中该 (plugin_id, version) 行数恰好为 1。

**为什么是 PBT**：探索"作者狂点提交按钮"、"两个浏览器 tab 同时提交"等并发情况，幂等性必须在并发下也成立。

---

## 待客户端 spec 适配的 breaking change

以下变更落地后会破坏现有 NEKO_Client（`N.E.K.O/frontend/plugin-manager/src/api/market.ts`），需在客户端 spec 中适配，**本 spec 不动客户端代码**：

1. **plugin 对象 JSON 结构变更**：`GET /api/v1/plugins` 与 `GET /api/v1/plugins/{id}` 响应中，plugin 对象顶层不再有 `version` 与 `download_url` 字段；改为读取 `plugin.latest_version.version` / `plugin.latest_version.package_url` / `plugin.latest_version.package_sha256`。客户端 `MarketPluginRaw` interface 与 `normalizeMarketPlugin` 函数需同步更新；同时 `download_url ?? repo_url` 的 fallback 逻辑必须删除。
2. **`GET /api/v1/plugins/{id}/versions/latest` 行为变更**：本 spec 后该接口在没有 `is_latest = TRUE AND yanked_at IS NULL` 的版本时一律返回 404，**不再 fallback** 到 `repo_url` 或任何其他字段；客户端遇到 404 应展示"该插件暂无可下载版本"的状态，而不是尝试下载 `repo_url`。

---

## 后续阶段

需求文档到此结束。下一阶段（design）将：

1. 把 Requirement 1 的字段加成翻译为具体的 SQLAlchemy 模型 diff 与 alembic 迁移脚本（含 SQLite partial index 的具体写法）；
2. 把 Requirement 3 的发版流程画成时序图（Author → Market_Frontend → Market_Backend → Release_Fetcher → GitHub API → DB）；
3. 把 P0–P3 的 PBT 性质映射到具体 Hypothesis 测试模块，并设计 mock GitHub API 的策略（建议用 `respx`）；
4. 给 Market 前端 `PluginDetail.tsx` 版本 tab 与发版表单画线框；
5. 详细化错误码到中文文案的映射表。

请 review Requirements 0–9 与 P0–P3。确认无误后告知进入 design 阶段，或回复 `Skip to Implementation Plan` 让我连续生成 design 与 tasks。
