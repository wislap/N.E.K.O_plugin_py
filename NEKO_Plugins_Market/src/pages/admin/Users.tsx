import { useEffect, useMemo, useState } from "react";
import {
  Ban,
  Calendar,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Edit,
  Mail,
  MoreHorizontal,
  Search,
  Shield,
  Trash2,
  User
} from "lucide-react";
import { useAdminSession } from "@/admin/session";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { adminApi, type Role, type User as UserType } from "@/services/adminApi";
import { notifySuccess, reportError } from "@/lib/error-reporting";
import { toast } from "sonner";

type UserForm = {
  username: string;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  role_ids: number[];
};

function roleIds(user: UserType | null) {
  return user?.roles?.map((role) => role.id) ?? [];
}

function sameIds(left: number[], right: number[]) {
  if (left.length !== right.length) return false;
  const leftSet = new Set(left);
  return right.every((id) => leftSet.has(id));
}

export default function AdminUsers() {
  const { user: currentUser, permissions: sessionPermissions } = useAdminSession();
  const [users, setUsers] = useState<UserType[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRolesLoading, setIsRolesLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [selectedUser, setSelectedUser] = useState<UserType | null>(null);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [editForm, setEditForm] = useState<UserForm>({
    username: "",
    email: "",
    is_admin: false,
    is_active: true,
    role_ids: []
  });

  const currentLevel = sessionPermissions?.level ?? 0;
  const isSuperAdmin = Boolean(sessionPermissions?.is_super_admin || sessionPermissions?.is_admin);
  const canAssignRoles = Boolean(
    isSuperAdmin ||
      sessionPermissions?.permissions.includes("*") ||
      sessionPermissions?.permissions.includes("system:role")
  );

  const assignableRoles = useMemo(() => {
    return roles.filter((role) => {
      if (role.code === "super_admin") return false;
      if (role.is_active === false) return false;
      if (isSuperAdmin) return true;
      return role.level < currentLevel;
    });
  }, [currentLevel, isSuperAdmin, roles]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(searchQuery.trim());
      setPage(1);
    }, 300);

    return () => window.clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    fetchUsers();
  }, [debouncedSearch, page, pageSize]);

  useEffect(() => {
    if (canAssignRoles) {
      fetchRoles();
    }
  }, [canAssignRoles]);

  const isCurrentUser = (user: UserType | null) => Boolean(
    currentUser && user && currentUser.id === user.id
  );

  const canManageUser = (user: UserType | null) => {
    if (!user) return false;
    if (isCurrentUser(user)) return false;
    if (isSuperAdmin) return true;
    if (user.is_admin) return false;
    return (user.level ?? 0) < currentLevel;
  };

  const canEditUser = (user: UserType | null) => {
    if (!user) return false;
    return isCurrentUser(user) || canManageUser(user);
  };

  const fetchUsers = async () => {
    try {
      setIsLoading(true);
      const data = await adminApi.getUsers({
        q: debouncedSearch || undefined,
        page,
        page_size: pageSize
      });
      setUsers(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages ?? 0);
    } catch (error) {
      reportError(error, {
        title: "获取用户列表失败",
        userMessage: "无法加载用户列表，请稍后重试。",
        context: { module: "admin.users", action: "fetchUsers", debouncedSearch, page, pageSize }
      });
      setUsers([]);
      setTotal(0);
      setTotalPages(0);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchRoles = async () => {
    try {
      setIsRolesLoading(true);
      const data = await adminApi.getRoles();
      setRoles(data);
    } catch (error) {
      reportError(error, {
        title: "获取角色失败",
        userMessage: "无法加载可分配角色，请检查权限。",
        context: { module: "admin.users", action: "fetchRoles" }
      });
      setRoles([]);
    } finally {
      setIsRolesLoading(false);
    }
  };

  const handleEdit = (user: UserType) => {
    if (!canEditUser(user)) return;
    setSelectedUser(user);
    setEditForm({
      username: user.username,
      email: user.email,
      is_admin: user.is_admin,
      is_active: user.is_active,
      role_ids: roleIds(user)
    });
    setIsEditOpen(true);
  };

  const handleSave = async () => {
    if (!selectedUser) return;
    const isSelf = isCurrentUser(selectedUser);

    if (isSelf && selectedUser.is_admin && !editForm.is_admin) {
      toast.error("不能降级当前登录用户");
      setEditForm((form) => ({ ...form, is_admin: true }));
      return;
    }
    if (isSelf && selectedUser.is_active && !editForm.is_active) {
      toast.error("不能禁用当前登录用户");
      setEditForm((form) => ({ ...form, is_active: true }));
      return;
    }
    if (!isSelf && !canManageUser(selectedUser)) {
      toast.error("只能管理等级低于自己的用户");
      return;
    }

    try {
      const payload: Partial<UserType> = {
        username: editForm.username,
        email: editForm.email
      };
      if (!isSelf) {
        payload.is_active = editForm.is_active;
      }
      if (isSuperAdmin && !isSelf) {
        payload.is_admin = editForm.is_admin;
      }

      await adminApi.updateUser(selectedUser.id, payload);

      const originalRoleIds = roleIds(selectedUser);
      const shouldAssignRoles =
        canAssignRoles &&
        !isSelf &&
        !editForm.is_admin &&
        !sameIds(originalRoleIds, editForm.role_ids);
      if (shouldAssignRoles) {
        await adminApi.assignRolesToUser(selectedUser.id, editForm.role_ids);
      }

      await fetchUsers();
      setIsEditOpen(false);
      notifySuccess("用户已更新");
    } catch (error) {
      reportError(error, {
        title: "更新用户失败",
        userMessage: "用户信息保存失败，请检查输入或权限。",
        context: { module: "admin.users", action: "updateUser", userId: selectedUser.id }
      });
    }
  };

  const handleDelete = async () => {
    if (!selectedUser) return;
    if (isCurrentUser(selectedUser)) {
      toast.error("不能删除当前登录用户");
      setIsDeleteOpen(false);
      return;
    }
    if (!canManageUser(selectedUser)) {
      toast.error("只能删除等级低于自己的用户");
      setIsDeleteOpen(false);
      return;
    }
    try {
      await adminApi.deleteUser(selectedUser.id);
      await fetchUsers();
      setIsDeleteOpen(false);
      notifySuccess("用户已删除");
    } catch (error) {
      reportError(error, {
        title: "删除用户失败",
        userMessage: "删除用户失败，请检查权限或用户状态。",
        context: { module: "admin.users", action: "deleteUser", userId: selectedUser.id }
      });
    }
  };

  const handleToggleActive = async (user: UserType) => {
    if (!canManageUser(user)) {
      toast.error("只能管理等级低于自己的用户");
      return;
    }
    try {
      await adminApi.updateUser(user.id, { is_active: !user.is_active });
      await fetchUsers();
      notifySuccess(user.is_active ? "用户已禁用" : "用户已启用");
    } catch (error) {
      reportError(error, {
        title: "切换用户状态失败",
        userMessage: "用户状态切换失败，请检查权限。",
        context: { module: "admin.users", action: "toggleActive", userId: user.id }
      });
    }
  };

  const toggleRole = (roleId: number) => {
    setEditForm((prev) => ({
      ...prev,
      role_ids: prev.role_ids.includes(roleId)
        ? prev.role_ids.filter((id) => id !== roleId)
        : [...prev.role_ids, roleId]
    }));
  };

  const renderUserRoles = (user: UserType) => {
    if (user.is_admin) {
      return (
        <Badge className="bg-violet-500/10 text-violet-600 border-violet-500/20 hover:bg-violet-500/10">
          <Shield className="h-3 w-3 mr-1" />
          超级管理员
        </Badge>
      );
    }

    const userRoles = user.roles ?? [];
    if (userRoles.length === 0) {
      return (
        <Badge variant="outline">
          <User className="h-3 w-3 mr-1" />
          普通用户
        </Badge>
      );
    }

    return (
      <div className="flex max-w-md flex-wrap gap-1">
        {userRoles.slice(0, 3).map((role) => (
          <Badge key={role.id} variant="outline">
            {role.name}
          </Badge>
        ))}
        {userRoles.length > 3 && (
          <Badge variant="secondary">+{userRoles.length - 3}</Badge>
        )}
      </div>
    );
  };

  const selectedIsSelf = isCurrentUser(selectedUser);
  const selectedCanManage = canManageUser(selectedUser);
  const showSuperAdminControl = isSuperAdmin && selectedUser && !selectedIsSelf;
  const showActiveControl = selectedUser && !selectedIsSelf && selectedCanManage;
  const showRoleControl =
    selectedUser &&
    canAssignRoles &&
    !selectedIsSelf &&
    selectedCanManage &&
    !editForm.is_admin;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">用户管理</h2>
        <p className="text-muted-foreground">管理用户账户、角色和等级边界</p>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="搜索用户名或邮箱..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardHeader>
        <CardContent>
          <div className="mb-4 flex flex-col gap-3 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
            <div>
              共 {total} 个用户
              {debouncedSearch && <span>，正在搜索 “{debouncedSearch}”</span>}
            </div>
            <div className="flex items-center gap-2">
              <span>每页</span>
              <Select
                value={String(pageSize)}
                onValueChange={(value) => {
                  setPageSize(Number(value));
                  setPage(1);
                }}
              >
                <SelectTrigger className="h-8 w-20">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="10">10</SelectItem>
                  <SelectItem value="20">20</SelectItem>
                  <SelectItem value="50">50</SelectItem>
                  <SelectItem value="100">100</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {isLoading ? (
            <div className="text-center py-8">加载中...</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>用户</TableHead>
                  <TableHead>邮箱</TableHead>
                  <TableHead>角色</TableHead>
                  <TableHead>等级</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>注册时间</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8">
                      暂无用户数据
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((user) => {
                    const isSelf = isCurrentUser(user);
                    const canManage = canManageUser(user);
                    const canEdit = canEditUser(user);
                    const hasActions = canEdit || canManage;
                    return (
                      <TableRow key={user.id}>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                              <User className="h-4 w-4 text-primary" />
                            </div>
                            <div>
                              <div className="font-medium">{user.username}</div>
                              {isSelf && <div className="text-xs text-muted-foreground">当前登录</div>}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1 text-muted-foreground">
                            <Mail className="h-3 w-3" />
                            {user.email}
                          </div>
                        </TableCell>
                        <TableCell>{renderUserRoles(user)}</TableCell>
                        <TableCell>
                          <Badge variant="outline">等级 {user.level ?? 0}</Badge>
                        </TableCell>
                        <TableCell>
                          {user.is_active ? (
                            <Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/20">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              正常
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="bg-red-500/10 text-red-600 border-red-500/20">
                              <Ban className="h-3 w-3 mr-1" />
                              已禁用
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1 text-muted-foreground text-sm">
                            <Calendar className="h-3 w-3" />
                            {new Date(user.created_at).toLocaleDateString()}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          {hasActions && (
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon">
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                {canEdit && (
                                  <DropdownMenuItem onClick={() => handleEdit(user)}>
                                    <Edit className="h-4 w-4 mr-2" />
                                    编辑
                                  </DropdownMenuItem>
                                )}
                                {canManage && (
                                  <DropdownMenuItem onClick={() => handleToggleActive(user)}>
                                    {user.is_active ? (
                                      <>
                                        <Ban className="h-4 w-4 mr-2" />
                                        禁用
                                      </>
                                    ) : (
                                      <>
                                        <CheckCircle className="h-4 w-4 mr-2" />
                                        启用
                                      </>
                                    )}
                                  </DropdownMenuItem>
                                )}
                                {canManage && (
                                  <DropdownMenuItem
                                    className="text-red-500"
                                    onClick={() => {
                                      setSelectedUser(user);
                                      setIsDeleteOpen(true);
                                    }}
                                  >
                                    <Trash2 className="h-4 w-4 mr-2" />
                                    删除
                                  </DropdownMenuItem>
                                )}
                              </DropdownMenuContent>
                            </DropdownMenu>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          )}

          {!isLoading && totalPages > 1 && (
            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="text-sm text-muted-foreground">
                第 {page} / {totalPages} 页
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((current) => Math.max(1, current - 1))}
                  disabled={page <= 1}
                >
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  上一页
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                  disabled={page >= totalPages}
                >
                  下一页
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>编辑用户</DialogTitle>
            <DialogDescription>修改用户资料和后台角色</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>用户名</Label>
                <Input
                  value={editForm.username}
                  onChange={(e) =>
                    setEditForm({ ...editForm, username: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>邮箱</Label>
                <Input
                  type="email"
                  value={editForm.email}
                  onChange={(e) =>
                    setEditForm({ ...editForm, email: e.target.value })
                  }
                />
              </div>
            </div>

            {showSuperAdminControl && (
              <div className="flex items-center justify-between rounded-md border p-3">
                <div className="space-y-1">
                  <Label>超级管理员</Label>
                  <p className="text-xs text-muted-foreground">拥有全部权限和最高管理等级</p>
                </div>
                <Switch
                  checked={editForm.is_admin}
                  onCheckedChange={(checked) =>
                    setEditForm({ ...editForm, is_admin: checked })
                  }
                />
              </div>
            )}

            {showActiveControl && (
              <div className="flex items-center justify-between rounded-md border p-3">
                <Label>账户启用</Label>
                <Switch
                  checked={editForm.is_active}
                  onCheckedChange={(checked) =>
                    setEditForm({ ...editForm, is_active: checked })
                  }
                />
              </div>
            )}

            {showRoleControl && (
              <div className="space-y-2">
                <Label>角色</Label>
                <ScrollArea className="h-56 rounded-md border">
                  <div className="space-y-2 p-3">
                    {isRolesLoading ? (
                      <div className="py-6 text-center text-sm text-muted-foreground">加载中...</div>
                    ) : assignableRoles.length === 0 ? (
                      <div className="py-6 text-center text-sm text-muted-foreground">暂无可分配角色</div>
                    ) : (
                      assignableRoles.map((role) => (
                        <label
                          key={role.id}
                          className="flex items-start gap-3 rounded-md border p-3"
                        >
                          <Checkbox
                            checked={editForm.role_ids.includes(role.id)}
                            onCheckedChange={() => toggleRole(role.id)}
                          />
                          <span className="min-w-0 flex-1">
                            <span className="flex items-center gap-2">
                              <span className="font-medium">{role.name}</span>
                              <Badge variant="outline">等级 {role.level}</Badge>
                            </span>
                            <span className="block truncate text-sm text-muted-foreground">
                              {role.description || role.code}
                            </span>
                          </span>
                        </label>
                      ))
                    )}
                  </div>
                </ScrollArea>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave}>保存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              确定要删除用户 "{selectedUser?.username}" 吗？此操作不可撤销。
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
