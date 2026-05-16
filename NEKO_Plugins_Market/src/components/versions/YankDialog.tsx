import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { getVersionErrorMessage, versionsApi } from "@/services/versions";
import type { PluginVersion } from "@/services/types";
import { reportError } from "@/lib/error-reporting";

interface YankDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  pluginId: number;
  version: PluginVersion;
  /** 当前操作者是 admin 但不是作者时，文案改为"管理员撤回" */
  adminAction: boolean;
  onSuccess: () => void;
}

export function YankDialog({
  open,
  onOpenChange,
  pluginId,
  version,
  adminAction,
  onSuccess,
}: YankDialogProps) {
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = reason.trim();
    if (trimmed.length < 1 || trimmed.length > 500) {
      toast.error("撤回原因必须为 1-500 字符");
      return;
    }
    setSubmitting(true);
    try {
      const resp = await versionsApi.yank(pluginId, version.id, { reason: trimmed });
      toast.success(`已撤回 v${resp.yanked.version}`);
      if (resp.promoted) {
        toast.info(`已自动晋级 v${resp.promoted.version} 为 ${resp.promoted.channel} 最新版`);
      }
      setReason("");
      onSuccess();
    } catch (err) {
      const message = getVersionErrorMessage(err, "撤回失败");
      toast.error(message);
      reportError(err, {
        title: "撤回版本失败",
        severity: "warn",
        context: {
          module: "yankDialog",
          action: "submit",
          pluginId,
          versionId: version.id,
        },
      });
    } finally {
      setSubmitting(false);
    }
  }

  const title = adminAction
    ? `管理员撤回 v${version.version}`
    : `撤回 v${version.version}`;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[#1A1A2E] border-slate-800 text-slate-200">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription className="text-slate-400">
            撤回是单向操作，不可恢复。如果该版本是当前 latest，系统会自动晋级
            该 channel 中次新的非已撤回版本（若不存在则该 channel 暂无 latest）。
          </DialogDescription>
        </DialogHeader>
        <form className="space-y-4" onSubmit={onSubmit}>
          <div className="space-y-1.5">
            <Label htmlFor="yank_reason">撤回原因（1-500 字）</Label>
            <Textarea
              id="yank_reason"
              required
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={500}
              placeholder="例如：发现严重安全漏洞 / 包文件损坏 / 误发版"
              className="bg-[#0F0F1A] border-slate-700 text-slate-200 min-h-[100px]"
            />
            <p className="text-xs text-slate-500">{reason.trim().length} / 500</p>
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
              className="bg-red-500 text-white hover:bg-red-500/90"
            >
              {submitting ? "撤回中..." : "确认撤回"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
