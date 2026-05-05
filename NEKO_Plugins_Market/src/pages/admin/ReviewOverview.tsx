import { Archive, CheckCircle2, ClipboardList, MessageSquareWarning, ShieldAlert, Timer } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useReviewOverview } from "@/admin/reviewQueries";

const overviewCards = [
  { key: "submitted", label: "待进入审核", icon: ClipboardList },
  { key: "in_review", label: "审核中", icon: Timer },
  { key: "unresolved_critical", label: "Critical 未解决", icon: ShieldAlert },
  { key: "unresolved_major", label: "Major 未解决", icon: MessageSquareWarning },
  { key: "approved", label: "已通过", icon: CheckCircle2 },
  { key: "closed", label: "已归档", icon: Archive }
] as const;

export default function ReviewOverview() {
  const { data: overview, isLoading, isFetching } = useReviewOverview();

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">审核总览</h2>
        <p className="text-muted-foreground">
          查看插件审核队列、风险评论和归档结果。
          {isFetching && !isLoading ? " 正在同步最新数据..." : ""}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {overviewCards.map((item) => {
          const Icon = item.icon;
          return (
            <Card key={item.key}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">{item.label}</CardTitle>
                <Icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <Skeleton className="h-9 w-20" />
                ) : (
                  <div className="text-3xl font-bold">{overview?.[item.key] ?? 0}</div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
