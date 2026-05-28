import { useEffect, useState } from "react";
import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  Download,
  ExternalLink,
  MoreHorizontal,
  Package,
  RefreshCcw,
  Search,
  Star,
  Trash2,
  User
} from "lucide-react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import { adminApi, type Plugin } from "@/services/adminApi";
import { notifySuccess, reportError } from "@/lib/error-reporting";

type StatusFilter = "all" | "approved" | "disabled";
type FeaturedFilter = "all" | "featured";
type SortValue = "created_at:desc" | "created_at:asc" | "download_count:desc" | "rating_average:desc" | "name:asc";

const statusLabels: Record<string, string> = {
  approved: "已发布",
  disabled: "已禁用"
};

function formatDate(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleDateString();
}

function statusBadge(plugin: Plugin) {
  if (plugin.status === "approved") {
    return <Badge variant="outline" className="border-green-500/20 bg-green-500/10 text-green-600">已发布</Badge>;
  }
  if (plugin.status === "disabled") {
    return <Badge variant="outline" className="border-red-500/20 bg-red-500/10 text-red-600">已禁用</Badge>;
  }
  return <Badge variant="outline">{statusLabels[plugin.status] ?? plugin.status}</Badge>;
}

export default function AdminPlugins() {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [featured, setFeatured] = useState<FeaturedFilter>("all");
  const [sort, setSort] = useState<SortValue>("created_at:desc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [selectedPlugin, setSelectedPlugin] = useState<Plugin | null>(null);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(searchQuery.trim());
      setPage(1);
    }, 300);

    return () => window.clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    void fetchPlugins();
  }, [debouncedSearch, status, featured, sort, page, pageSize]);

  const fetchPlugins = async () => {
    const [sortBy, sortOrder] = sort.split(":") as [SortValue extends `${infer Field}:${string}` ? Field : string, "asc" | "desc"];
    try {
      setIsLoading(true);
      const data = await adminApi.getAdminPlugins({
        q: debouncedSearch || undefined,
        status: status === "all" ? undefined : status,
        featured_only: featured === "featured" ? true : undefined,
        sort_by: sortBy as "created_at" | "download_count" | "rating_average" | "name",
        sort_order: sortOrder,
        page,
        page_size: pageSize
      });
      setPlugins(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages ?? 0);
    } catch (error) {
      reportError(error, {
        title: "获取插件列表失败",
        userMessage: "无法加载插件列表，请稍后重试。",
        context: { module: "admin.plugins", action: "fetchPlugins", debouncedSearch, status, featured, sort, page, pageSize }
      });
      setPlugins([]);
      setTotal(0);
      setTotalPages(0);
    } finally {
      setIsLoading(false);
    }
  };

  const openDelete = (plugin: Plugin) => {
    setSelectedPlugin(plugin);
    setIsDeleteOpen(true);
  };

  const handleDelete = async () => {
    if (!selectedPlugin) return;
    try {
      setIsDeleting(true);
      await adminApi.deleteAdminPlugin(selectedPlugin.id);
      notifySuccess("插件已删除");
      setIsDeleteOpen(false);
      await fetchPlugins();
    } catch (error) {
      reportError(error, {
        title: "删除插件失败",
        userMessage: "删除插件失败，请检查权限或插件关联数据。",
        context: { module: "admin.plugins", action: "deletePlugin", pluginId: selectedPlugin.id }
      });
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold">插件管理</h2>
          <p className="text-muted-foreground">查看和删除市场插件</p>
        </div>
        <Button variant="outline" onClick={() => void fetchPlugins()} disabled={isLoading}>
          <RefreshCcw className="mr-2 h-4 w-4" />
          刷新
        </Button>
      </div>

      <Card>
        <CardHeader className="space-y-3 pb-3">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="搜索插件名称、描述..."
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              className="pl-10"
            />
          </div>
          <div className="grid gap-3 md:grid-cols-4">
            <Select
              value={status}
              onValueChange={(value: StatusFilter) => {
                setStatus(value);
                setPage(1);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="插件状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="approved">已发布</SelectItem>
                <SelectItem value="disabled">已禁用</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={featured}
              onValueChange={(value: FeaturedFilter) => {
                setFeatured(value);
                setPage(1);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="推荐状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部插件</SelectItem>
                <SelectItem value="featured">仅推荐</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={sort}
              onValueChange={(value: SortValue) => {
                setSort(value);
                setPage(1);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="排序" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="created_at:desc">最新创建</SelectItem>
                <SelectItem value="created_at:asc">最早创建</SelectItem>
                <SelectItem value="download_count:desc">下载最多</SelectItem>
                <SelectItem value="rating_average:desc">评分最高</SelectItem>
                <SelectItem value="name:asc">名称 A-Z</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={String(pageSize)}
              onValueChange={(value) => {
                setPageSize(Number(value));
                setPage(1);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="每页数量" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="10">每页 10</SelectItem>
                <SelectItem value="20">每页 20</SelectItem>
                <SelectItem value="50">每页 50</SelectItem>
                <SelectItem value="100">每页 100</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <div className="mb-4 text-sm text-muted-foreground">
            共 {total} 个插件
            {debouncedSearch && <span>，正在搜索 “{debouncedSearch}”</span>}
          </div>

          {isLoading ? (
            <div className="py-8 text-center text-muted-foreground">加载中...</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>插件</TableHead>
                  <TableHead>作者</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>版本</TableHead>
                  <TableHead>数据</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {plugins.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                      暂无插件数据
                    </TableCell>
                  </TableRow>
                ) : (
                  plugins.map((plugin) => (
                    <TableRow key={plugin.id}>
                      <TableCell>
                        <div className="flex min-w-0 items-center gap-3">
                          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10">
                            <Package className="h-4 w-4 text-primary" />
                          </div>
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="font-medium">{plugin.name}</span>
                              {plugin.is_featured > 0 && (
                                <Badge variant="outline" className="border-amber-500/20 bg-amber-500/10 text-amber-600">
                                  <Star className="mr-1 h-3 w-3" />
                                  推荐
                                </Badge>
                              )}
                            </div>
                            <div className="mt-1 max-w-[320px] truncate font-mono text-xs text-muted-foreground">
                              {plugin.slug}
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1 text-sm text-muted-foreground">
                          <User className="h-3.5 w-3.5" />
                          {plugin.author_name}
                        </div>
                      </TableCell>
                      <TableCell>{statusBadge(plugin)}</TableCell>
                      <TableCell>
                        {plugin.latest_version ? (
                          <div className="space-y-1 text-sm">
                            <div className="font-mono">{plugin.latest_version.version}</div>
                            <Badge variant="outline">{plugin.latest_version.channel}</Badge>
                          </div>
                        ) : (
                          <span className="text-sm text-muted-foreground">无可用版本</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1 text-sm text-muted-foreground">
                          <div className="flex items-center gap-1">
                            <Download className="h-3.5 w-3.5" />
                            {plugin.download_count}
                          </div>
                          <div>{plugin.rating_average.toFixed(1)} 分 / {plugin.rating_count} 条</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1 text-sm text-muted-foreground">
                          <Calendar className="h-3.5 w-3.5" />
                          {formatDate(plugin.created_at)}
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
                            {plugin.status === "approved" && (
                              <DropdownMenuItem asChild>
                                <Link to={`/plugin/${plugin.id}`}>
                                  <ExternalLink className="mr-2 h-4 w-4" />
                                  查看详情
                                </Link>
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuItem className="text-red-500" onClick={() => openDelete(plugin)}>
                              <Trash2 className="mr-2 h-4 w-4" />
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
                  <ChevronLeft className="mr-1 h-4 w-4" />
                  上一页
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                  disabled={page >= totalPages}
                >
                  下一页
                  <ChevronRight className="ml-1 h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除插件</DialogTitle>
            <DialogDescription>
              确定要删除插件 “{selectedPlugin?.name}” 吗？此操作会删除版本、评论、评分、签名等插件关联数据，审核记录会保留但解除插件关联。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteOpen(false)} disabled={isDeleting}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
              {isDeleting ? "删除中..." : "删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
