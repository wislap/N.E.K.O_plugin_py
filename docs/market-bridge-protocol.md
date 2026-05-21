# N.E.K.O ↔ Market Bridge 协议

## 概述

本协议定义了 N.E.K.O 本地客户端与插件市场（Plugin Market）之间的双向通信方式。

## 架构

```
┌─────────────────────────┐              ┌─────────────────────────┐
│  Plugin Market (Web)    │              │  N.E.K.O (Local)        │
│                         │              │                         │
│  Frontend (React)       │─── HTTP ────►│  Plugin Server :48911   │
│  nekoBridge SDK         │              │  /market/* endpoints    │
│                         │              │                         │
│  Backend (FastAPI)      │◄── HTTPS ────│  OAuth / API calls      │
│  api.market.com         │              │                         │
└─────────────────────────┘              └─────────────────────────┘
         │                                         ▲
         │          neko://install?...             │
         └─────────── URI Scheme ─────────────────┘
```

## 通信方式

| 方向 | 方式 | 用途 |
|------|------|------|
| Market → N.E.K.O | localhost HTTP | 安装、查询状态（主通道） |
| Market → N.E.K.O | `neko://` URI Scheme | 唤起客户端（fallback） |
| N.E.K.O → Market | HTTPS API | 登录、同步数据 |

## 端点定义

### `GET /market/status`

探测客户端是否在线。**不需要 token**。

**Response:**
```json
{
  "online": true,
  "version": "0.1.0",
  "protocol_version": 1,
  "client_name": "N.E.K.O Plugin Server",
  "installed_count": 12,
  "token_required": true
}
```

### `POST /market/install?token={bridge_token}`

触发插件安装（异步）。

**Request:**
```json
{
  "package_url": "https://github.com/.../lifekit-1.2.0.neko-plugin",
  "package_sha256": "abcdef1234567890...",
  "payload_hash": "optional_payload_hash",
  "plugin_id": "lifekit",
  "version": "1.2.0",
  "on_conflict": "rename"
}
```

**Response:**
```json
{
  "task_id": "abc123",
  "status": "pending",
  "message": "安装任务已创建，正在下载包..."
}
```

### `GET /market/tasks/{task_id}?token={bridge_token}`

查询安装进度。

**Response:**
```json
{
  "task_id": "abc123",
  "status": "downloading",
  "progress": 0.45,
  "message": "正在下载: 2048KB / 4096KB",
  "result": null,
  "error": null
}
```

Status 值: `pending` → `downloading` → `verifying` → `installing` → `completed` | `failed`

### `GET /market/installed?token={bridge_token}`

查询已安装插件列表。

**Response:**
```json
{
  "installed": [
    {"plugin_id": "lifekit", "path": "/home/user/.neko/plugins/lifekit"},
    {"plugin_id": "translator", "path": "/home/user/.neko/plugins/translator"}
  ],
  "count": 2
}
```

### `POST /market/token-exchange`

通过一次性码获取 bridge token。**不需要 token**（因为这是获取 token 的端点）。

**Request:**
```json
{
  "one_time_code": "aBcDeFgH"
}
```

**Response:**
```json
{
  "bridge_token": "full_token_string...",
  "expires_in": null
}
```

## 安全模型

### Bridge Token

- 每次 N.E.K.O 启动时生成随机 token
- 写入 `~/.neko/bridge.json`，文件权限应为仅 owner 可读写（`0600`）：
  `{"token": "...", "port": 48911, "one_time_code": "...", "one_time_code_expires_in": 300}`
- Market 前端通过以下方式获取 token：
  1. 用户在 N.E.K.O 面板点"连接市场" → 生成短期一次性码 → 用户粘贴到 Market 网页
  2. 或通过 `neko://pair?code=xxx` URI 自动传递
- Token 存储在 localStorage，重启 N.E.K.O 后需要重新配对
- 一次性码仅存在本地内存中，默认 5 分钟过期，成功交换后立即失效

### 安装包可信度

- Market 一键安装只应使用 `latest_version.package_url` 和 `latest_version.package_sha256`
- `package_url` 必须指向真实 `.neko-plugin` / `.neko-bundle` 资产，不能 fallback 到仓库主页
- 没有 `package_sha256` 的版本只能展示为“暂无可安装版本”或让用户前往源码页手动处理
- `plugin_id` 表示 Market 数据库 ID；如需校验包内 `plugin.toml` 身份，应额外传 `expected_plugin_toml_id`

### 为什么不只用 CORS？

CORS 只在浏览器层面生效，curl/脚本可以绕过。Bridge token 确保只有经过用户授权的网页才能调用本地 API。

## URI Scheme

### 注册

N.E.K.O 安装时注册 `neko://` 协议处理器：
- Windows: 注册表 `HKCU\Software\Classes\neko`
- macOS: Info.plist CFBundleURLTypes
- Linux: `~/.local/share/applications/neko.desktop` 的 MimeType

### 支持的 URI

```
neko://install?url={package_url}&sha256={hash}&id={plugin_id}&version={ver}
neko://auth/callback?code={oauth_code}&state={state}
neko://pair?code={one_time_code}
neko://open?plugin={plugin_id}
```

## OAuth 登录流程（N.E.K.O → Market）

1. N.E.K.O 生成 `state` + PKCE `code_verifier` / `code_challenge`
2. 打开浏览器: `market.com/oauth/authorize?client_id=neko-desktop&redirect_uri=neko://auth/callback&state=xxx&code_challenge=yyy`
3. 用户在 Market 网页登录并授权
4. Market 302 重定向到 `neko://auth/callback?code=abc&state=xxx`
5. 系统唤起 N.E.K.O，N.E.K.O 收到 code
6. N.E.K.O 调用 `POST market.com/oauth/token` 换取 access_token
7. 本地存储 token，后续 API 调用带上

## 前端 SDK 使用

```typescript
import { nekoBridge } from "@/lib/neko-bridge"

// 探测客户端
const status = await nekoBridge.probe()
if (status) {
  console.log(`N.E.K.O 在线，已安装 ${status.installed_count} 个插件`)
}

// 安装插件
const taskId = await nekoBridge.install(
  {
    package_url: "https://...",
    package_sha256: "abc...",
    plugin_id: "lifekit",
    version: "1.2.0",
  },
  (task) => {
    console.log(`进度: ${task.progress * 100}% - ${task.message}`)
  }
)

// 检查是否已安装
const installed = await nekoBridge.isInstalled("lifekit")
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `NEKO_MARKET_ORIGINS` | 允许的 Market 域名（逗号分隔） | 空（仅允许 localhost） |

示例: `NEKO_MARKET_ORIGINS=https://neko-market.com,https://market.neko.app`
