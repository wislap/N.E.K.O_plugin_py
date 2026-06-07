import { useEffect, useMemo, useState } from "react";
import {
  Edit,
  Plus,
  Shield,
  Trash2,
  UserCog,
  Users
} from "lucide-react";
import { useAdminSession } from "@/admin/session";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { adminApi, type Permission, type Role } from "@/services/adminApi";
import { notifySuccess, reportError } from "@/lib/error-reporting";
import { toast } from "sonner";

const CATEGORY_LABELS: Record<string, string> = {
  system: "系统",
  plugin: "插件",
  ai: "AI"
};

type RoleForm = {
  code: string;
  name: string;
  description: string;
  level: number;
  is_active: boolean;
  permissions: string[];
};

function permissionLabel(permission: Permission) {
  return permission.name || permission.code;
}

export default function AdminPermissions() {
  const { permissions: sessionPermissions } = useAdminSession();
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [editForm, setEditForm] = useState<RoleForm>({
    code: "",
    name: "",
    description: "",
    level: 10,
    is_active: true,
    permissions: []
  });

  const currentLevel = sessionPermissions?.level ?? 0;
  const isSuperAdmin = Boolean(sessionPermissions?.is_super_admin || sessionPermissions?.is_admin);
  const maxEditableLevel = isSuperAdmin ? 999 : Math.max(0, currentLevel - 1);

  const permissionByCode = useMemo(() => {
    return new Map(permissions.map((permission) => [permission.code, permission]));
  }, [permissions]);

  const groupedPermissions = useMemo(() => {
    return permissions.reduce<Record<string, Permission[]>>((groups, permission) => {
      const category = permission.category || "other";
      groups[category] = groups[category] ?? [];
      groups[category].push(permission);
      return groups;
    }, {});
  }, [permissions]);

  useEffect(() => {
    fetchAccessData();
  }, []);

  const canManageRole = (role: Role) => {
    if (role.is_system) return false;
    if (isSuperAdmin) return true;
    return role.level < currentLevel;
  };

  const fetchAccessData = async () => {
    try {
      setIsLoading(true);
      const [roleData, permissionData] = await Promise.all([
        adminApi.getRoles(),
        adminApi.getPermissions()
      ]);
      setRoles(roleData);
      setPermissions(permissionData);
    } catch (error) {
      reportError(error, {
        title: "获取角色失败",
        userMessage: "无法加载角色列表，请检查权限。",
        context: { module: "admin.permissions", action: "fetchAccessData" }
      });
      setRoles([]);
      setPermissions([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = () => {
    setSelectedRole(null);
    setEditForm({
      code: "",
      name: "",
      description: "",
      level: Math.min(10, maxEditableLevel || 10),
      is_active: true,
      permissions: []
    });
    setIsEditOpen(true);
  };

  const handleEdit = (role: Role) => {
    if (!canManageRole(role)) return;
    setSelectedRole(role);
    setEditForm({
      code: role.code ?? "",
      name: role.name,
      description: role.description,
      level: role.level,
      is_active: role.is_active ?? true,
      permissions: role.permissions
    });
    setIsEditOpen(true);
  };

  const handleSave = async () => {
    const level = Number(editForm.level);
    if (!editForm.name.trim()) {
      toast.error("角色名称不能为空");
      return;
    }
    if (!isSuperAdmin && level >= currentLevel) {
      toast.error("角色等级必须低于当前用户等级");
      return;
    }

    try {
      const payload = {
        code: editForm.code.trim() || undefined,
        name: editForm.name.trim(),
        description: editForm.description.trim(),
        level,
        is_active: editForm.is_active,
        permissions: editForm.permissions
      };
      if (selectedRole) {
        await adminApi.updateRole(selectedRole.id, payload);
      } else {
        await adminApi.createRole(payload);
      }
      await fetchAccessData();
      setIsEditOpen(false);
      notifySuccess(selectedRole ? "角色已更新" : "角色已创建");
    } catch (error) {
      reportError(error, {
        title: "保存角色失败",
        userMessage: "角色保存失败，请检查权限配置。",
        context: { module: "admin.permissions", action: "saveRole", roleId: selectedRole?.id }
      });
    }
  };

  const handleDelete = async () => {
    if (!selectedRole || !canManageRole(selectedRole)) return;
    try {
      await adminApi.deleteRole(selectedRole.id);
      await fetchAccessData();
      setIsDeleteOpen(false);
      notifySuccess("角色已删除");
    } catch (error) {
      reportError(error, {
        title: "删除角色失败",
        userMessage: "角色删除失败，请检查权限或系统角色状态。",
        context: { module: "admin.permissions", action: "deleteRole", roleId: selectedRole.id }
      });
    }
  };

  const togglePermission = (permissionId: string) => {
    setEditForm((prev) => ({
      ...prev,
      permissions: prev.permissions.includes(permissionId)
        ? prev.permissions.filter((id) => id !== permissionId)
        : [...prev.permissions, permissionId]
    }));
  };

  const renderRolePermissions = (role: Role) => {
    if (role.permissions.length === 0) {
      return <span className="text-sm text-muted-foreground">无权限</span>;
    }
    const visiblePermissions = role.permissions.slice(0, 8);
    return (
      <>
        {visiblePermissions.map((permissionCode: string) => {
          const permission = permissionByCode.get(permissionCode);
          return (
            <Badge key={permissionCode} variant="outline" className="text-xs">
              {permission ? permissionLabel(permission) : permissionCode}
            </Badge>
          );
        })}
        {role.permissions.length > visiblePermissions.length && (
          <Badge variant="secondary" className="text-xs">
            +{role.permissions.length - visiblePermissions.length}
          </Badge>
        )}
      </>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">角色管理</h2>
          <p className="text-muted-foreground">角色决定后台权限，等级决定管理边界</p>
        </div>
        {maxEditableLevel > 0 && (
          <Button onClick={handleCreate}>
            <Plus className="h-4 w-4 mr-2" />
            新建角色
          </Button>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {isLoading ? (
          <div className="col-span-full text-center py-8">加载中...</div>
        ) : roles.length === 0 ? (
          <div className="col-span-full text-center py-8 text-muted-foreground">暂无角色</div>
        ) : (
          roles.map((role) => (
            <Card key={role.id}>
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="h-10 w-10 shrink-0 rounded-lg bg-primary/10 flex items-center justify-center">
                      <UserCog className="h-5 w-5 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <CardTitle className="truncate text-lg">{role.name}</CardTitle>
                      <CardDescription className="truncate">{role.code}</CardDescription>
                    </div>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    {canManageRole(role) && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleEdit(role)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                    )}
                    {canManageRole(role) && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          setSelectedRole(role);
                          setIsDeleteOpen(true);
                        }}
                      >
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                  <Badge variant="outline">等级 {role.level}</Badge>
                  <span className="inline-flex items-center gap-1">
                    <Users className="h-4 w-4" />
                    {role.user_count} 个用户
                  </span>
                  {role.is_system && <Badge variant="secondary">系统内置</Badge>}
                  {role.is_active === false && <Badge variant="destructive">停用</Badge>}
                </div>
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">权限</Label>
                  <div className="flex flex-wrap gap-1">
                    {renderRolePermissions(role)}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Shield className="h-5 w-5" />
            权限清单
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>权限</TableHead>
                <TableHead>分类</TableHead>
                <TableHead>代码</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {permissions.map((permission) => (
                <TableRow key={permission.code}>
                  <TableCell className="font-medium">{permissionLabel(permission)}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {CATEGORY_LABELS[permission.category] ?? permission.category}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {permission.code}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{selectedRole ? "编辑角色" : "新建角色"}</DialogTitle>
            <DialogDescription>配置角色、等级和权限</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 md:grid-cols-[1fr_160px]">
            <div className="space-y-2">
              <Label>角色名称</Label>
              <Input
                value={editForm.name}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                placeholder="审核员"
              />
            </div>
            <div className="space-y-2">
              <Label>等级</Label>
              <Input
                type="number"
                min={0}
                max={isSuperAdmin ? 999 : maxEditableLevel}
                value={editForm.level}
                onChange={(e) =>
                  setEditForm({ ...editForm, level: Number(e.target.value) })
                }
              />
            </div>
            {!selectedRole && (
              <div className="space-y-2 md:col-span-2">
                <Label>角色代码</Label>
                <Input
                  value={editForm.code}
                  onChange={(e) => setEditForm({ ...editForm, code: e.target.value })}
                  placeholder="reviewer"
                />
              </div>
            )}
            <div className="space-y-2 md:col-span-2">
              <Label>描述</Label>
              <Textarea
                value={editForm.description}
                onChange={(e) =>
                  setEditForm({ ...editForm, description: e.target.value })
                }
                rows={2}
              />
            </div>
            {selectedRole && (
              <div className="flex items-center justify-between md:col-span-2">
                <Label>启用角色</Label>
                <Switch
                  checked={editForm.is_active}
                  onCheckedChange={(checked) =>
                    setEditForm({ ...editForm, is_active: checked })
                  }
                />
              </div>
            )}
            <div className="space-y-2 md:col-span-2">
              <Label>权限</Label>
              <ScrollArea className="h-72 rounded-md border">
                <div className="space-y-4 p-4">
                  {Object.entries(groupedPermissions).map(([category, categoryPermissions]) => (
                    <div key={category} className="space-y-2">
                      <div className="text-sm font-medium">
                        {CATEGORY_LABELS[category] ?? category}
                      </div>
                      <div className="grid gap-2 md:grid-cols-2">
                        {categoryPermissions.map((permission) => (
                          <label
                            key={permission.code}
                            className="flex items-start gap-3 rounded-md border p-3"
                          >
                            <Checkbox
                              checked={editForm.permissions.includes(permission.code)}
                              onCheckedChange={() => togglePermission(permission.code)}
                            />
                            <span className="min-w-0">
                              <span className="block text-sm font-medium">
                                {permissionLabel(permission)}
                              </span>
                              <span className="block truncate font-mono text-xs text-muted-foreground">
                                {permission.code}
                              </span>
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave}>{selectedRole ? "保存" : "创建"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              确定要删除角色 "{selectedRole?.name}" 吗？此操作不可撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteOpen(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
