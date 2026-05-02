import { useEffect, useState } from "react";
import {
  CheckCircle,
  XCircle,
  Clock,
  Eye,
  Search,
  Filter,
  RefreshCw,
  Code,
  Github,
  User,
  Calendar
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { adminApi, type Plugin } from "@/services/adminApi";
import { notifySuccess, reportError } from "@/lib/error-reporting";

interface ReviewData {
  comment: string;
}

export default function AdminPlugins() {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedPlugin, setSelectedPlugin] = useState<Plugin | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isReviewOpen, setIsReviewOpen] = useState(false);
  const [reviewData, setReviewData] = useState<ReviewData>({
    comment: ""
  });

  useEffect(() => {
    fetchPlugins();
  }, []);

  const fetchPlugins = async () => {
    try {
      setIsLoading(true);
      const data = await adminApi.getAllPlugins();
      setPlugins(data);
    } catch (error) {
      reportError(error, {
        title: "获取插件列表失败",
        userMessage: "无法加载插件审核列表，请稍后重试。",
        context: { module: "admin.plugins", action: "fetchPlugins" }
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleApprove = async (pluginId: number) => {
    try {
      await adminApi.approvePlugin(pluginId, reviewData.comment);
      fetchPlugins();
      setIsReviewOpen(false);
      notifySuccess("插件已通过审核");
    } catch (error) {
      reportError(error, {
        title: "审核通过失败",
        userMessage: "插件审核通过操作失败，请检查权限或后端日志。",
        context: { module: "admin.plugins", action: "approvePlugin", pluginId }
      });
    }
  };

  const handleReject = async (pluginId: number) => {
    try {
      await adminApi.rejectPlugin(pluginId, reviewData.comment);
      fetchPlugins();
      setIsReviewOpen(false);
      notifySuccess("插件已拒绝");
    } catch (error) {
      reportError(error, {
        title: "审核拒绝失败",
        userMessage: "插件审核拒绝操作失败，请检查权限或后端日志。",
        context: { module: "admin.plugins", action: "rejectPlugin", pluginId }
      });
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "pending":
        return (
          <Badge variant="outline" className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20">
            <Clock className="h-3 w-3 mr-1" />
            待审核
          </Badge>
        );
      case "approved":
        return (
          <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">
            <CheckCircle className="h-3 w-3 mr-1" />
            已通过
          </Badge>
        );
      case "rejected":
        return (
          <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/20">
            <XCircle className="h-3 w-3 mr-1" />
            已拒绝
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const filteredPlugins = plugins.filter((plugin) => {
    const matchesSearch =
      plugin.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (plugin.description ?? "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      plugin.author_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === "all" || plugin.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const pendingPlugins = filteredPlugins.filter((p) => p.status === "pending");
  const approvedPlugins = filteredPlugins.filter((p) => p.status === "approved");
  const rejectedPlugins = filteredPlugins.filter((p) => p.status === "rejected");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">插件审核</h2>
          <p className="text-muted-foreground">管理插件的审核状态</p>
        </div>
        <Button variant="outline" onClick={fetchPlugins}>
          <RefreshCw className="h-4 w-4 mr-2" />
          刷新
        </Button>
      </div>

      {/* 搜索和筛选 */}
      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索插件名称、描述或作者..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <Filter className="h-4 w-4 mr-2" />
            <SelectValue placeholder="筛选状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="pending">待审核</SelectItem>
            <SelectItem value="approved">已通过</SelectItem>
            <SelectItem value="rejected">已拒绝</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* 插件列表 */}
      <Tabs defaultValue="pending" className="space-y-4">
        <TabsList>
          <TabsTrigger value="pending">
            待审核 ({pendingPlugins.length})
          </TabsTrigger>
          <TabsTrigger value="approved">
            已通过 ({approvedPlugins.length})
          </TabsTrigger>
          <TabsTrigger value="rejected">
            已拒绝 ({rejectedPlugins.length})
          </TabsTrigger>
        </TabsList>

        {["pending", "approved", "rejected"].map((status) => {
          const statusPlugins =
            status === "pending"
              ? pendingPlugins
              : status === "approved"
              ? approvedPlugins
              : rejectedPlugins;

          return (
            <TabsContent key={status} value={status} className="space-y-4">
              {isLoading ? (
                <div className="text-center py-8">加载中...</div>
              ) : statusPlugins.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  暂无{status === "pending" ? "待审核" : status === "approved" ? "已通过" : "已拒绝"}的插件
                </div>
              ) : (
                <div className="grid gap-4">
                  {statusPlugins.map((plugin) => (
                    <Card key={plugin.id}>
                      <CardHeader className="pb-3">
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-4">
                            <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center">
                              <Code className="h-6 w-6 text-primary" />
                            </div>
                            <div>
                              <CardTitle className="text-lg">{plugin.name}</CardTitle>
                              <CardDescription className="line-clamp-1">
                                {plugin.description}
                              </CardDescription>
                            </div>
                          </div>
                          {getStatusBadge(plugin.status)}
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div className="flex items-center gap-6 text-sm text-muted-foreground">
                          <div className="flex items-center gap-1">
                            <User className="h-4 w-4" />
                            {plugin.author_name}
                          </div>
                          <div className="flex items-center gap-1">
                            <Github className="h-4 w-4" />
                            <a
                              href={plugin.repo_url ?? undefined}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="hover:text-foreground"
                            >
                              查看仓库
                            </a>
                          </div>
                          <div className="flex items-center gap-1">
                            <Calendar className="h-4 w-4" />
                            {new Date(plugin.created_at).toLocaleDateString()}
                          </div>
                        </div>
                        <div className="flex gap-2 mt-4">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setSelectedPlugin(plugin);
                              setIsDetailOpen(true);
                            }}
                          >
                            <Eye className="h-4 w-4 mr-1" />
                            查看详情
                          </Button>
                          {plugin.status === "pending" && (
                            <Button
	                              size="sm"
	                              onClick={() => {
	                                setSelectedPlugin(plugin);
	                                setReviewData({
	                                  comment: ""
	                                });
	                                setIsReviewOpen(true);
	                              }}
                            >
                              <CheckCircle className="h-4 w-4 mr-1" />
                              审核
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </TabsContent>
          );
        })}
      </Tabs>

      {/* 详情对话框 */}
      <Dialog open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>插件详情</DialogTitle>
            <DialogDescription>
              {selectedPlugin?.name}
            </DialogDescription>
          </DialogHeader>
          {selectedPlugin && (
            <div className="space-y-4">
              <div>
                <Label>描述</Label>
                <p className="text-sm text-muted-foreground mt-1">
                  {selectedPlugin.description}
                </p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>作者</Label>
                  <p className="text-sm text-muted-foreground mt-1">
                    {selectedPlugin.author_name}
                  </p>
                </div>
                <div>
                  <Label>版本</Label>
                  <p className="text-sm text-muted-foreground mt-1">
                    {selectedPlugin.version}
                  </p>
                </div>
              </div>
              <div>
                <Label>仓库地址</Label>
                <a
                  href={selectedPlugin.repo_url ?? undefined}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-primary hover:underline mt-1 block"
                >
                  {selectedPlugin.repo_url}
                </a>
              </div>
              {selectedPlugin.readme && (
                <div>
                  <Label>README</Label>
                  <div className="mt-2 p-4 bg-muted rounded-lg max-h-64 overflow-y-auto">
                    <pre className="text-sm whitespace-pre-wrap">
                      {selectedPlugin.readme}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* 审核对话框 */}
      <Dialog open={isReviewOpen} onOpenChange={setIsReviewOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>审核插件</DialogTitle>
	            <DialogDescription>
	              {selectedPlugin?.name}
	            </DialogDescription>
	          </DialogHeader>
	          <div className="space-y-4">
	            <div className="space-y-2">
	              <Label>审核意见</Label>
	              <Textarea
                placeholder="请输入审核意见..."
                value={reviewData.comment}
                onChange={(e) =>
                  setReviewData({ ...reviewData, comment: e.target.value })
                }
                rows={4}
              />
            </div>
          </div>
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => selectedPlugin && handleReject(selectedPlugin.id)}
            >
              <XCircle className="h-4 w-4 mr-1" />
              拒绝
            </Button>
            <Button onClick={() => selectedPlugin && handleApprove(selectedPlugin.id)}>
              <CheckCircle className="h-4 w-4 mr-1" />
              通过
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
