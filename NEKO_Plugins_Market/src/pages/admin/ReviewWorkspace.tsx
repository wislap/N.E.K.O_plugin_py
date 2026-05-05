import { useMemo, useState } from "react";
import {
  CheckCircle2,
  CircleDot,
  ExternalLink,
  GitBranch,
  MessageSquarePlus,
  RefreshCw,
  Search,
  ShieldAlert,
  Timer,
  XCircle
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import type { ReviewComment, ReviewCommentPayload, ReviewSubmission } from "@/services/adminApi";
import { notifySuccess, reportError } from "@/lib/error-reporting";
import {
  REVIEW_WORKSPACE_LIST_PARAMS,
  usePrefetchReviewSubmission,
  useReviewMutations,
  useReviewSubmission,
  useReviewSubmissions
} from "@/admin/reviewQueries";

const SELECTED_SUBMISSION_STORAGE_KEY = "neko.admin.review.selectedSubmissionId";

const severityOptions: Array<{ value: ReviewComment["severity"]; label: string }> = [
  { value: "critical", label: "Critical" },
  { value: "major", label: "Major" },
  { value: "minor", label: "Minor" },
  { value: "nitpick", label: "Nitpick" }
];

const areaOptions: Array<{ value: ReviewComment["target_area"]; label: string }> = [
  { value: "ownership", label: "所有权" },
  { value: "metadata", label: "元数据" },
  { value: "code", label: "代码" },
  { value: "security", label: "安全" },
  { value: "packaging", label: "打包" },
  { value: "license", label: "协议" },
  { value: "docs", label: "文档" },
  { value: "release", label: "发布" },
  { value: "other", label: "其他" }
];

function statusLabel(status: ReviewSubmission["status"]) {
  if (status === "submitted") return "待审核";
  if (status === "in_review") return "审核中";
  if (status === "closed") return "已关闭";
  return "草稿";
}

function severityClass(severity: ReviewComment["severity"]) {
  if (severity === "critical") return "border-red-500/30 bg-red-500/10 text-red-300";
  if (severity === "major") return "border-orange-500/30 bg-orange-500/10 text-orange-300";
  if (severity === "minor") return "border-blue-500/30 bg-blue-500/10 text-blue-300";
  return "border-slate-500/30 bg-slate-500/10 text-slate-300";
}

function ReviewQueueItem({
  submission,
  active,
  onPreview,
  onSelect
}: {
  submission: ReviewSubmission;
  active: boolean;
  onPreview: () => void;
  onSelect: () => void;
}) {
  const snapshot = submission.current_snapshot;
  return (
    <button
      type="button"
      aria-pressed={active}
      onFocus={onPreview}
      onMouseEnter={onPreview}
      onClick={onSelect}
      className={`w-full rounded-lg border p-3 text-left transition-colors ${
        active ? "border-primary bg-primary/10" : "border-border bg-card hover:bg-muted/50"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate font-medium">{snapshot?.plugin_name ?? `提交 #${submission.id}`}</div>
          <div className="mt-1 truncate text-xs text-muted-foreground">{snapshot?.repo_name ?? snapshot?.repo_url}</div>
        </div>
        <Badge variant="outline" className="shrink-0">
          {statusLabel(submission.status)}
        </Badge>
      </div>
      <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
        <span>未解决 {submission.review_counts.unresolved}</span>
        {submission.review_counts.critical > 0 && <span className="text-red-300">Critical {submission.review_counts.critical}</span>}
        {submission.review_counts.major > 0 && <span className="text-orange-300">Major {submission.review_counts.major}</span>}
      </div>
    </button>
  );
}

export default function ReviewWorkspace() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<"all" | ReviewSubmission["status"]>("all");
  const [selectedId, setSelectedId] = useState<number | null>(() => {
    if (typeof window === "undefined") return null;
    const storedValue = Number(window.localStorage.getItem(SELECTED_SUBMISSION_STORAGE_KEY));
    return Number.isFinite(storedValue) && storedValue > 0 ? storedValue : null;
  });
  const [commentForm, setCommentForm] = useState<ReviewCommentPayload>({
    severity: "minor",
    target_area: "metadata",
    target_ref: "",
    body: ""
  });
  const [decisionSummary, setDecisionSummary] = useState("");

  const listParams = useMemo(() => {
    const trimmedQuery = q.trim();
    if (!trimmedQuery && status === "all") {
      return REVIEW_WORKSPACE_LIST_PARAMS;
    }

    return {
      q: trimmedQuery || undefined,
      status: status === "all" ? undefined : status,
      page_size: 50
    };
  }, [q, status]);

  const submissionsQuery = useReviewSubmissions(listParams);
  const submissions = useMemo(() => submissionsQuery.data?.items ?? [], [submissionsQuery.data?.items]);
  const prefetchSubmission = usePrefetchReviewSubmission();
  const activeSelectedId = selectedId && submissions.some((submission) => submission.id === selectedId)
    ? selectedId
    : submissions[0]?.id ?? null;
  const detailQuery = useReviewSubmission(activeSelectedId);
  const detail = detailQuery.data ?? null;
  const mutations = useReviewMutations(activeSelectedId);

  const currentCase = detail?.review_cases.find((item) => item.id === detail.current_review_case_id)
    ?? detail?.review_cases.find((item) => item.status === "open")
    ?? null;
  const comments = currentCase?.comments ?? [];
  const snapshot = detail?.current_snapshot;
  const isBusy = Object.values(mutations).some((mutation) => mutation.isPending);

  const runAction = async (action: () => Promise<unknown>, success: string) => {
    try {
      await action();
      notifySuccess(success);
    } catch (error) {
      reportError(error, {
        title: "审核操作失败",
        userMessage: "审核操作没有成功，请检查权限或后端日志。",
        context: { module: "admin.review.workspace" }
      });
    }
  };

  const selectSubmission = (submissionId: number) => {
    setSelectedId(submissionId);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(SELECTED_SUBMISSION_STORAGE_KEY, String(submissionId));
    }
  };

  const submitComment = () => {
    if (!currentCase || !commentForm.body.trim()) return;
    runAction(
      () => mutations.addComment.mutateAsync({
        caseId: currentCase.id,
        payload: {
          ...commentForm,
          target_ref: commentForm.target_ref?.trim() || null,
          body: commentForm.body.trim()
        }
      }),
      "审核意见已添加"
    );
    setCommentForm((current) => ({ ...current, body: "", target_ref: "" }));
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] min-h-[680px] flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">审核工作区</h2>
          <p className="text-muted-foreground">左侧选择申请，中间查看快照，右侧处理结构化审核意见。</p>
        </div>
        <Button variant="outline" onClick={() => submissionsQuery.refetch()} disabled={submissionsQuery.isFetching}>
          <RefreshCw className={`mr-2 h-4 w-4 ${submissionsQuery.isFetching ? "animate-spin" : ""}`} />
          同步
        </Button>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-[320px_minmax(0,1fr)_360px] gap-4">
        <aside className="flex min-h-0 flex-col rounded-lg border bg-card">
          <div className="space-y-3 border-b p-3">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input value={q} onChange={(event) => setQ(event.target.value)} placeholder="搜索插件、仓库..." className="pl-9" />
            </div>
            <Select value={status} onValueChange={(value) => setStatus(value as typeof status)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部开放申请</SelectItem>
                <SelectItem value="submitted">待审核</SelectItem>
                <SelectItem value="in_review">审核中</SelectItem>
                <SelectItem value="closed">已关闭</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-3">
            {submissionsQuery.isLoading && Array.from({ length: 6 }).map((_, index) => (
              <Skeleton key={index} className="h-24 rounded-lg" />
            ))}
            {!submissionsQuery.isLoading && submissions.length === 0 && (
              <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                没有匹配的审核申请
              </div>
            )}
            {submissions.map((submission) => (
              <ReviewQueueItem
                key={submission.id}
                submission={submission}
                active={submission.id === activeSelectedId}
                onPreview={() => prefetchSubmission(submission.id)}
                onSelect={() => selectSubmission(submission.id)}
              />
            ))}
          </div>
        </aside>

        <section className="min-h-0 overflow-y-auto rounded-lg border bg-card">
          {!detail && detailQuery.isLoading && (
            <div className="space-y-4 p-5">
              <Skeleton className="h-8 w-64" />
              <Skeleton className="h-40 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          )}
          {!detail && !detailQuery.isLoading && (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              请选择一个审核申请
            </div>
          )}
          {detail && (
            <div className="space-y-4 p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <h3 className="truncate text-xl font-semibold">{snapshot?.plugin_name ?? `提交 #${detail.id}`}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{snapshot?.short_description ?? "暂无简介"}</p>
                </div>
                <Badge variant="outline">{statusLabel(detail.status)}</Badge>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <GitBranch className="h-4 w-4" />
                    GitHub 快照
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <Label className="text-muted-foreground">仓库</Label>
                      <div className="mt-1 truncate">{snapshot?.repo_owner}/{snapshot?.repo_name}</div>
                    </div>
                    <div>
                      <Label className="text-muted-foreground">提交</Label>
                      <div className="mt-1 truncate font-mono">{snapshot?.resolved_commit ?? snapshot?.submitted_ref ?? "-"}</div>
                    </div>
                  </div>
                  {snapshot?.repo_url && (
                    <Button asChild variant="outline" size="sm">
                      <a href={snapshot.repo_url} target="_blank" rel="noreferrer">
                        <ExternalLink className="mr-2 h-4 w-4" />
                        打开 GitHub
                      </a>
                    </Button>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <ShieldAlert className="h-4 w-4" />
                    阻塞状态
                  </CardTitle>
                </CardHeader>
                <CardContent className="grid gap-3 sm:grid-cols-4">
                  <div className="rounded-md border p-3">
                    <div className="text-xs text-muted-foreground">Critical</div>
                    <div className="text-2xl font-semibold text-red-300">{detail.review_counts.critical}</div>
                  </div>
                  <div className="rounded-md border p-3">
                    <div className="text-xs text-muted-foreground">Major</div>
                    <div className="text-2xl font-semibold text-orange-300">{detail.review_counts.major}</div>
                  </div>
                  <div className="rounded-md border p-3">
                    <div className="text-xs text-muted-foreground">Minor</div>
                    <div className="text-2xl font-semibold">{detail.review_counts.minor}</div>
                  </div>
                  <div className="rounded-md border p-3">
                    <div className="text-xs text-muted-foreground">未解决</div>
                    <div className="text-2xl font-semibold">{detail.review_counts.unresolved}</div>
                  </div>
                </CardContent>
              </Card>

              <div className="flex flex-wrap gap-2">
                {detail.status === "submitted" && (
                  <Button
                    disabled={isBusy}
                    onClick={() => runAction(() => mutations.startReview.mutateAsync({ submissionId: detail.id }), "已进入审核")}
                  >
                    <Timer className="mr-2 h-4 w-4" />
                    开始审核
                  </Button>
                )}
                {currentCase && (
                  <>
                    <Button
                      disabled={isBusy}
                      onClick={() => runAction(
                        () => mutations.approveCase.mutateAsync({ caseId: currentCase.id, summary: decisionSummary, force: true }),
                        "审核已通过"
                      )}
                    >
                      <CheckCircle2 className="mr-2 h-4 w-4" />
                      通过
                    </Button>
                    <Button
                      variant="outline"
                      disabled={isBusy}
                      onClick={() => runAction(
                        () => mutations.rejectCase.mutateAsync({ caseId: currentCase.id, summary: decisionSummary }),
                        "审核已拒绝"
                      )}
                    >
                      <XCircle className="mr-2 h-4 w-4" />
                      驳回
                    </Button>
                  </>
                )}
              </div>
              {currentCase && (
                <Textarea
                  value={decisionSummary}
                  onChange={(event) => setDecisionSummary(event.target.value)}
                  placeholder="审核结论摘要..."
                  rows={3}
                />
              )}
            </div>
          )}
        </section>

        <aside className="flex min-h-0 flex-col rounded-lg border bg-card">
          <div className="border-b p-4">
            <h3 className="font-semibold">审核评论</h3>
            <p className="text-sm text-muted-foreground">按严重程度标记问题，resolve 后解除阻塞。</p>
          </div>
          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
            {!currentCase && (
              <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                开始审核后可以添加评论
              </div>
            )}
            {comments.map((comment) => (
              <Card key={comment.id}>
                <CardHeader className="space-y-2 pb-2">
                  <div className="flex items-center justify-between gap-2">
                    <Badge variant="outline" className={severityClass(comment.severity)}>
                      {comment.severity}
                    </Badge>
                    <Badge variant={comment.is_resolved ? "secondary" : "outline"}>
                      {comment.is_resolved ? "已解决" : "未解决"}
                    </Badge>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {comment.target_area}{comment.target_ref ? ` · ${comment.target_ref}` : ""}
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="whitespace-pre-wrap text-sm">{comment.body}</p>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={isBusy}
                    onClick={() => runAction(
                      () => comment.is_resolved
                        ? mutations.reopenComment.mutateAsync(comment.id)
                        : mutations.resolveComment.mutateAsync(comment.id),
                      comment.is_resolved ? "评论已重新打开" : "评论已解决"
                    )}
                  >
                    <CircleDot className="mr-2 h-4 w-4" />
                    {comment.is_resolved ? "重新打开" : "标记解决"}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
          {currentCase && (
            <div className="space-y-3 border-t p-4">
              <div className="grid grid-cols-2 gap-2">
                <Select
                  value={commentForm.severity}
                  onValueChange={(value) => setCommentForm((current) => ({ ...current, severity: value as ReviewComment["severity"] }))}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {severityOptions.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}
                  </SelectContent>
                </Select>
                <Select
                  value={commentForm.target_area}
                  onValueChange={(value) => setCommentForm((current) => ({ ...current, target_area: value as ReviewComment["target_area"] }))}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {areaOptions.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <Input
                value={commentForm.target_ref ?? ""}
                onChange={(event) => setCommentForm((current) => ({ ...current, target_ref: event.target.value }))}
                placeholder="目标文件/字段，如 plugin.toml"
              />
              <Textarea
                value={commentForm.body}
                onChange={(event) => setCommentForm((current) => ({ ...current, body: event.target.value }))}
                placeholder="添加审核意见..."
                rows={4}
              />
              <Button className="w-full" disabled={isBusy || !commentForm.body.trim()} onClick={submitComment}>
                <MessageSquarePlus className="mr-2 h-4 w-4" />
                添加评论
              </Button>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
