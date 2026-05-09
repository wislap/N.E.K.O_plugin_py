/**
 * InstallButton — 一键安装插件到本地 N.E.K.O 客户端
 *
 * 状态流转：
 * idle → probing → ready / offline
 * ready → installing → progress → success / error
 * offline → fallback (URI Scheme / 下载)
 */

import { useState, useEffect, useCallback } from "react"
import { nekoBridge, type InstallTask } from "@/lib/neko-bridge"

interface InstallButtonProps {
  pluginId: string
  version: string
  packageUrl: string
  packageSha256: string
  payloadHash?: string
  /** 外部控制：是否已安装 */
  isInstalled?: boolean
  onInstalled?: () => void
  className?: string
}

type ButtonState =
  | "idle"
  | "probing"
  | "ready"
  | "offline"
  | "no-token"
  | "installing"
  | "success"
  | "error"

export function InstallButton({
  pluginId,
  version,
  packageUrl,
  packageSha256,
  payloadHash,
  isInstalled: externalInstalled,
  onInstalled,
  className = "",
}: InstallButtonProps) {
  const [state, setState] = useState<ButtonState>("idle")
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")

  // 探测客户端状态
  useEffect(() => {
    let cancelled = false

    async function probe() {
      setState("probing")
      const status = await nekoBridge.probe()
      if (cancelled) return

      if (!status) {
        setState("offline")
      } else if (!nekoBridge.hasToken) {
        setState("no-token")
      } else {
        setState("ready")
      }
    }

    probe()
    return () => { cancelled = true }
  }, [])

  // 处理安装进度
  const handleProgress = useCallback((task: InstallTask) => {
    setProgress(task.progress)
    setMessage(task.message)

    if (task.status === "completed") {
      setState("success")
      onInstalled?.()
    } else if (task.status === "failed") {
      setState("error")
      setError(task.error || "安装失败")
    }
  }, [onInstalled])

  // 触发安装
  const handleInstall = useCallback(async () => {
    setState("installing")
    setProgress(0)
    setMessage("正在准备...")
    setError("")

    const taskId = await nekoBridge.install(
      {
        package_url: packageUrl,
        package_sha256: packageSha256,
        payload_hash: payloadHash,
        plugin_id: pluginId,
        version,
      },
      handleProgress,
    )

    // 如果返回 null，说明走了 fallback（URI Scheme / 下载）
    if (!taskId) {
      setState("offline")
    }
  }, [packageUrl, packageSha256, payloadHash, pluginId, version, handleProgress])

  // 已安装状态
  if (externalInstalled) {
    return (
      <button
        disabled
        className={`install-btn install-btn--installed ${className}`}
      >
        ✓ 已安装
      </button>
    )
  }

  // 根据状态渲染
  switch (state) {
    case "idle":
    case "probing":
      return (
        <button disabled className={`install-btn install-btn--loading ${className}`}>
          检测中...
        </button>
      )

    case "ready":
      return (
        <button
          onClick={handleInstall}
          className={`install-btn install-btn--ready ${className}`}
        >
          安装到 N.E.K.O
        </button>
      )

    case "no-token":
      return (
        <button
          onClick={handleInstall}
          className={`install-btn install-btn--warning ${className}`}
          title="未配对，将尝试 URI Scheme 方式安装"
        >
          安装到 N.E.K.O
        </button>
      )

    case "offline":
      return (
        <div className="install-btn-group">
          <button
            onClick={handleInstall}
            className={`install-btn install-btn--offline ${className}`}
            title="客户端未检测到，将尝试唤起或下载"
          >
            安装
          </button>
          <a
            href={packageUrl}
            download
            className="install-btn install-btn--download"
            title="直接下载 .neko-plugin 文件"
          >
            ↓
          </a>
        </div>
      )

    case "installing":
      return (
        <button disabled className={`install-btn install-btn--progress ${className}`}>
          <span className="install-btn__bar" style={{ width: `${progress * 100}%` }} />
          <span className="install-btn__text">
            {message || `${Math.round(progress * 100)}%`}
          </span>
        </button>
      )

    case "success":
      return (
        <button disabled className={`install-btn install-btn--success ${className}`}>
          ✓ 安装成功
        </button>
      )

    case "error":
      return (
        <button
          onClick={handleInstall}
          className={`install-btn install-btn--error ${className}`}
          title={error}
        >
          安装失败，重试
        </button>
      )
  }
}
