import { useEffect, useMemo, useState } from "react";
import { CheckCircle, Copy, KeyRound, Plus, PowerOff, ShieldCheck } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { adminApi, type ServerKeyPair } from "@/services/adminApi";
import { getErrorMessage, notifySuccess, reportError } from "@/lib/error-reporting";

function formatDate(value?: string | null) {
  return value ? new Date(value).toLocaleString() : "-";
}

export default function AdminSignatures() {
  const [keys, setKeys] = useState<ServerKeyPair[]>([]);
  const [defaultKey, setDefaultKey] = useState<ServerKeyPair | null>(null);
  const [selectedKey, setSelectedKey] = useState<ServerKeyPair | null>(null);
  const [newKeyName, setNewKeyName] = useState("");
  const [setAsDefault, setSetAsDefault] = useState(true);
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isDeactivateOpen, setIsDeactivateOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const activeKeys = useMemo(() => keys.filter((key) => key.is_active), [keys]);

  useEffect(() => {
    fetchKeys();
  }, []);

  const fetchKeys = async () => {
    try {
      setIsLoading(true);
      setMessage("");
      const [keyList, currentDefault] = await Promise.all([
        adminApi.getSignatureKeys(),
        adminApi.getDefaultPublicKey().catch(() => null)
      ]);
      setKeys(keyList);
      setDefaultKey(currentDefault);
    } catch (error) {
      setKeys([]);
      setDefaultKey(null);
      const message = getErrorMessage(error, "读取签名密钥失败");
      setMessage(message);
      reportError(error, {
        title: "读取签名密钥失败",
        userMessage: message,
        context: { module: "admin.signatures", action: "fetchKeys" }
      });
    } finally {
      setIsLoading(false);
    }
  };

  const createKey = async () => {
    if (!newKeyName.trim()) return;
    try {
      setIsSaving(true);
      await adminApi.createSignatureKey(newKeyName.trim(), setAsDefault);
      setIsCreateOpen(false);
      setNewKeyName("");
      setSetAsDefault(true);
      await fetchKeys();
      setMessage("签名密钥已创建。");
      notifySuccess("签名密钥已创建");
    } catch (error) {
      const message = getErrorMessage(error, "创建签名密钥失败");
      setMessage(message);
      reportError(error, {
        title: "创建签名密钥失败",
        userMessage: message,
        context: { module: "admin.signatures", action: "createKey", keyName: newKeyName }
      });
    } finally {
      setIsSaving(false);
    }
  };

  const deactivateKey = async () => {
    if (!selectedKey) return;
    try {
      setIsSaving(true);
      await adminApi.deactivateSignatureKey(selectedKey.id);
      setIsDeactivateOpen(false);
      await fetchKeys();
      setMessage("签名密钥已停用。");
      notifySuccess("签名密钥已停用");
    } catch (error) {
      const message = getErrorMessage(error, "停用签名密钥失败");
      setMessage(message);
      reportError(error, {
        title: "停用签名密钥失败",
        userMessage: message,
        context: { module: "admin.signatures", action: "deactivateKey", keyId: selectedKey.id }
      });
    } finally {
      setIsSaving(false);
    }
  };

  const copyPublicKey = async (publicKey: string) => {
    try {
      await navigator.clipboard.writeText(publicKey);
      setMessage("公钥已复制。");
      notifySuccess("公钥已复制");
    } catch (error) {
      setMessage("复制失败，请手动选择公钥内容。");
      reportError(error, {
        severity: "warn",
        title: "复制公钥失败",
        userMessage: "复制失败，请手动选择公钥内容。",
        context: { module: "admin.signatures", action: "copyPublicKey" }
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">签名管理</h2>
          <p className="text-muted-foreground">管理插件代码签名使用的服务端密钥</p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          新建密钥
        </Button>
      </div>

      {message && (
        <Alert>
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5" />
              服务端密钥
            </CardTitle>
            <CardDescription>停用密钥不会删除历史签名记录</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="py-8 text-center">加载中...</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>创建时间</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {keys.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4} className="py-8 text-center">
                        暂无签名密钥
                      </TableCell>
                    </TableRow>
                  ) : (
                    keys.map((key) => (
                      <TableRow key={key.id}>
                        <TableCell>
                          <div className="font-medium">{key.name}</div>
                          <div className="text-xs text-muted-foreground">ID: {key.id}</div>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-2">
                            {key.is_active ? (
                              <Badge variant="outline" className="border-green-500/20 bg-green-500/10 text-green-500">
                                激活
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="border-red-500/20 bg-red-500/10 text-red-500">
                                已停用
                              </Badge>
                            )}
                            {key.is_default && (
                              <Badge className="bg-primary/10 text-primary hover:bg-primary/10">
                                默认
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatDate(key.created_at)}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button variant="ghost" size="icon" onClick={() => copyPublicKey(key.public_key)}>
                              <Copy className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="text-red-500 hover:text-red-500"
                              disabled={!key.is_active}
                              onClick={() => {
                                setSelectedKey(key);
                                setIsDeactivateOpen(true);
                              }}
                            >
                              <PowerOff className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5" />
              默认公钥
            </CardTitle>
            <CardDescription>客户端校验插件签名时会使用公开公钥</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border p-3">
                <div className="text-sm text-muted-foreground">激活密钥</div>
                <div className="mt-1 text-2xl font-bold">{activeKeys.length}</div>
              </div>
              <div className="rounded-lg border p-3">
                <div className="text-sm text-muted-foreground">全部密钥</div>
                <div className="mt-1 text-2xl font-bold">{keys.length}</div>
              </div>
            </div>

            {defaultKey ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  {defaultKey.name}
                </div>
                <Textarea value={defaultKey.public_key} readOnly className="h-56 font-mono text-xs" />
                <Button variant="outline" className="w-full" onClick={() => copyPublicKey(defaultKey.public_key)}>
                  <Copy className="mr-2 h-4 w-4" />
                  复制默认公钥
                </Button>
              </div>
            ) : (
              <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-600">
                暂无默认公钥，请创建密钥并设为默认。
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建签名密钥</DialogTitle>
            <DialogDescription>系统会生成新的密钥对，私钥仅保存在服务端。</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>密钥名称</Label>
              <Input value={newKeyName} onChange={(event) => setNewKeyName(event.target.value)} />
            </div>
            <label className="flex items-center justify-between rounded-lg border p-3">
              <span className="text-sm">设为默认密钥</span>
              <Switch checked={setAsDefault} onCheckedChange={setSetAsDefault} />
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateOpen(false)}>取消</Button>
            <Button onClick={createKey} disabled={isSaving || !newKeyName.trim()}>
              {isSaving ? "创建中..." : "创建"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isDeactivateOpen} onOpenChange={setIsDeactivateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>停用密钥</DialogTitle>
            <DialogDescription>
              确定停用“{selectedKey?.name}”吗？停用后它不能再用于新的插件签名。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeactivateOpen(false)}>取消</Button>
            <Button variant="destructive" onClick={deactivateKey} disabled={isSaving}>
              停用
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
