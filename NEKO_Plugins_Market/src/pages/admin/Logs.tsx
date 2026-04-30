import { useEffect, useState } from "react";
import { FileText, RefreshCw, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { adminApi, type LogStats } from "@/services/api";

const logTypes = [
  { value: "all", label: "全部日志" },
  { value: "review", label: "审核日志" },
  { value: "sandbox", label: "沙箱日志" },
  { value: "permission", label: "权限审计日志" }
];

export default function AdminLogs() {
  const [stats, setStats] = useState<LogStats>({});
  const [retention, setRetention] = useState<Record<string, number>>({});
  const [logType, setLogType] = useState("all");
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isCleaning, setIsCleaning] = useState(false);

  const fetchLogs = async () => {
    setIsLoading(true);
    setMessage("");
    try {
      const [statsData, retentionData] = await Promise.all([
        adminApi.getLogStats(),
        adminApi.getRetentionSettings().catch(() => ({}))
      ]);
      setStats(statsData);
      setRetention(retentionData);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "读取日志信息失败");
      setStats({});
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const handleCleanup = async () => {
    setIsCleaning(true);
    setMessage("");
    try {
      const result = await adminApi.cleanupLogs(logType);
      setMessage(`${result.message}，删除 ${result.deleted_count} 条记录。`);
      await fetchLogs();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "清理失败");
    } finally {
      setIsCleaning(false);
    }
  };

  const statItems = Object.entries(stats).filter(([, value]) => typeof value === "number");
  const retentionItems = Object.entries(retention);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">日志查看</h2>
          <p className="text-muted-foreground">查看日志统计并执行保留期清理</p>
        </div>
        <Button variant="outline" onClick={fetchLogs}>
          <RefreshCw className="h-4 w-4 mr-2" />
          刷新
        </Button>
      </div>

      {message && (
        <Alert>
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {isLoading ? (
          <Card className="md:col-span-2 lg:col-span-4">
            <CardContent className="py-8 text-center text-muted-foreground">加载中...</CardContent>
          </Card>
        ) : statItems.length === 0 ? (
          <Card className="md:col-span-2 lg:col-span-4">
            <CardContent className="py-8 text-center text-muted-foreground">暂无日志统计</CardContent>
          </Card>
        ) : (
          statItems.map(([key, value]) => (
            <Card key={key}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{key}</CardTitle>
                <FileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{value}</div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>手动清理</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 sm:flex-row">
            <Select value={logType} onValueChange={setLogType}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {logTypes.map((item) => (
                  <SelectItem key={item.value} value={item.value}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="destructive" onClick={handleCleanup} disabled={isCleaning}>
              <Trash2 className="h-4 w-4 mr-2" />
              {isCleaning ? "清理中..." : "清理日志"}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>保留策略</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {retentionItems.length === 0 ? (
              <div className="text-sm text-muted-foreground">暂无保留策略数据</div>
            ) : (
              retentionItems.map(([key, value]) => (
                <div key={key} className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{key}</span>
                  <span className="font-medium">{value}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
