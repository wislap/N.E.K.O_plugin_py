import { useEffect, useState } from "react";
import { Edit, Layers3, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { adminApi, type ZoneAdminItem, type ZonePayload } from "@/services/adminApi";
import { notifySuccess, reportError } from "@/lib/error-reporting";

const emptyForm: ZonePayload = {
  name: "",
  slug: "",
  description: "",
  icon: "",
  color: "#8b5cf6",
  sort_order: 0
};

export default function AdminZones() {
  const [zones, setZones] = useState<ZoneAdminItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedZone, setSelectedZone] = useState<ZoneAdminItem | null>(null);
  const [form, setForm] = useState<ZonePayload>(emptyForm);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);

  useEffect(() => {
    fetchZones();
  }, []);

  const fetchZones = async () => {
    try {
      setIsLoading(true);
      const data = await adminApi.getAdminZones();
      setZones(data);
    } catch (error) {
      reportError(error, {
        title: "获取分区列表失败",
        userMessage: "无法加载分区列表，请稍后重试。",
        context: { module: "admin.zones", action: "fetchZones" }
      });
      setZones([]);
    } finally {
      setIsLoading(false);
    }
  };

  const openCreate = () => {
    setSelectedZone(null);
    setForm(emptyForm);
    setIsEditorOpen(true);
  };

  const openEdit = (zone: ZoneAdminItem) => {
    setSelectedZone(zone);
    setForm({
      name: zone.name,
      slug: zone.slug,
      description: zone.description ?? "",
      icon: zone.icon ?? "",
      color: zone.color ?? "#8b5cf6",
      sort_order: zone.sort_order
    });
    setIsEditorOpen(true);
  };

  const saveZone = async () => {
    const payload = {
      ...form,
      name: form.name.trim(),
      slug: form.slug.trim(),
      description: form.description?.trim() || null,
      icon: form.icon?.trim() || null,
      color: form.color?.trim() || null,
      sort_order: Number(form.sort_order) || 0
    };

    try {
      if (selectedZone) {
        await adminApi.updateZone(selectedZone.id, {
          name: payload.name,
          description: payload.description,
          icon: payload.icon,
          color: payload.color,
          sort_order: payload.sort_order
        });
      } else {
        await adminApi.createZone(payload);
      }
      setIsEditorOpen(false);
      await fetchZones();
      notifySuccess(selectedZone ? "分区已更新" : "分区已创建");
    } catch (error) {
      reportError(error, {
        title: "保存分区失败",
        userMessage: "分区保存失败，请检查名称、Slug 或权限。",
        context: { module: "admin.zones", action: "saveZone", zoneId: selectedZone?.id }
      });
    }
  };

  const deleteZone = async () => {
    if (!selectedZone) return;
    try {
      await adminApi.deleteZone(selectedZone.id);
      setIsDeleteOpen(false);
      await fetchZones();
      notifySuccess("分区已删除");
    } catch (error) {
      reportError(error, {
        title: "删除分区失败",
        userMessage: "分区删除失败，请检查权限或关联数据。",
        context: { module: "admin.zones", action: "deleteZone", zoneId: selectedZone.id }
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">分区管理</h2>
          <p className="text-muted-foreground">维护首页分区、配色和展示顺序</p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="mr-2 h-4 w-4" />
          新建分区
        </Button>
      </div>

      <Card>
        <CardContent className="pt-6">
          {isLoading ? (
            <div className="py-8 text-center">加载中...</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>分区</TableHead>
                  <TableHead>Slug</TableHead>
                  <TableHead>颜色</TableHead>
                  <TableHead>排序</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {zones.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="py-8 text-center">
                      暂无分区
                    </TableCell>
                  </TableRow>
                ) : (
                  zones.map((zone) => (
                    <TableRow key={zone.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                            <Layers3 className="h-4 w-4 text-primary" />
                          </div>
                          <div>
                            <div className="font-medium">{zone.name}</div>
                            <div className="max-w-md truncate text-sm text-muted-foreground">
                              {zone.description || "无描述"}
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-sm">{zone.slug}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span
                            className="h-4 w-4 rounded-full border"
                            style={{ backgroundColor: zone.color ?? "#8b5cf6" }}
                          />
                          <span className="font-mono text-sm">{zone.color ?? "-"}</span>
                        </div>
                      </TableCell>
                      <TableCell>{zone.sort_order}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button variant="ghost" size="icon" onClick={() => openEdit(zone)}>
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-red-500 hover:text-red-500"
                            onClick={() => {
                              setSelectedZone(zone);
                              setIsDeleteOpen(true);
                            }}
                          >
                            <Trash2 className="h-4 w-4" />
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

      <Dialog open={isEditorOpen} onOpenChange={setIsEditorOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{selectedZone ? "编辑分区" : "新建分区"}</DialogTitle>
            <DialogDescription>分区会影响首页入口和插件分区列表。</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>名称</Label>
                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>Slug</Label>
                <Input
                  value={form.slug}
                  disabled={Boolean(selectedZone)}
                  onChange={(e) => setForm({ ...form, slug: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>描述</Label>
              <Textarea value={form.description ?? ""} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-2">
                <Label>图标</Label>
                <Input value={form.icon ?? ""} onChange={(e) => setForm({ ...form, icon: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>颜色</Label>
                <Input value={form.color ?? ""} onChange={(e) => setForm({ ...form, color: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>排序</Label>
                <Input
                  type="number"
                  value={form.sort_order}
                  onChange={(e) => setForm({ ...form, sort_order: Number(e.target.value) })}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditorOpen(false)}>取消</Button>
            <Button onClick={saveZone} disabled={!form.name.trim() || !form.slug.trim()}>保存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除分区</DialogTitle>
            <DialogDescription>确定删除“{selectedZone?.name}”吗？</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteOpen(false)}>取消</Button>
            <Button variant="destructive" onClick={deleteZone}>删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
