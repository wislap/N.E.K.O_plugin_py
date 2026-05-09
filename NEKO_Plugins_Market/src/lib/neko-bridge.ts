/**
 * N.E.K.O Bridge — Market 前端与本地客户端的通信层
 *
 * 提供：
 * - 探测本地客户端是否在线
 * - 触发插件安装（带进度轮询）
 * - 查询已安装插件列表
 * - Token 配对流程
 * - URI Scheme fallback
 */

const DEFAULT_PORT = 48911
const PORT_RANGE = [48911, 48912, 48913, 48914, 48915] as const
const PROBE_TIMEOUT = 3000
const POLL_INTERVAL = 1000

const STORAGE_KEY_TOKEN = "neko_bridge_token"
const STORAGE_KEY_PORT = "neko_bridge_port"

export interface BridgeStatus {
  online: boolean
  version: string
  protocol_version: number
  client_name: string
  installed_count: number
}

export interface InstallRequest {
  package_url: string
  package_sha256: string
  payload_hash?: string
  plugin_id?: string
  version?: string
  on_conflict?: "rename" | "fail"
}

export interface InstallTask {
  task_id: string
  status: "pending" | "downloading" | "verifying" | "installing" | "completed" | "failed"
  progress: number
  message: string
  result?: Record<string, unknown>
  error?: string
}

export interface InstalledPlugin {
  plugin_id: string
  path: string
}

type InstallProgressCallback = (task: InstallTask) => void

class NekoBridge {
  private _port: number | null = null
  private _token: string | null = null
  private _online: boolean | null = null

  constructor() {
    // 从 localStorage 恢复
    this._token = localStorage.getItem(STORAGE_KEY_TOKEN)
    const savedPort = localStorage.getItem(STORAGE_KEY_PORT)
    if (savedPort) this._port = parseInt(savedPort, 10)
  }

  get online(): boolean | null {
    return this._online
  }

  get hasToken(): boolean {
    return !!this._token
  }

  private get baseUrl(): string {
    return `http://127.0.0.1:${this._port || DEFAULT_PORT}`
  }

  // ─── 探测 ────────────────────────────────────────────────────

  /**
   * 探测本地客户端是否在线。
   * 会依次尝试已知端口，找到后缓存。
   */
  async probe(): Promise<BridgeStatus | null> {
    // 优先尝试缓存的端口
    if (this._port) {
      const status = await this._probePort(this._port)
      if (status) {
        this._online = true
        return status
      }
    }

    // 扫描端口范围
    for (const port of PORT_RANGE) {
      if (port === this._port) continue
      const status = await this._probePort(port)
      if (status) {
        this._port = port
        localStorage.setItem(STORAGE_KEY_PORT, String(port))
        this._online = true
        return status
      }
    }

    this._online = false
    return null
  }

  private async _probePort(port: number): Promise<BridgeStatus | null> {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/market/status`, {
        signal: AbortSignal.timeout(PROBE_TIMEOUT),
      })
      if (res.ok) {
        return await res.json()
      }
    } catch {
      // 端口不可达
    }
    return null
  }

  // ─── Token 配对 ──────────────────────────────────────────────

  /**
   * 通过一次性码交换 bridge token。
   * 一次性码由 N.E.K.O 客户端通过 neko:// URI 或用户手动提供。
   */
  async exchangeToken(oneTimeCode: string): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/market/token-exchange`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ one_time_code: oneTimeCode }),
      })
      if (res.ok) {
        const data = await res.json()
        this._token = data.bridge_token
        localStorage.setItem(STORAGE_KEY_TOKEN, data.bridge_token)
        return true
      }
    } catch {
      // 连接失败
    }
    return false
  }

  /**
   * 清除已保存的 token（断开配对）。
   */
  disconnect(): void {
    this._token = null
    this._port = null
    localStorage.removeItem(STORAGE_KEY_TOKEN)
    localStorage.removeItem(STORAGE_KEY_PORT)
    this._online = null
  }

  // ─── 安装 ────────────────────────────────────────────────────

  /**
   * 触发插件安装。
   *
   * 优先使用 localhost API（带进度），fallback 到 URI Scheme。
   * 返回 task_id 或 null（fallback 到 URI/下载时）。
   */
  async install(
    request: InstallRequest,
    onProgress?: InstallProgressCallback,
  ): Promise<string | null> {
    // 尝试 localhost API
    if (this._token && (await this.probe())) {
      try {
        const url = new URL(`${this.baseUrl}/market/install`)
        url.searchParams.set("token", this._token)

        const res = await fetch(url.toString(), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(request),
        })

        if (res.ok) {
          const data = await res.json()
          const taskId = data.task_id as string

          // 开始轮询进度
          if (onProgress) {
            this._pollProgress(taskId, onProgress)
          }

          return taskId
        }

        if (res.status === 403) {
          // Token 失效
          this.disconnect()
        }
      } catch {
        // localhost 不可达
      }
    }

    // Fallback: URI Scheme
    this._fallbackUriScheme(request)
    return null
  }

  /**
   * 轮询安装任务进度。
   */
  async getTaskStatus(taskId: string): Promise<InstallTask | null> {
    if (!this._token) return null

    try {
      const url = new URL(`${this.baseUrl}/market/tasks/${taskId}`)
      url.searchParams.set("token", this._token)

      const res = await fetch(url.toString())
      if (res.ok) {
        return await res.json()
      }
    } catch {
      // 连接失败
    }
    return null
  }

  private _pollProgress(taskId: string, onProgress: InstallProgressCallback): void {
    const poll = async () => {
      const task = await this.getTaskStatus(taskId)
      if (!task) return

      onProgress(task)

      if (task.status !== "completed" && task.status !== "failed") {
        setTimeout(poll, POLL_INTERVAL)
      }
    }
    setTimeout(poll, 500)
  }

  // ─── 已安装列表 ──────────────────────────────────────────────

  /**
   * 查询本地已安装的插件 ID 列表。
   */
  async getInstalled(): Promise<InstalledPlugin[]> {
    if (!this._token || !(await this.probe())) return []

    try {
      const url = new URL(`${this.baseUrl}/market/installed`)
      url.searchParams.set("token", this._token)

      const res = await fetch(url.toString())
      if (res.ok) {
        const data = await res.json()
        return data.installed || []
      }
    } catch {
      // 连接失败
    }
    return []
  }

  /**
   * 快速检查某个插件是否已安装。
   */
  async isInstalled(pluginId: string): Promise<boolean> {
    const installed = await this.getInstalled()
    return installed.some((p) => p.plugin_id === pluginId)
  }

  // ─── URI Scheme Fallback ─────────────────────────────────────

  private _fallbackUriScheme(request: InstallRequest): void {
    const params = new URLSearchParams()
    params.set("url", request.package_url)
    params.set("sha256", request.package_sha256)
    if (request.plugin_id) params.set("id", request.plugin_id)
    if (request.version) params.set("version", request.version)
    if (request.payload_hash) params.set("payload_hash", request.payload_hash)

    const uri = `neko://install?${params.toString()}`

    // 尝试唤起客户端
    window.location.href = uri

    // 2 秒后如果还在当前页面，说明协议未注册，提供下载兜底
    setTimeout(() => {
      if (document.hasFocus()) {
        // 用户还在页面上，说明 neko:// 没有被处理
        const shouldDownload = window.confirm(
          "未检测到 N.E.K.O 客户端。\n是否直接下载插件包文件？"
        )
        if (shouldDownload) {
          window.open(request.package_url, "_blank")
        }
      }
    }, 2000)
  }

  // ─── OAuth 辅助 ──────────────────────────────────────────────

  /**
   * 生成 Market OAuth 授权 URL（供 N.E.K.O 客户端使用）。
   */
  static buildOAuthUrl(params: {
    marketBaseUrl: string
    clientId?: string
    state: string
    codeChallenge: string
  }): string {
    const url = new URL("/oauth/authorize", params.marketBaseUrl)
    url.searchParams.set("client_id", params.clientId || "neko-desktop")
    url.searchParams.set("redirect_uri", "neko://auth/callback")
    url.searchParams.set("state", params.state)
    url.searchParams.set("code_challenge", params.codeChallenge)
    url.searchParams.set("code_challenge_method", "S256")
    url.searchParams.set("response_type", "code")
    return url.toString()
  }
}

/** 全局单例 */
export const nekoBridge = new NekoBridge()
