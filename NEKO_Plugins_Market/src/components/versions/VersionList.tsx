import { useEffect, useMemo, useState } from "react";
import { ChevronDown, Plus, RefreshCw, Trash2 } from "lucide-react";
import { marked } from "marked";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { versionsApi } from "@/services/versions";
import type { PluginVersion } from "@/services/types";
import { getErrorMessage, reportError } from "@/lib/error-reporting";
import { formatDate } from "@/lib/utils";

import { PublishFromReleaseDialog } from "./PublishFromReleaseDialog";
import { YankDialog } from "./YankDialog";

type ChannelFilter = "all" | "stable" | "beta";

interface VersionListProps {
  pluginId: number;
  /** 当前用户是否是该插件作者 */
  canAuthorManage: boolean;
  /** 当前用户是否是 admin（与作者身份独立） */
  isAdmin: boolean;
  /** 是否在挂载后立即打开 publish dialog（用于 ?action=publish 跳转） */
  autoOpenPublish?: boolean;
  /** publish 完成后清除 ?action=publish 查询参数的回调 */
  onAutoOpenConsumed?: () => void;
}

export function VersionList({
  pluginId,
  canAuthorManage,
  isAdmin,
  autoOpenPublish,
  onAutoOpenConsumed,
}: VersionListProps) {
  const [versions, setVersions] = useState<PluginVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [channelFilter, setChannelFilter] = useState<ChannelFilter>("all");
  const [includeYanked, setIncludeYanked] = useState(true);
  const [expandedSha, setExpandedSha] = useState<Record<number, boolean>>({});

  const [publishOpen, setPublishOpen] = useState(false);
  const [yankTarget, setYankTarget] = useState<PluginVersion | null>(null);

  const canManage = canAuthorManage || isAdmin;
  const adminAction = isAdmin && !canAuthorManage;

  const refresh = useMemo(
    () => async () => {
      setLoading(true);
      setError("");
      try {
        const items = await versionsApi.list(pluginId, {
          channel: channelFilter === "all" ? undefined : channelFilter,
          includeYanked,
        });
        setVersions(items);
      } catch (err) {
        setError(getErrorMessage(err, "加载版本列表失败"));
        reportError(err, {
          title: "版本列表加载失败",
          context: {
            module: "versionList",
            action: "list",
            pluginId,
            channelFilter,
            includeYanked,
          },
        });
      } finally {
        setLoading(false);
      }
    },
    [pluginId, channelFilter, includeYanked],
  );

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (autoOpenPublish && canManage) {
      setPublishOpen(true);
      onAutoOpenConsumed?.();
    }
  }, [autoOpenPublish, canManage, onAutoOpenConsumed]);


  return (
    <div className="space-y-4">
      {/* 顶部工具栏 */}
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-1 rounded-lg border border-slate-800/60 bg-[#1A1A2E] p-1">
          {(["all", "stable", "beta"] as ChannelFilter[]).map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() => setChannelFilter(opt)}
              className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                channelFilter === opt
                  ? "bg-primary text-primary-foreground"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {opt === "all" ? "全部" : opt}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-400">
            <Switch
              checked={includeYanked}
              onCheckedChange={setIncludeYanked}
            />
            包含已撤回版本
          </label>
          <Button
            size="sm"
            variant="outline"
            className="border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white"
            onClick={() => refresh()}
            disabled={loading}
          >
            <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            刷新
          </Button>
          {canManage && (
            <Button
              size="sm"
              className="bg-primary text-primary-foreground hover:bg-primary/90"
              onClick={() => setPublishOpen(true)}
            >
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              发布新版本
            </Button>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {!loading && versions.length === 0 && !error && (
        <div className="rounded-2xl border border-slate-800/50 bg-[#1A1A2E] p-12 text-center text-slate-500">
          {canManage ? "该插件尚未发布任何版本，点击右上角发布第一版" : "该插件尚未发布任何版本"}
        </div>
      )}

      {/* 版本卡片列表 */}
      <div className="space-y-3">
        {versions.map((v) => (
          <VersionRow
            key={v.id}
            version={v}
            shaExpanded={!!expandedSha[v.id]}
            onToggleSha={() =>
              setExpandedSha((prev) => ({ ...prev, [v.id]: !prev[v.id] }))
            }
            canYank={canManage && v.yanked_at === null}
            adminAction={adminAction}
            onYank={() => setYankTarget(v)}
          />
        ))}
      </div>

      <PublishFromReleaseDialog
        open={publishOpen}
        onOpenChange={setPublishOpen}
        pluginId={pluginId}
        onSuccess={() => {
          setPublishOpen(false);
          refresh();
        }}
      />

      {yankTarget && (
        <YankDialog
          open={true}
          onOpenChange={(open) => {
            if (!open) setYankTarget(null);
          }}
          pluginId={pluginId}
          version={yankTarget}
          adminAction={adminAction}
          onSuccess={() => {
            setYankTarget(null);
            refresh();
          }}
        />
      )}
    </div>
  );
}


interface VersionRowProps {
  version: PluginVersion;
  shaExpanded: boolean;
  onToggleSha: () => void;
  canYank: boolean;
  adminAction: boolean;
  onYank: () => void;
}

function VersionRow({
  version,
  shaExpanded,
  onToggleSha,
  canYank,
  adminAction,
  onYank,
}: VersionRowProps) {
  const isYanked = version.yanked_at !== null;
  const isLatest = version.is_latest && !isYanked;
  const channelLabel = version.channel;
  const sha = version.package_sha256 || "";
  const shaShort = sha ? sha.slice(0, 12) : "";
  const changelogHtml = useMemo(
    () => (version.changelog ? marked.parse(version.changelog) : ""),
    [version.changelog],
  );

  return (
    <div
      className={`rounded-xl border p-4 transition-colors ${
        isYanked
          ? "border-slate-800/50 bg-[#15151f] opacity-60"
          : "border-slate-800/50 bg-[#1A1A2E]"
      }`}
      title={isYanked ? `已撤回原因：${version.yanked_reason ?? "—"}` : undefined}
    >
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <span className="font-mono text-base font-semibold text-white">
          v{version.version}
        </span>
        <Badge
          className={
            channelLabel === "stable"
              ? "bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/20"
              : "bg-amber-500/15 text-amber-300 hover:bg-amber-500/20"
          }
        >
          {channelLabel}
        </Badge>
        {isLatest && (
          <Badge className="bg-primary/20 text-primary hover:bg-primary/25">
            最新
          </Badge>
        )}
        {isYanked && (
          <Badge className="bg-red-500/15 text-red-300 hover:bg-red-500/20">
            已撤回
          </Badge>
        )}
        <span className="ml-auto text-xs text-slate-500">
          {formatDate(version.created_at)}
        </span>
      </div>

      {shaShort && (
        <button
          type="button"
          onClick={onToggleSha}
          className="mb-2 inline-flex items-center gap-1 font-mono text-xs text-slate-500 hover:text-slate-300"
        >
          sha256: {shaExpanded ? sha : `${shaShort}…`}
          <ChevronDown
            className={`h-3 w-3 transition-transform ${shaExpanded ? "rotate-180" : ""}`}
          />
        </button>
      )}

      {changelogHtml && (
        <div
          className="prose prose-invert max-w-none text-sm"
          dangerouslySetInnerHTML={{ __html: changelogHtml }}
        />
      )}

      {isYanked && version.yanked_reason && (
        <p className="mt-2 text-xs text-red-300/80">
          撤回原因：{version.yanked_reason}
        </p>
      )}

      {canYank && (
        <div className="mt-3 flex justify-end">
          <Button
            size="sm"
            variant="outline"
            className="border-red-500/40 text-red-300 hover:bg-red-500/10 hover:text-red-200"
            onClick={onYank}
          >
            <Trash2 className="mr-1.5 h-3.5 w-3.5" />
            {adminAction ? "管理员撤回" : "撤回"}
          </Button>
        </div>
      )}
    </div>
  );
}
