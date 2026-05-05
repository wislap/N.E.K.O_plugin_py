import { Archive, CheckCircle2, CircleSlash, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { ReviewSubmission } from "@/services/adminApi";
import { REVIEW_ARCHIVE_LIST_PARAMS, useReviewSubmissions } from "@/admin/reviewQueries";

function decisionLabel(decision: ReviewSubmission["decision"]) {
  if (decision === "approved") return "已通过";
  if (decision === "rejected") return "已拒绝";
  if (decision === "canceled") return "已取消";
  if (decision === "superseded") return "已替代";
  return "已关闭";
}

function decisionVariant(decision: ReviewSubmission["decision"]) {
  return decision === "approved" ? "default" : "secondary";
}

export default function ReviewArchive() {
  const { data, isLoading, isFetching } = useReviewSubmissions(REVIEW_ARCHIVE_LIST_PARAMS);
  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">审核归档</h2>
        <p className="text-muted-foreground">
          保留所有关闭后的审核申请，方便误操作恢复和后续追溯。
          {isFetching && !isLoading ? " 正在同步最新数据..." : ""}
        </p>
      </div>

      <div className="space-y-3">
        {isLoading && Array.from({ length: 4 }).map((_, index) => (
          <Card key={index}>
            <CardHeader>
              <Skeleton className="h-5 w-56" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-4 w-full max-w-xl" />
            </CardContent>
          </Card>
        ))}

        {!isLoading && items.length === 0 && (
          <Card>
            <CardContent className="flex items-center gap-3 py-8 text-muted-foreground">
              <Archive className="h-5 w-5" />
              暂无已归档的审核申请
            </CardContent>
          </Card>
        )}

        {!isLoading && items.map((item) => {
          const snapshot = item.current_snapshot;
          const isApproved = item.decision === "approved";
          const Icon = isApproved ? CheckCircle2 : CircleSlash;
          return (
            <Card key={item.id}>
              <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0">
                <div className="min-w-0">
                  <CardTitle className="truncate text-base">
                    {snapshot?.plugin_name ?? `提交 #${item.id}`}
                  </CardTitle>
                  <p className="mt-1 truncate text-sm text-muted-foreground">
                    {snapshot?.repo_url ?? "未记录仓库地址"}
                  </p>
                </div>
                <Badge variant={decisionVariant(item.decision)} className="gap-1">
                  <Icon className="h-3.5 w-3.5" />
                  {decisionLabel(item.decision)}
                </Badge>
              </CardHeader>
              <CardContent className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                <span>未解决评论 {item.review_counts.unresolved}</span>
                <span>关闭时间 {item.closed_at ? new Date(item.closed_at).toLocaleString() : "-"}</span>
                {snapshot?.repo_url && (
                  <Button asChild variant="ghost" size="sm" className="ml-auto gap-2">
                    <a href={snapshot.repo_url} target="_blank" rel="noreferrer">
                      <ExternalLink className="h-4 w-4" />
                      GitHub
                    </a>
                  </Button>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
