import { useEffect, useState } from "react";
import { Mail, Save, Send, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { adminApi, type SMTPSettings } from "@/services/adminApi";
import { getErrorMessage, notifySuccess, reportError } from "@/lib/error-reporting";

const defaultSettings: SMTPSettings = {
  host: "",
  port: 587,
  user: "",
  password: "",
  tls: true,
  from_email: "",
  enabled: false
};

export default function AdminSMTP() {
  const [settings, setSettings] = useState<SMTPSettings>(defaultSettings);
  const [testEmail, setTestEmail] = useState("");
  const [message, setMessage] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);

  useEffect(() => {
    adminApi.getSMTPSettings()
      .then((data) => setSettings({ ...data, password: "" }))
      .catch((error) => {
        const message = "暂时无法读取 SMTP 设置，请确认后端已启动且账号具备权限。";
        setMessage(message);
        reportError(error, {
          title: "读取 SMTP 设置失败",
          userMessage: message,
          context: { module: "admin.smtp", action: "getSMTPSettings" }
        });
      });
  }, []);

  const updateField = <K extends keyof SMTPSettings>(key: K, value: SMTPSettings[K]) => {
    setSettings((current) => ({ ...current, [key]: value }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    setMessage("");
    try {
      await adminApi.updateSMTPSettings(settings);
      setMessage("SMTP 设置已保存。");
      notifySuccess("SMTP 设置已保存");
    } catch (error) {
      const message = getErrorMessage(error, "保存失败");
      setMessage(message);
      reportError(error, {
        title: "保存 SMTP 设置失败",
        userMessage: message,
        context: { module: "admin.smtp", action: "updateSMTPSettings" }
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleTest = async () => {
    if (!testEmail) return;
    setIsTesting(true);
    setMessage("");
    try {
      const result = await adminApi.testSMTP(testEmail);
      setMessage(result.message);
      notifySuccess("SMTP 测试完成", result.message);
    } catch (error) {
      const message = getErrorMessage(error, "测试邮件发送失败");
      setMessage(message);
      reportError(error, {
        title: "SMTP 测试失败",
        userMessage: message,
        context: { module: "admin.smtp", action: "testSMTP", testEmail }
      });
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">SMTP 设置</h2>
        <p className="text-muted-foreground">配置审核通知和系统邮件的发送服务</p>
      </div>

      {message && (
        <Alert>
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mail className="h-5 w-5" />
              邮件服务配置
            </CardTitle>
            <CardDescription>密码留空时后端会保留原配置</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="smtp-host">SMTP 主机</Label>
                <Input id="smtp-host" value={settings.host} onChange={(event) => updateField("host", event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="smtp-port">端口</Label>
                <Input id="smtp-port" type="number" value={settings.port} onChange={(event) => updateField("port", Number(event.target.value))} />
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="smtp-user">用户名</Label>
                <Input id="smtp-user" value={settings.user} onChange={(event) => updateField("user", event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="smtp-password">密码</Label>
                <Input id="smtp-password" type="password" value={settings.password ?? ""} onChange={(event) => updateField("password", event.target.value)} />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="smtp-from">发件人邮箱</Label>
              <Input id="smtp-from" type="email" value={settings.from_email} onChange={(event) => updateField("from_email", event.target.value)} />
            </div>
            <div className="flex flex-wrap gap-6">
              <label className="flex items-center gap-3">
                <Switch checked={settings.tls} onCheckedChange={(checked) => updateField("tls", checked)} />
                <span className="text-sm">启用 TLS</span>
              </label>
              <label className="flex items-center gap-3">
                <Switch checked={settings.enabled} onCheckedChange={(checked) => updateField("enabled", checked)} />
                <span className="text-sm">启用邮件服务</span>
              </label>
            </div>
            <Button onClick={handleSave} disabled={isSaving}>
              <Save className="h-4 w-4 mr-2" />
              {isSaving ? "保存中..." : "保存设置"}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5" />
              发送测试
            </CardTitle>
            <CardDescription>用于验证当前 SMTP 配置是否可用</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="test-email">测试收件人</Label>
              <Input id="test-email" type="email" value={testEmail} onChange={(event) => setTestEmail(event.target.value)} />
            </div>
            <Button variant="outline" onClick={handleTest} disabled={isTesting || !testEmail} className="w-full">
              <Send className="h-4 w-4 mr-2" />
              {isTesting ? "发送中..." : "发送测试邮件"}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
