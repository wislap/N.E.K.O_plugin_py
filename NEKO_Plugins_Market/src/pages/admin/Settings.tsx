import { useEffect, useMemo, useState } from "react";
import {
  Check,
  EyeOff,
  RefreshCw,
  Save,
  Settings as SettingsIcon,
  Shield,
  Wand2
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { adminApi, type SystemSetting } from "@/services/api";

type EditableValue = string | number | boolean | null;

const groupLabels: Record<string, string> = {
  smtp: "邮件服务",
  general: "通用设置",
  security: "安全设置",
  review: "审核设置"
};

function normalizeValue(setting: SystemSetting): EditableValue {
  if (setting.value === "true") return true;
  if (setting.value === "false") return false;
  if (setting.key.endsWith("_port")) {
    return Number(setting.value || 0);
  }
  return setting.value ?? "";
}

function isBooleanSetting(setting: SystemSetting) {
  return setting.value === true || setting.value === false || setting.value === "true" || setting.value === "false";
}

function formatUpdatedAt(value?: string) {
  return value ? new Date(value).toLocaleString() : "-";
}

export default function AdminSettings() {
  const [settings, setSettings] = useState<SystemSetting[]>([]);
  const [drafts, setDrafts] = useState<Record<string, EditableValue>>({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);

  const fetchSettings = async () => {
    setIsLoading(true);
    setMessage("");
    setError("");
    try {
      const data = await adminApi.getSettings();
      const nextSettings = data.settings;
      setSettings(nextSettings);
      setDrafts(
        Object.fromEntries(
          nextSettings.map((setting) => [setting.key, normalizeValue(setting)])
        )
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "读取系统设置失败");
      setSettings([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const groupedSettings = useMemo(() => {
    return settings.reduce<Record<string, SystemSetting[]>>((groups, setting) => {
      const group = setting.group || "general";
      groups[group] = [...(groups[group] || []), setting];
      return groups;
    }, {});
  }, [settings]);

  const hasSettings = settings.length > 0;
  const encryptedCount = settings.filter((setting) => setting.is_encrypted).length;

  const handleInit = async () => {
    setMessage("");
    setError("");
    try {
      const result = await adminApi.initSettings();
      setMessage(result.message);
      await fetchSettings();
    } catch (err) {
      setError(err instanceof Error ? err.message : "初始化失败");
    }
  };

  const saveSetting = async (setting: SystemSetting) => {
    setMessage("");
    setError("");
    setSavingKey(setting.key);
    try {
      await adminApi.updateSetting(setting.key, drafts[setting.key]);
      setMessage(`${setting.key} 已保存`);
      await fetchSettings();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSavingKey(null);
    }
  };

  const setDraft = (key: string, value: EditableValue) => {
    setDrafts((current) => ({ ...current, [key]: value }));
  };

  const isDirty = (setting: SystemSetting) => {
    return drafts[setting.key] !== normalizeValue(setting);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-sm text-primary">
            <SettingsIcon className="h-4 w-4" />
            系统配置
          </div>
          <h2 className="text-2xl font-bold">系统设置</h2>
          <p className="text-muted-foreground">初始化、查看并编辑后端运行配置</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={fetchSettings} disabled={isLoading}>
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
          <Check className="h-4 w-4" />
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>配置项</CardDescription>
            <CardTitle>{settings.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>分组</CardDescription>
            <CardTitle>{Object.keys(groupedSettings).length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>敏感项</CardDescription>
            <CardTitle className="flex items-center gap-2">
              {encryptedCount}
              <Shield className="h-5 w-5 text-muted-foreground" />
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {isLoading ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">加载中...</CardContent>
        </Card>
      ) : !hasSettings ? (
        <Card>
          <CardContent className="py-10 text-center">
            <p className="text-muted-foreground">暂无配置项</p>
            <Button onClick={handleInit} className="mt-4">
              <Wand2 className="h-4 w-4 mr-2" />
              初始化默认设置
            </Button>
          </CardContent>
        </Card>
      ) : (
        Object.entries(groupedSettings).map(([group, items]) => (
          <Card key={group}>
            <CardHeader>
              <CardTitle>{groupLabels[group] || group}</CardTitle>
              <CardDescription>{items.length} 个配置项</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {items.map((setting) => {
                const draft = drafts[setting.key];
                const dirty = isDirty(setting);
                const isSaving = savingKey === setting.key;

                return (
                  <div
                    key={setting.key}
                    className="grid gap-3 rounded-lg border p-4 lg:grid-cols-[minmax(220px,1fr)_minmax(260px,1.2fr)_auto]"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium">{setting.key}</p>
                        {setting.is_encrypted && (
                          <Badge variant="outline" className="gap-1">
                            <EyeOff className="h-3 w-3" />
                            敏感
                          </Badge>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {setting.description || "暂无说明"}
                      </p>
                      <p className="mt-2 text-xs text-muted-foreground">
                        更新于 {formatUpdatedAt(setting.updated_at)}
                      </p>
                    </div>

                    <div className="flex items-center">
                      {isBooleanSetting(setting) ? (
                        <div className="flex items-center gap-3">
                          <Switch
                            checked={Boolean(draft)}
                            onCheckedChange={(checked) => setDraft(setting.key, checked)}
                          />
                          <span className="text-sm text-muted-foreground">
                            {draft ? "启用" : "停用"}
                          </span>
                        </div>
                      ) : (
                        <Input
                          type={setting.key.endsWith("_port") ? "number" : "text"}
                          value={String(draft ?? "")}
                          placeholder={setting.is_encrypted ? "留空或保持遮蔽表示不修改" : ""}
                          onChange={(event) =>
                            setDraft(
                              setting.key,
                              setting.key.endsWith("_port")
                                ? Number(event.target.value)
                                : event.target.value
                            )
                          }
                        />
                      )}
                    </div>

                    <div className="flex items-center justify-end gap-2">
                      {dirty && (
                        <Badge variant="secondary">未保存</Badge>
                      )}
                      <Button
                        size="sm"
                        onClick={() => saveSetting(setting)}
                        disabled={!dirty || isSaving}
                      >
                        <Save className="h-4 w-4 mr-2" />
                        {isSaving ? "保存中" : "保存"}
                      </Button>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );
}
