import { useEffect, useState } from "react";
import { RefreshCw, Settings as SettingsIcon, Wand2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { adminApi, type SystemSetting } from "@/services/api";

export default function AdminSettings() {
  const [settings, setSettings] = useState<SystemSetting[]>([]);
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  const fetchSettings = async () => {
    setIsLoading(true);
    setMessage("");
    try {
      const data = await adminApi.getSettings();
      setSettings(data.settings);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "读取系统设置失败");
      setSettings([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleInit = async () => {
    try {
      const result = await adminApi.initSettings();
      setMessage(result.message);
      await fetchSettings();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "初始化失败");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">系统设置</h2>
          <p className="text-muted-foreground">查看和初始化后端系统配置</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchSettings}>
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={handleInit}>
            <Wand2 className="h-4 w-4 mr-2" />
            初始化默认设置
          </Button>
        </div>
      </div>

      {message && (
        <Alert>
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <SettingsIcon className="h-5 w-5" />
            配置项
          </CardTitle>
          <CardDescription>敏感配置会由后端遮蔽显示</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="py-8 text-center text-muted-foreground">加载中...</div>
          ) : settings.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">暂无配置项</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>键名</TableHead>
                  <TableHead>值</TableHead>
                  <TableHead>说明</TableHead>
                  <TableHead>更新时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {settings.map((setting) => (
                  <TableRow key={setting.key}>
                    <TableCell className="font-medium">{setting.key}</TableCell>
                    <TableCell className="max-w-xs truncate">{String(setting.value ?? "")}</TableCell>
                    <TableCell className="text-muted-foreground">{setting.description || "-"}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {setting.updated_at ? new Date(setting.updated_at).toLocaleString() : "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
