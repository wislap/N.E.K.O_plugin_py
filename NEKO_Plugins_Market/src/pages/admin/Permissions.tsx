import { useEffect, useState } from "react";
import {
  Shield,
  UserCog,
  Plus,
  Edit,
  Trash2,
  Users
} from "lucide-react";
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
import { Textarea } from "@/components/ui/textarea";
import { adminApi } from "@/services/api";

interface Permission {
  id: string;
  name: string;
  description: string;
}

interface Role {
  id: number;
  name: string;
  description: string;
  permissions: string[];
  user_count: number;
}

const AVAILABLE_PERMISSIONS: Permission[] = [
  { id: "plugin_review", name: "插件审核", description: "审核插件提交" },
  { id: "plugin_manage", name: "插件管理", description: "管理所有插件" },
  { id: "user_manage", name: "用户管理", description: "管理用户账户" },
  { id: "system_setting", name: "系统设置", description: "修改系统配置" },
  { id: "log_view", name: "日志查看", description: "查看系统日志" },
  { id: "smtp_setting", name: "SMTP设置", description: "配置邮件服务" }
];

export default function AdminPermissions() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [editForm, setEditForm] = useState({
    name: "",
    description: "",
    permissions: [] as string[]
  });

  useEffect(() => {
    fetchRoles();
  }, []);

  const fetchRoles = async () => {
    try {
      setIsLoading(true);
      const data = await adminApi.getRoles();
      setRoles(data);
    } catch (error) {
      console.error("获取角色列表失败:", error);
      // 使用默认数据
      setRoles([
        {
          id: 1,
          name: "超级管理员",
          description: "拥有所有权限",
          permissions: AVAILABLE_PERMISSIONS.map((p) => p.id),
          user_count: 1
        },
        {
          id: 2,
          name: "审核员",
          description: "负责插件审核",
          permissions: ["plugin_review", "log_view"],
          user_count: 2
        },
        {
          id: 3,
          name: "运营",
          description: "日常运营管理",
          permissions: ["user_manage", "plugin_manage", "log_view"],
          user_count: 3
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = () => {
    setSelectedRole(null);
    setEditForm({
      name: "",
      description: "",
      permissions: []
    });
    setIsEditOpen(true);
  };

  const handleEdit = (role: Role) => {
    setSelectedRole(role);
    setEditForm({
      name: role.name,
      description: role.description,
      permissions: role.permissions
    });
    setIsEditOpen(true);
  };

  const handleSave = async () => {
    try {
      if (selectedRole) {
        await adminApi.updateRole(selectedRole.id, editForm);
      } else {
        await adminApi.createRole(editForm);
      }
      fetchRoles();
      setIsEditOpen(false);
    } catch (error) {
      console.error("保存角色失败:", error);
    }
  };

  const handleDelete = async () => {
    if (!selectedRole) return;
    try {
      await adminApi.deleteRole(selectedRole.id);
      fetchRoles();
      setIsDeleteOpen(false);
    } catch (error) {
      console.error("删除角色失败:", error);
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">权限管理</h2>
          <p className="text-muted-foreground">管理角色和权限配置</p>
        </div>
        <Button onClick={handleCreate}>
          <Plus className="h-4 w-4 mr-2" />
          新建角色
        </Button>
      </div>

      {/* 角色列表 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {isLoading ? (
          <div className="col-span-full text-center py-8">加载中...</div>
        ) : (
          roles.map((role) => (
            <Card key={role.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                      <UserCog className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">{role.name}</CardTitle>
                      <CardDescription>{role.description}</CardDescription>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleEdit(role)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    {role.id > 3 && (
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
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Users className="h-4 w-4" />
                  {role.user_count} 个用户
                </div>
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">权限</Label>
                  <div className="flex flex-wrap gap-1">
                    {role.permissions.length === 0 ? (
                      <span className="text-sm text-muted-foreground">
                        无权限
                      </span>
                    ) : (
                      role.permissions.map((permId) => {
                        const perm = AVAILABLE_PERMISSIONS.find(
                          (p) => p.id === permId
                        );
                        return perm ? (
                          <Badge
                            key={permId}
                            variant="outline"
                            className="text-xs"
                          >
                            {perm.name}
                          </Badge>
                        ) : null;
                      })
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* 权限说明 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Shield className="h-5 w-5" />
            权限说明
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>权限名称</TableHead>
                <TableHead>说明</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {AVAILABLE_PERMISSIONS.map((perm) => (
                <TableRow key={perm.id}>
                  <TableCell className="font-medium">{perm.name}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {perm.description}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 编辑对话框 */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {selectedRole ? "编辑角色" : "新建角色"}
            </DialogTitle>
            <DialogDescription>
              配置角色信息和权限
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>角色名称</Label>
              <Input
                value={editForm.name}
                onChange={(e) =>
                  setEditForm({ ...editForm, name: e.target.value })
                }
                placeholder="输入角色名称"
              />
            </div>
            <div className="space-y-2">
              <Label>描述</Label>
              <Textarea
                value={editForm.description}
                onChange={(e) =>
                  setEditForm({ ...editForm, description: e.target.value })
                }
                placeholder="输入角色描述"
                rows={2}
              />
            </div>
            <div className="space-y-2">
              <Label>权限配置</Label>
              <div className="border rounded-lg p-4 space-y-2">
                {AVAILABLE_PERMISSIONS.map((perm) => (
                  <div
                    key={perm.id}
                    className="flex items-start gap-3 p-2 hover:bg-muted rounded-lg cursor-pointer"
                    onClick={() => togglePermission(perm.id)}
                  >
                    <Checkbox
                      checked={editForm.permissions.includes(perm.id)}
                      onCheckedChange={() => togglePermission(perm.id)}
                    />
                    <div className="flex-1">
                      <div className="font-medium">{perm.name}</div>
                      <div className="text-sm text-muted-foreground">
                        {perm.description}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave}>
              {selectedRole ? "保存" : "创建"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 删除确认对话框 */}
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
