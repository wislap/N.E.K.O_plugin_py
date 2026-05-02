import { useEffect, useState } from "react";
import {
  Search,
  UserPlus,
  MoreHorizontal,
  Shield,
  User,
  Mail,
  Calendar,
  Ban,
  CheckCircle,
  Edit,
  Trash2,
  ChevronLeft,
  ChevronRight
} from "lucide-react";
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
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { adminApi, type User as UserType } from "@/services/api";

export default function AdminUsers() {
  const [users, setUsers] = useState<UserType[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [selectedUser, setSelectedUser] = useState<UserType | null>(null);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [editForm, setEditForm] = useState({
    username: "",
    email: "",
    is_admin: false,
    is_active: true
  });

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
      console.error("获取用户列表失败:", error);
      setUsers([]);
      setTotal(0);
      setTotalPages(0);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEdit = (user: UserType) => {
    setSelectedUser(user);
    setEditForm({
      username: user.username,
      email: user.email,
      is_admin: user.is_admin,
      is_active: user.is_active
    });
    setIsEditOpen(true);
  };

  const handleSave = async () => {
    if (!selectedUser) return;
    try {
      await adminApi.updateUser(selectedUser.id, editForm);
      await fetchUsers();
      setIsEditOpen(false);
    } catch (error) {
      console.error("更新用户失败:", error);
    }
  };

  const handleDelete = async () => {
    if (!selectedUser) return;
    try {
      await adminApi.deleteUser(selectedUser.id);
      await fetchUsers();
      setIsDeleteOpen(false);
    } catch (error) {
      console.error("删除用户失败:", error);
    }
  };

  const handleToggleActive = async (user: UserType) => {
    try {
      await adminApi.updateUser(user.id, { is_active: !user.is_active });
      await fetchUsers();
    } catch (error) {
      console.error("切换用户状态失败:", error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">用户管理</h2>
          <p className="text-muted-foreground">管理系统用户账户</p>
        </div>
        <Button>
          <UserPlus className="h-4 w-4 mr-2" />
          添加用户
        </Button>
      </div>

      {/* 搜索 */}
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
                  <TableHead>状态</TableHead>
                  <TableHead>注册时间</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8">
                      暂无用户数据
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                            <User className="h-4 w-4 text-primary" />
                          </div>
                          <span className="font-medium">{user.username}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1 text-muted-foreground">
                          <Mail className="h-3 w-3" />
                          {user.email}
                        </div>
                      </TableCell>
                      <TableCell>
                        {user.is_admin ? (
                          <Badge className="bg-purple-500/10 text-purple-500 border-purple-500/20">
                            <Shield className="h-3 w-3 mr-1" />
                            管理员
                          </Badge>
                        ) : (
                          <Badge variant="outline">
                            <User className="h-3 w-3 mr-1" />
                            普通用户
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {user.is_active ? (
                          <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            正常
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/20">
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
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => handleEdit(user)}>
                              <Edit className="h-4 w-4 mr-2" />
                              编辑
                            </DropdownMenuItem>
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
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))
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

      {/* 编辑对话框 */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>编辑用户</DialogTitle>
            <DialogDescription>
              修改用户信息
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
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
            <div className="flex items-center justify-between">
              <Label>管理员权限</Label>
              <Switch
                checked={editForm.is_admin}
                onCheckedChange={(checked) =>
                  setEditForm({ ...editForm, is_admin: checked })
                }
              />
            </div>
            <div className="flex items-center justify-between">
              <Label>账户状态</Label>
              <Switch
                checked={editForm.is_active}
                onCheckedChange={(checked) =>
                  setEditForm({ ...editForm, is_active: checked })
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave}>保存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 删除确认对话框 */}
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
