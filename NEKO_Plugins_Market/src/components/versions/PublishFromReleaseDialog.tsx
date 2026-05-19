import { useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getVersionErrorMessage, versionsApi } from "@/services/versions";
import { reportError } from "@/lib/error-reporting";
import type { VersionReleaseCandidate } from "@/services/types";

const RELEASE_URL_PATTERN =
  /^https?:\/\/github\.com\/[^/]+\/[^/]+\/releases\/(?:tag\/[^/?#]+|\d+)\/?$/i;

interface PublishFromReleaseDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  pluginId: number;
  onSuccess: () => void;
}

export function PublishFromReleaseDialog({
  open,
  onOpenChange,
  pluginId,
  onSuccess,
}: PublishFromReleaseDialogProps) {
  const [releaseUrl, setReleaseUrl] = useState("");
  const [channel, setChannel] = useState<"stable" | "beta">("stable");
  const [changelog, setChangelog] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [loadingCandidates, setLoadingCandidates] = useState(false);
  const [candidates, setCandidates] = useState<VersionReleaseCandidate[]>([]);
  const [candidateError, setCandidateError] = useState("");
  const [validationError, setValidationError] = useState("");

  const packageCandidates = candidates.filter((item) => item.has_package_asset);

  function reset() {
    setReleaseUrl("");
    setChannel("stable");
    setChangelog("");
    setSubmitting(false);
    setLoadingCandidates(false);
    setCandidates([]);
    setCandidateError("");
    setValidationError("");
  }

  async function loadReleaseCandidates() {
    setLoadingCandidates(true);
    setCandidateError("");
    try {
      const items = await versionsApi.releaseCandidates(pluginId);
      setCandidates(items);
      const firstPackageRelease = items.find((item) => item.has_package_asset);
      if (firstPackageRelease) {
        setReleaseUrl(firstPackageRelease.release_url);
        if (firstPackageRelease.prerelease) {
          setChannel("beta");
        }
      } else if (items.length > 0) {
        setCandidateError("找到了 GitHub Release，但没有包含 .neko-plugin / .neko-bundle 的资产。");
      } else {
        setCandidateError("没有找到 GitHub Release。请先推送 v* 标签并等待 release.yml 完成。");
      }
    } catch (err) {
      const message = getVersionErrorMessage(err, "自动获取 GitHub Release 失败");
      setCandidateError(message);
      reportError(err, {
        title: "自动获取 GitHub Release 失败",
        severity: "warn",
        context: {
          module: "publishFromRelease",
          action: "releaseCandidates",
          pluginId,
        },
      });
    } finally {
      setLoadingCandidates(false);
    }
  }

  useEffect(() => {
    if (open) {
      void loadReleaseCandidates();
    }
  }, [open, pluginId]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!RELEASE_URL_PATTERN.test(releaseUrl.trim())) {
      setValidationError(
        "release_url 必须是 https://github.com/<owner>/<repo>/releases/tag/<tag> 或 /releases/<id>",
      );
      return;
    }
    setValidationError("");
    setSubmitting(true);
    try {
      const created = await versionsApi.publishFromRelease(pluginId, {
        release_url: releaseUrl.trim(),
        channel,
        changelog: changelog.trim() || undefined,
      });
      toast.success(`已发布 v${created.version}（${created.channel}）`);
      reset();
      onSuccess();
    } catch (err) {
      const message = getVersionErrorMessage(err, "发布失败");
      toast.error(message);
      reportError(err, {
        title: "发布版本失败",
        severity: "warn",
        context: {
          module: "publishFromRelease",
          action: "submit",
          pluginId,
          channel,
        },
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next && !submitting) reset();
        onOpenChange(next);
      }}
    >
      <DialogContent className="bg-[#1A1A2E] border-slate-800 text-slate-200">
        <DialogHeader>
          <DialogTitle>发布新版本</DialogTitle>
          <DialogDescription className="text-slate-400">
            后端会从 GitHub release 拉取插件包，自动校验仓库归属与字节级 sha256
            后入库。作者无法手动填写 sha256。
          </DialogDescription>
        </DialogHeader>

        <form className="space-y-4" onSubmit={onSubmit}>
          <div className="space-y-1.5">
            <Label htmlFor="release_url">GitHub Release URL</Label>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Select
                value={packageCandidates.find((item) => item.release_url === releaseUrl)?.release_url ?? ""}
                onValueChange={(value) => {
                  const selected = candidates.find((item) => item.release_url === value);
                  setReleaseUrl(value);
                  if (selected?.prerelease) {
                    setChannel("beta");
                  }
                }}
                disabled={loadingCandidates || packageCandidates.length === 0}
              >
                <SelectTrigger className="bg-[#0F0F1A] border-slate-700 text-slate-200 sm:w-[220px]">
                  <SelectValue
                    placeholder={loadingCandidates ? "正在获取 Release..." : "选择 Release"}
                  />
                </SelectTrigger>
                <SelectContent>
                  {packageCandidates.map((item) => (
                    <SelectItem key={item.release_url} value={item.release_url}>
                      {item.tag_name}{item.prerelease ? "（beta）" : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                type="button"
                variant="outline"
                onClick={() => loadReleaseCandidates()}
                disabled={loadingCandidates || submitting}
                className="border-slate-700 text-slate-300 hover:bg-slate-800"
              >
                {loadingCandidates ? "获取中..." : "重新获取"}
              </Button>
            </div>
            <Input
              id="release_url"
              type="url"
              required
              placeholder="https://github.com/your/plugin/releases/tag/v1.2.0"
              value={releaseUrl}
              onChange={(e) => setReleaseUrl(e.target.value)}
              className="bg-[#0F0F1A] border-slate-700 text-slate-200"
            />
            {candidateError && (
              <p className="text-xs text-amber-300">{candidateError}</p>
            )}
            {packageCandidates.length > 0 && !candidateError && (
              <p className="text-xs text-slate-500">
                已自动读取 {packageCandidates.length} 个包含插件包资产的 GitHub Release，可直接选择或手动修改 URL。
              </p>
            )}
            {validationError && (
              <p className="text-xs text-red-400">{validationError}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label>Channel</Label>
            <Select value={channel} onValueChange={(v) => setChannel(v as "stable" | "beta")}>
              <SelectTrigger className="bg-[#0F0F1A] border-slate-700 text-slate-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="stable">stable（正式版，默认）</SelectItem>
                <SelectItem value="beta">beta（测试版）</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="changelog">Changelog（可选，支持 Markdown）</Label>
            <Textarea
              id="changelog"
              value={changelog}
              onChange={(e) => setChangelog(e.target.value)}
              placeholder="本次更新内容…"
              className="bg-[#0F0F1A] border-slate-700 text-slate-200 min-h-[100px]"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={submitting}
              className="border-slate-700 text-slate-300 hover:bg-slate-800"
            >
              取消
            </Button>
            <Button
              type="submit"
              disabled={submitting}
              className="bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {submitting ? "拉取并发布中..." : "发布"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
