# Requirements Document — Market 插件版本管理

## Introduction

本特性为 Plugin Market（后端 FastAPI + 前端 `NEKO_Plugins_Market`）建立完整的"版本管理"概念，让一个插件可以拥有多条版本记录、可分渠道（channel）发布、可标记 latest、可撤回（yank），并把 GitHub Release 资产的指纹（`package_sha256`、`payload_hash`）在发布时由后端**重算并冻结**到 `Version` 表，而不是信任作者填写的值。

边界明确：

- 仅涉及 Market 侧（后端 + Market 前端）。
- N.E.K.O 客户端代码不在本特性范围内，但返回结构必须与客户端 `frontend/plugin-manager/src/api/market.ts` 已有期望兼容（`package_url` / `package_sha256` / `payload_hash` / `download_url` 必须继续返回）。
- 不做包级 ECDSA 签名（下一个 spec 处理），仅做"hash 冻结到表"。
- 不做依赖图、不做托管型存储、不做 LTS 超长支持期语义。

## Glossary

- **Market_Backend**: FastAPI 后端服务（端口 8000，路径 `app/`）。
- **Market_Frontend**: React + TypeScript 前端（`NEKO_Plugins_Market/`，端口 5173）。
- **NEKO_Client**: 用户本地的 N.E.K.O 桌面客户端（不在本特性范围内）。
- **Plugin**: `plugins` 表中的一条记录，代表一个插件。
- **Version**: `versions` 表中的一条记录，代表 Plugin 的一次发布。
- **Channel**: 版本所属的发布渠道，枚举值为 `stable` / `beta` / `nightly` / `lts`。
- **Release**: GitHub Release，由作者在仓库上发布，包含一个或多个 release asset。
- **Release_Asset**: GitHub Release 上的可下载文件，期望后缀为 `.neko-plugin` 或 `.neko-bundle`。
- **package_sha256**: Release_Asset 整个文件字节的 SHA-256 十六进制小写哈希。
- **payload_hash**: 对 Release_Asset 内 `payload/` 目录规范化后内容计算的 SHA-256（与 `neko-plugin-cli` 的 `metadata.toml [payload].hash` 一致）。
- **is_latest**: Version 表上的布尔字段，标记该版本是否为所属 (Plugin, Channel) 的当前最新版。
- **yanked**: 一个 Version 被作者或管理员撤回，不再分发给新用户，但已下载的副本不受影响。`yanked_at` 非空即视为已 yank。
- **Publish_From_Release**: 一次发布操作：作者提供 GitHub release URL，Market_Backend 拉取资产 → 重算指纹 → 落库为新 Version。
- **Frozen_Fact**: 由后端在发布时刻计算并写入数据库、之后视为不可变事实的字段（`package_url` / `package_sha256` / `payload_hash` / `source_commit` / `release_tag` / `release_url`）。
- **Channel_Subscription**: 客户端选择性接收哪些 channel 版本的偏好（默认仅 `stable`）。
- **Version_Service**: `app/services/version_service.py`，封装版本相关数据库操作。
- **Release_Fetcher**: 本特性新增的服务，封装"拉 GitHub Release 资产 + 算 hash + 解析 metadata.toml"的逻辑。
- **Author**: 拥有 Plugin（`plugin.author_id == user.id`）的用户。
- **Admin**: 拥有 `plugin_management` 权限的管理员用户。

---

## Key Design Decisions（候选方案 + 推荐）

以下决策点会直接影响 acceptance criteria 的写法，先列出候选与推荐，再让 acceptance criteria 落到对应方案上。如对推荐方案有不同意见，请在 review 阶段提出，我会同步修改下方的 Requirements。

### D1. 作者发版的入口 / 是否每次发版都要走审核

| 方案 | 说明 | 取舍 |
|---|---|---|
| A. 每次发版都走审核工作台 | 复用 `plugin_submissions` 流程，每个版本生成一个 submission | 审核压力大，作者迭代慢；但代码安全性最高 |
| B. **首次提交插件需审核，后续版本作者自助发布**（推荐） | 已通过 `PluginStatus.APPROVED` 的插件，作者可直接调 `publish-from-release`，但作者必须证明 release 来自原仓库（`release_url` 的 owner/repo 必须等于 `plugin.repo_url` 的 owner/repo） | 在安全和迭代速度间平衡；和当前 `plugin_submissions` 解耦 |
| C. 管理员代发 | 作者只能提交 release_url，由管理员触发发布 | 太重，现实中没人这么做 |

**推荐 B**：插件本体已审过，后续版本只在仓库归属一致的前提下自助发布；管理员可随时 yank 异常版本。后续若发现问题再升级到方案 A 或加 AI 二次审核（不在本 spec 内）。

### D2. `is_latest` 是否按 channel 分

| 方案 | 说明 |
|---|---|
| A. 全局只有一个 latest | 所有 channel 共享一个 latest 标记 |
| B. **每个 channel 各有一个 latest**（推荐） | (plugin_id, channel) 唯一约束 is_latest=true |

**推荐 B**：客户端对 stable / beta / nightly 各自有"最新版"的概念，混在一起会让"订阅 beta 通道"语义模糊。前端展示也按 channel 分组更直观。

### D3. fetch release 失败的策略

| 方案 | 说明 |
|---|---|
| A. 直接拒绝（事务 rollback） | 没有副作用，作者重试即可 |
| B. **直接拒绝 + 记录失败日志**（推荐） | 拒绝且不写 Version 表，但写一条 `release_publish_attempt` 日志（含错误原因），方便管理员排查 |
| C. 留 pending，后台重试 | 复杂度高，引入异步任务调度 |

**推荐 B**：原子性最好，作者立刻看到错误，无需等待。失败日志单表记录 `release_url / error_kind / error_message / attempted_at / actor_id`，仅供管理员查询。

### D4. channel 是否可发布后切换

| 方案 | 说明 |
|---|---|
| A. 不可切换，只能发新版本 | 简单但作者不便 |
| B. **允许 PATCH channel**（推荐） | 通过 `PATCH /api/v1/plugins/{id}/versions/{version_id}`，且切换后必须重算 is_latest |
| C. 仅允许 beta → stable 单向晋升 | 多此一举 |

**推荐 B**：作者经常会先发 beta 再"晋升"到 stable。切换时 Market_Backend 必须事务化重算 is_latest，避免出现两个 stable latest。

### D5. version 字符串约束

| 方案 | 说明 |
|---|---|
| A. 强制 semver（PEP 440 子集） | 排序靠谱，但拒绝旧仓库 `v0.1` 等不规范写法 |
| B. **仅要求 (plugin_id, version) 唯一 + 长度限制**（推荐） | 排序时用"是否符合 semver → semver 排序，否则按 created_at 排序"两段式 |
| C. 完全自由 | 太散，排序不稳定 |

**推荐 B**：保持向后兼容，但内部维护一个 `is_semver_compliant` 推导属性（不入库，仅在比较时用）。`is_latest` 不依赖 version 字符串排序，只依赖发布时间事务化切换。

### D6. yanked 版本对客户端的可见性

| 方案 | 说明 |
|---|---|
| A. 完全过滤 | 客户端调 `GET /versions` 默认看不到 yanked |
| B. **默认过滤，但 `?include_yanked=true` 可显示**（推荐） | 客户端可选地显示 yanked 状态，UI 标灰 |
| C. 总是返回但加标记 | 可能误导新用户安装 |

**推荐 B**：默认 `?include_yanked=false`。Market 自己的版本列表 UI 默认 include_yanked=true（让作者/用户能看到历史撤回记录），客户端默认 include_yanked=false。`GET /versions/latest` 永远不会返回 yanked 版本（即便没有非 yanked 也是 404，而不是返回 yanked）。

### D7. min_app_version / max_app_version 是否在本特性启用

| 方案 | 说明 |
|---|---|
| A. 启用，前端展示 + 客户端可读 | 要前端 UI 能填、能展示 |
| B. **保留字段，前端只读展示，不强校验**（推荐） | UI 列表显示，但不基于它过滤 |
| C. 不动，留给以后 | 浪费已有列 |

**推荐 B**：前端版本列表展示这两个字段（如果非空），`publish-from-release` 接口接受这两个字段（作为请求体可选项），但 Market_Backend 不基于它做拒绝；客户端目前也未读取，等客户端 spec 接入后再做强校验。

---

## Requirements

### Requirement 1: Version 表结构扩展

**User Story:** As a Market_Backend 维护者, I want Version 表拥有 channel / is_latest / yanked_at / published_by 等字段, so that 后续业务逻辑有可落地的数据模型。

#### Acceptance Criteria

1. THE Market_Backend SHALL 在 `versions` 表上新增 `channel` 字段，类型为 `VARCHAR(16)`，非空，默认值 `"stable"`，取值仅限 `stable` / `beta` / `nightly` / `lts`。
2. THE Market_Backend SHALL 在 `versions` 表上新增 `is_latest` 字段，类型为 `BOOLEAN`，非空，默认值 `false`。
3. THE Market_Backend SHALL 在 `versions` 表上新增 `yanked_at` 字段，类型为 `DATETIME`，可空，默认值 `NULL`。
4. THE Market_Backend SHALL 在 `versions` 表上新增 `yanked_reason` 字段，类型为 `TEXT`，可空。
5. THE Market_Backend SHALL 在 `versions` 表上新增 `yanked_by` 字段，类型为 `INTEGER`，可空，外键指向 `users.id`。
6. THE Market_Backend SHALL 在 `versions` 表上新增 `published_by` 字段，类型为 `INTEGER`，可空，外键指向 `users.id`，记录发版操作者。
7. THE Market_Backend SHALL 在 `versions` 表上新增 `signature_id` 字段，类型为 `INTEGER`，可空，外键指向 `plugin_signatures.id`，本特性内不写入此字段，仅预留。
8. THE Market_Backend SHALL 在 `versions` 表上为 `(plugin_id, version)` 建立唯一索引。
9. THE Market_Backend SHALL 在 `versions` 表上为 `(plugin_id, channel, is_latest)` 建立部分索引（仅 `is_latest = true` 时生效），用于约束"每个 (plugin, channel) 至多一条 latest"。
10. THE Market_Backend SHALL 通过 alembic 迁移脚本变更上述结构，迁移可前进可回退。

### Requirement 2: 数据迁移 — 存量数据补全

**User Story:** As a Market_Backend 维护者, I want 存量 Version 行被填上合理的 channel 与 is_latest, so that 上线本特性后旧数据不会出现"没有 latest"或"channel 为空"的状态。

#### Acceptance Criteria

1. THE Market_Backend SHALL 在 alembic 迁移的 `upgrade()` 中，将所有现存 `versions` 行的 `channel` 设置为 `"stable"`。
2. WHEN 迁移执行时，THE Market_Backend SHALL 对每个 `plugin_id`，在该 plugin 的所有现存 versions 中按 `created_at` 降序选取第一条，将其 `is_latest` 置为 `true`，其余 `is_latest` 置为 `false`。
3. IF 一个 plugin 在 `versions` 表中没有任何记录，THEN THE Market_Backend SHALL 不为该 plugin 创建占位 version（保持空）。
4. THE Market_Backend SHALL 在迁移的 `downgrade()` 中删除新增的列与索引，但不要求恢复 `is_latest` 之前的（不存在的）状态。

### Requirement 3: 发布版本（从 GitHub Release）

**User Story:** As an Author, I want 通过提供 GitHub release URL 让 Market_Backend 自动拉取资产并冻结指纹, so that 我不需要手动算 sha256，也避免作者填错指纹。

#### Acceptance Criteria

1. THE Market_Backend SHALL 提供 `POST /api/v1/plugins/{plugin_id}/versions/publish-from-release` 接口，请求体包含 `release_url`（必填）、`channel`（可选，默认 `"stable"`）、`changelog`（可选）、`min_app_version` / `max_app_version`（可选）。
2. WHEN 请求到达且 `current_user.id == plugin.author_id` 或 `current_user` 拥有 `plugin_management` 权限，THE Market_Backend SHALL 接受请求；否则返回 HTTP 403。
3. THE Market_Backend SHALL 校验 `release_url` 的 GitHub owner/repo 等于 `plugin.repo_url` 的 owner/repo，否则返回 HTTP 400 并附错误码 `release_repo_mismatch`。
4. WHEN 接受请求后，THE Release_Fetcher SHALL 调用 GitHub API 获取 release 元数据，定位 release assets 中后缀为 `.neko-plugin` 或 `.neko-bundle` 的第一个 asset 作为 Release_Asset。
5. IF release 中找不到符合后缀的 asset，THEN THE Market_Backend SHALL 返回 HTTP 400，错误码 `release_asset_not_found`，且不写入任何 Version 行。
6. WHEN 找到 Release_Asset 后，THE Release_Fetcher SHALL 下载该 asset 的全部字节，下载上限为 200 MiB，超过则返回 HTTP 413 错误码 `release_asset_too_large`。
7. WHEN 下载完成，THE Release_Fetcher SHALL 计算下载字节的 SHA-256（小写十六进制）作为 `package_sha256`。
8. WHEN 下载完成，THE Release_Fetcher SHALL 解析 asset 内的 `metadata.toml` 中 `[payload].hash` 字段作为 `payload_hash` 写入；若 asset 内无该文件或字段则 `payload_hash` 留空。
9. THE Market_Backend SHALL 从 release 元数据中提取 `tag_name` 作为 `release_tag`，提取 release 页 URL 作为 `release_url`，提取 asset 的 `browser_download_url` 作为 `package_url` 并同时写入 `download_url`，提取 `target_commitish` 解析后的 commit sha 作为 `source_commit`。
10. THE Market_Backend SHALL 将 `plugin.repo_url` 写入 `source_repo_url`。
11. THE Market_Backend SHALL 使用 release `tag_name` 作为新 Version 的 `version` 字段（去除前导 `v` / `V`，例如 `v1.2.0` → `1.2.0`）。
12. IF `(plugin_id, version)` 已存在于 `versions` 表，THEN THE Market_Backend SHALL 返回 HTTP 409，错误码 `version_already_exists`，不写入。
13. WHEN 上述步骤全部成功，THE Market_Backend SHALL 在单个数据库事务中：
    - 将该 plugin 上 `channel == 请求 channel` 且 `is_latest == true` 的所有现存版本置为 `is_latest = false`；
    - 插入新 Version 行，`is_latest = true`，`published_by = current_user.id`，`channel = 请求 channel`，`yanked_at = NULL`，`verification_status = "passed"`（因为 hash 已由后端冻结）；
    - 当请求 channel 为 `"stable"`，且新版本 `is_latest = true` 时，更新 `plugins.version` 字段为该版本字符串。
14. IF 事务失败（数据库异常、网络异常、超时），THEN THE Market_Backend SHALL 回滚事务并返回 HTTP 502 错误码 `release_publish_failed`，且不留下任何半成品 Version 行。
15. THE Market_Backend SHALL 在每次 `publish-from-release` 调用（无论成败）时记录一条 `release_publish_attempt` 日志，字段包括 `plugin_id` / `actor_id` / `release_url` / `channel` / `outcome`（`success` / `failed`）/ `error_kind` / `error_message` / `attempted_at`。
16. THE Market_Backend SHALL 在响应体中返回新建的 Version 完整字段（含 `package_sha256`、`payload_hash`、`is_latest`、`channel`、`yanked_at`）。

### Requirement 4: 撤回版本（yank）与恢复（unyank）

**User Story:** As an Author or Admin, I want 撤回某个版本, so that 当版本有严重问题时可以阻止新用户继续安装。

#### Acceptance Criteria

1. THE Market_Backend SHALL 提供 `POST /api/v1/plugins/{plugin_id}/versions/{version_id}/yank` 接口，请求体含 `reason: string`（必填，1-500 字符）。
2. WHEN 请求者为 plugin 作者或拥有 `plugin_management` 权限的 Admin，THE Market_Backend SHALL 接受请求；否则返回 HTTP 403。
3. WHEN 请求被接受且 `versions[version_id].yanked_at IS NULL`，THE Market_Backend SHALL 在单个事务中：
    - 设置 `yanked_at = utc_now()`、`yanked_reason = reason`、`yanked_by = current_user.id`；
    - 如果该版本 `is_latest == true`，则将 `is_latest` 置为 `false`，并将该 (plugin_id, channel) 中 `yanked_at IS NULL` 且 `created_at` 最大的版本置为 `is_latest = true`；
    - 如果该版本是 `plugins.version` 当前指向的版本（即 channel=stable 且原本是 latest），更新 `plugins.version` 为新晋级的 latest 的版本字符串；如果没有可晋级的版本，保留原值不变。
4. IF 请求版本已经 `yanked_at != NULL`，THEN THE Market_Backend SHALL 返回 HTTP 409，错误码 `version_already_yanked`。
5. THE Market_Backend SHALL 提供 `POST /api/v1/plugins/{plugin_id}/versions/{version_id}/unyank` 接口，请求体可空。
6. WHEN unyank 请求被接受且 `versions[version_id].yanked_at IS NOT NULL`，THE Market_Backend SHALL 在单个事务中：
    - 设置 `yanked_at = NULL`、`yanked_reason = NULL`、`yanked_by = NULL`；
    - 不自动改动 `is_latest`（即 unyank 后不抢回 latest 标记）。
7. IF unyank 请求版本 `yanked_at IS NULL`，THEN THE Market_Backend SHALL 返回 HTTP 409，错误码 `version_not_yanked`。
8. THE Market_Backend SHALL 在 yank / unyank 操作完成后记录审计日志（沿用现有 `app.routers.admin.logs` 风格），含 `actor_id` / `plugin_id` / `version_id` / `action` / `reason` / `at`。

### Requirement 5: 修改版本元数据

**User Story:** As an Author or Admin, I want 修改 channel / changelog 等元数据, so that 我可以把一个 beta 版本"晋升"为 stable，或修正 changelog 文案。

#### Acceptance Criteria

1. THE Market_Backend SHALL 提供 `PATCH /api/v1/plugins/{plugin_id}/versions/{version_id}` 接口，请求体可包含 `channel`（可选）、`changelog`（可选）、`min_app_version`（可选）、`max_app_version`（可选）。
2. THE Market_Backend SHALL 拒绝在 PATCH 请求中修改 `package_sha256` / `payload_hash` / `package_url` / `download_url` / `release_url` / `release_tag` / `source_commit` / `source_repo_url` / `version` 字段，请求体含上述任一字段时返回 HTTP 400 错误码 `frozen_field_modification_forbidden`。
3. WHEN 请求者为 plugin 作者或 Admin，THE Market_Backend SHALL 接受请求；否则返回 HTTP 403。
4. WHEN 请求体包含 `channel` 且新 channel 与原 channel 不同，THE Market_Backend SHALL 在单个事务中：
    - 修改该版本的 `channel`；
    - 重新计算 (plugin_id, 旧 channel) 的 latest：选取 `yanked_at IS NULL` 且 `created_at` 最大的版本置为 `is_latest = true`，其余置 `false`；若无候选则旧 channel 不再有 latest；
    - 重新计算 (plugin_id, 新 channel) 的 latest：选取 `yanked_at IS NULL` 且 `created_at` 最大的版本置为 `is_latest = true`，其余置 `false`；
    - 如新 channel 为 `stable` 且该版本变为 stable 的 latest，更新 `plugins.version` 为该版本字符串；如旧 channel 为 stable 且该版本原本是 stable 的 latest，更新 `plugins.version` 为 stable 新晋级的 latest 版本字符串（若无则保留原值）。
5. IF 请求 `channel` 不在 `stable` / `beta` / `nightly` / `lts` 之内，THEN THE Market_Backend SHALL 返回 HTTP 400 错误码 `invalid_channel`。

### Requirement 6: 列表与查询 API 增强

**User Story:** As a Market_Frontend 或 NEKO_Client 开发者, I want 查询 versions 时支持按 channel 过滤、按是否包含 yanked 过滤, so that 不同消费方可以拿到自己想要的子集。

#### Acceptance Criteria

1. THE Market_Backend SHALL 在 `GET /api/v1/plugins/{plugin_id}/versions` 上支持查询参数 `channel`（可选，取值 `stable` / `beta` / `nightly` / `lts`），未传时返回所有 channel。
2. THE Market_Backend SHALL 在 `GET /api/v1/plugins/{plugin_id}/versions` 上支持查询参数 `include_yanked`（可选，`true` / `false`），默认值 `false`。
3. WHEN `include_yanked = false`，THE Market_Backend SHALL 仅返回 `yanked_at IS NULL` 的版本。
4. THE Market_Backend SHALL 按 `created_at` 降序返回版本列表。
5. THE Market_Backend SHALL 在 `GET /api/v1/plugins/{plugin_id}/versions/latest` 上支持查询参数 `channel`（可选，默认 `"stable"`）。
6. WHEN 查询 latest 时，THE Market_Backend SHALL 仅返回该 (plugin_id, channel) 中 `is_latest = true` 且 `yanked_at IS NULL` 的版本。
7. IF latest 查询找不到符合条件的版本，THEN THE Market_Backend SHALL 返回 HTTP 404，即便存在 yanked 版本也不返回。
8. THE Market_Backend SHALL 保证 versions 列表项 JSON 含字段 `id` / `plugin_id` / `version` / `channel` / `is_latest` / `yanked_at` / `yanked_reason` / `changelog` / `download_url` / `package_url` / `package_sha256` / `payload_hash` / `release_url` / `release_tag` / `source_commit` / `source_repo_url` / `min_app_version` / `max_app_version` / `created_at`，确保字段集是 NEKO_Client 现有期望的超集。

### Requirement 7: 已有 CRUD 路由的兼容性收紧

**User Story:** As a Market_Backend 维护者, I want 旧的 `POST /versions` 和 `DELETE /versions/{id}` 不再绕过新约束, so that 所有写入路径产生的数据都满足新模型。

#### Acceptance Criteria

1. WHEN 旧 `POST /api/v1/plugins/{plugin_id}/versions` 被调用，THE Market_Backend SHALL 仅允许 Admin 调用，作者调用返回 HTTP 403 错误码 `use_publish_from_release`。
2. WHEN Admin 通过旧 `POST /versions` 创建版本，THE Market_Backend SHALL 接受 `channel` 字段（默认 `"stable"`），并执行与 Requirement 3.13 相同的 is_latest 事务逻辑。
3. WHEN Admin 通过旧 `POST /versions` 创建版本未提供 `package_sha256`，THE Market_Backend SHALL 把 `verification_status` 写为 `"unverified"`；提供时写为 `"passed"`。
4. WHEN `DELETE /api/v1/plugins/{plugin_id}/versions/{version_id}` 被调用，THE Market_Backend SHALL 在删除前的事务中：若被删版本 `is_latest = true`，则将该 (plugin_id, channel) 中 `yanked_at IS NULL` 且 `created_at` 最大的剩余版本置为 latest。
5. THE Market_Backend SHALL 优先推荐使用 yank 而非 delete；接口文档中标注 `DELETE` 仅供管理员清理脏数据使用。

### Requirement 8: Market 前端 — 插件详情页版本列表

**User Story:** As a Market_Frontend 用户（普通访客或作者）, I want 在插件详情页看到版本列表, so that 我可以了解这个插件的发版历史和当前最新版。

#### Acceptance Criteria

1. THE Market_Frontend SHALL 在 `pages/PluginDetail.tsx` 增加"版本"标签页，调用 `GET /api/v1/plugins/{plugin_id}/versions?include_yanked=true` 获取列表。
2. THE Market_Frontend SHALL 为每条 version 渲染：版本号、channel 徽章、`package_sha256` 前 12 位（点击展开完整哈希）、`created_at` 本地时间、changelog（markdown 渲染）、latest 标记、yanked 标记。
3. WHEN 版本 `yanked_at != NULL`，THE Market_Frontend SHALL 把该行视觉置为灰阶并附 `已撤回` 徽章，hover 显示 `yanked_reason`。
4. WHEN 版本 `is_latest = true` 且 `yanked_at = NULL`，THE Market_Frontend SHALL 显示绿色 `最新` 徽章。
5. THE Market_Frontend SHALL 提供 channel 过滤器（按钮组：全部 / stable / beta / nightly / lts），默认 `全部`。
6. THE Market_Frontend SHALL 提供"显示已撤回版本"开关，默认开启。

### Requirement 9: Market 前端 — 作者发布新版本

**User Story:** As an Author, I want 在 Market 前端点击"发布新版本", so that 我不用打开 Postman 也能发版。

#### Acceptance Criteria

1. THE Market_Frontend SHALL 在 `pages/MyPlugins.tsx` 中为每个属于当前用户的已发布插件提供"发布新版本"按钮。
2. WHEN 用户点击"发布新版本"，THE Market_Frontend SHALL 弹出表单，字段含 `release_url`（必填，URL 格式校验）、`channel`（下拉，默认 `stable`）、`changelog`（多行文本，可空）、`min_app_version` / `max_app_version`（可空）。
3. WHEN 用户提交表单，THE Market_Frontend SHALL 调用 `POST /api/v1/plugins/{plugin_id}/versions/publish-from-release` 并展示进度态（pending / success / error）。
4. IF 后端返回错误码 `release_repo_mismatch`，THEN THE Market_Frontend SHALL 显示中文错误"GitHub release 不属于此插件的仓库"。
5. IF 后端返回 `release_asset_not_found`，THEN THE Market_Frontend SHALL 显示"未在此 release 中找到 .neko-plugin / .neko-bundle 资产"。
6. IF 后端返回 `version_already_exists`，THEN THE Market_Frontend SHALL 显示"该版本号已存在"。
7. WHEN 发布成功，THE Market_Frontend SHALL 关闭对话框、刷新版本列表、Toast 提示成功。

### Requirement 10: Market 前端 — 管理后台版本管理

**User Story:** As an Admin, I want 在管理后台对任意插件的版本进行 yank / unyank / 调整 channel, so that 出现安全问题时可以快速响应。

#### Acceptance Criteria

1. THE Market_Frontend SHALL 在 `src/admin/` 下增加版本管理页（路由 `/admin/plugins/{plugin_id}/versions`）。
2. THE Market_Frontend SHALL 在该页展示与 Requirement 8 相同结构的列表，但每行附带操作按钮：`Yank` / `Unyank` / `编辑（channel/changelog）`。
3. WHEN Admin 点击 `Yank`，THE Market_Frontend SHALL 弹出对话框要求填写撤回原因（1-500 字），调用 `POST /yank`。
4. WHEN Admin 点击 `Unyank`，THE Market_Frontend SHALL 弹确认后调用 `POST /unyank`。
5. WHEN Admin 编辑 channel 或 changelog 提交，THE Market_Frontend SHALL 调用 `PATCH /versions/{version_id}`。
6. THE Market_Frontend SHALL 在每次写操作完成后重新拉取版本列表（不依赖乐观更新）。

### Requirement 11: NEKO_Client 兼容性保证

**User Story:** As a NEKO_Client 维护者, I want Market 升级版本管理后客户端不需要改动也能正常工作, so that 客户端可以晚一些再适配新能力。

#### Acceptance Criteria

1. THE Market_Backend SHALL 在 `GET /api/v1/plugins/{plugin_id}/versions` 不传 `channel` / `include_yanked` 时，返回的字段集是 NEKO_Client `MarketPluginVersion` 接口的超集（包含 `id` / `plugin_id` / `version` / `changelog` / `download_url` / `package_url` / `package_sha256` / `payload_hash` / `created_at`）。
2. WHEN NEKO_Client 不传 `channel` 调用 `GET /versions/latest`，THE Market_Backend SHALL 默认按 `channel = "stable"` 返回（保持与升级前等价的语义）。
3. THE Market_Backend SHALL 不删除现有的 Version 字段；新增字段只增不减。

### Requirement 12: 错误处理与可观察性

**User Story:** As a Market_Backend 运维者, I want 发版相关错误集中可查, so that 能快速诊断发版失败的根因。

#### Acceptance Criteria

1. THE Market_Backend SHALL 为以下错误定义独立错误码并在响应 JSON 中以 `{"detail": "...", "code": "release_repo_mismatch"}` 形式返回：`release_repo_mismatch` / `release_asset_not_found` / `release_asset_too_large` / `release_publish_failed` / `version_already_exists` / `version_already_yanked` / `version_not_yanked` / `frozen_field_modification_forbidden` / `invalid_channel` / `use_publish_from_release`。
2. WHEN 拉取 GitHub release 时发生网络错误（超时、5xx、429），THE Release_Fetcher SHALL 在抛出异常前重试 1 次（指数退避 0.5s），仍失败则按 Requirement 3.14 处理。
3. THE Market_Backend SHALL 把 `release_publish_attempt` 日志保留至少 90 天，可由 Admin 通过 `/api/v1/admin/logs` 现有接口查询（具体接入点在 design 阶段细化）。

---

## Property-Based Testing — Correctness Properties

下列性质应在 design 阶段映射到 Hypothesis（后端）/ fast-check（前端）测试用例。每条均给出"输入空间 + 应保持的不变量"。

### P1. 同 (plugin, channel) 的 is_latest 至多一条

**输入空间:** 任意发版操作序列（publish-from-release / yank / unyank / patch channel / delete / 旧 POST /versions）。

**性质:** 操作序列结束后，对所有 (plugin_id, channel) 二元组，满足 `is_latest = true AND yanked_at IS NULL` 的 versions 行数恰好 ≤ 1。

**为什么是 PBT:** 输入是序列空间，状态机式探索能找到事务竞态、错误回滚后状态错乱、PATCH channel 时双方 channel 同时更新失败等 corner case；2-3 个例子无法覆盖。

### P2. yank 后再 unyank 不改变 is_latest 状态

**输入空间:** 任意 (plugin_id, version_id) 已发布且 `yanked_at IS NULL` 的初始状态，操作序列 `yank → unyank`。

**性质:** 操作序列结束后，该 version 的 `is_latest` 与序列开始前相比，**可能不同**（因 yank 时如果是 latest 会让位给次新版），但 unyank 单独执行不能改动 `is_latest`。具体形式：`is_latest_after_unyank == is_latest_after_yank`（unyank 是 is_latest 的恒等映射）。

**为什么是 PBT:** 验证 unyank 实现是不是真的"什么都不动" is_latest，避免有人误加 `is_latest = true` 的副作用。

### P3. publish-from-release 的 hash 与 release asset 字节级一致

**输入空间:** 任意 mock 的 release asset 字节流（含空文件、1 字节、含 NUL 字节、含 UTF-8 BOM、最多 200 MiB-1 字节）。

**性质:** `Version.package_sha256 == sha256(asset_bytes).hexdigest().lower()`，且 Market_Backend 写入数据库的值与 `hashlib.sha256(asset_bytes).hexdigest()` 在 byte-for-byte 上一致。

**为什么是 PBT:** 流式下载与 chunk 边界、超大文件、HTTP gzip 解压（不应启用）都可能让算 hash 偏离 asset 真实字节；属性级测试覆盖 chunk 大小空间。

### P4. publish-from-release 的幂等性（同 release_url 重复发版被拒）

**输入空间:** 任意已存在的 (plugin_id, version) 行，再次发起同一 release_url 的 publish-from-release。

**性质:** 重复调用永远返回 HTTP 409 `version_already_exists` 且不写入新行；versions 表行数不变。

**为什么是 PBT:** 探索"作者狂点提交按钮"、"同时两个浏览器 tab 提交"等并发情况，幂等性必须在并发下也成立。

### P5. channel 过滤的封闭性

**输入空间:** 任意 versions 表状态、任意 channel ∈ {`stable`, `beta`, `nightly`, `lts`}。

**性质:** `GET /versions?channel=X` 返回的所有项满足 `item.channel == X`；不传 `channel` 时返回所有 channel 的并集；`include_yanked=false` 返回的项均满足 `item.yanked_at IS NULL`；`include_yanked=true` 是其超集。

**为什么是 PBT:** 验证查询条件不会"漏过"某个 channel 或 yanked 状态。

### P6. PATCH channel 后旧 channel 与新 channel 的 latest 都自洽

**输入空间:** 任意已发布版本，PATCH 改动 channel 到任意合法值。

**性质:** PATCH 完成后，重新查询 (plugin, 旧 channel) latest 与 (plugin, 新 channel) latest，两者要么是 `yanked_at IS NULL` 且 `created_at` 最大的版本，要么不存在；不会出现"旧 channel 还指着已经搬走的版本作为 latest"。

**为什么是 PBT:** PATCH 同时影响两边 channel，事务边界稍写错就漏一边；属性测试遍历 channel 切换矩阵。

### P7. 旧 CRUD 接口产生的数据满足新约束

**输入空间:** 任意通过旧 `POST /versions` / `DELETE /versions/{id}` 调用产生的状态序列。

**性质:** 序列结束后，P1（is_latest 唯一性）、P5（channel 封闭性）仍然成立；旧接口不会留下 `channel` 为空或非合法枚举的行。

**为什么是 PBT:** 防止后端两条写入路径行为漂移。

### P8. version 字符串唯一约束

**输入空间:** 任意 (plugin_id, version) 字符串组合，含特殊字符、空格、长度边界。

**性质:** 同 plugin_id 下，重复 version 字符串第二次写入返回 HTTP 409；不同 plugin_id 下相同 version 字符串可共存。

**为什么是 PBT:** 验证唯一约束作用域是 (plugin_id, version) 而不是 version 全局。

### P9. yank 后 latest 自动晋级 — 全序列一致性

**输入空间:** 任意发版顺序 + 任意子集被 yank 的序列。

**性质:** 任意时刻，对每个 (plugin_id, channel)，若存在 `yanked_at IS NULL` 的版本，则 latest 必然指向其中 `created_at` 最大的那一条；若不存在，则该 (plugin_id, channel) 没有 latest。

**为什么是 PBT:** yank 与 publish 交叉执行时，latest 晋级逻辑必须始终满足"指向当前 channel 的最新非 yanked 版本"。

### P10. Frozen_Fact 字段不可被 PATCH 修改

**输入空间:** 任意 PATCH 请求体含 frozen field（`package_sha256` / `payload_hash` / `package_url` / `download_url` / `release_url` / `release_tag` / `source_commit` / `source_repo_url` / `version`）。

**性质:** 数据库 row 上述字段在 PATCH 前后字节级相等，且响应为 HTTP 400 `frozen_field_modification_forbidden`。

**为什么是 PBT:** Pydantic schema 误加字段、未来 schema 演进时容易破坏此约束；属性测试可用大量 mutation 探索。

---

## 后续阶段说明

需求文档在此告一段落。下一阶段（design）将：

1. 把 Requirement 1 的字段加成翻译为具体的 SQLAlchemy 模型 diff 与 alembic 迁移脚本；
2. 把 Requirement 3 的发版流程画成时序图（Author → Market_Frontend → Market_Backend → Release_Fetcher → GitHub API → DB）；
3. 把 P1–P10 的 PBT 性质映射到具体 Hypothesis 测试模块（建议放在 `tests/properties/test_version_management.py`），并设计 mock GitHub API 的策略；
4. 给前端 `MyPlugins.tsx` / `PluginDetail.tsx` / 管理后台版本管理页画线框；
5. 详细化错误码到中文文案的映射表。

请 review 上方 D1–D7 的推荐方案以及 Requirements 1–12，确认无误后告知进入 design 阶段，或直接 "Skip to Implementation Plan" 让我连续把 design 与 tasks 都生成出来。
