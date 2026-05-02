import { useEffect, useState } from "react";
import { Edit, FolderTree, Plus, Trash2 } from "lucide-react";
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
import { adminApi, type Category, type CategoryPayload } from "@/services/adminApi";

const emptyForm: CategoryPayload = {
  name: "",
  slug: "",
  description: "",
  icon: "",
  sort_order: 0
};

export default function AdminCategories() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null);
  const [form, setForm] = useState<CategoryPayload>(emptyForm);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);

  useEffect(() => {
    fetchCategories();
  }, []);

  const fetchCategories = async () => {
    try {
      setIsLoading(true);
      const data = await adminApi.getCategories();
      setCategories(data);
    } catch (error) {
      console.error("获取分类列表失败:", error);
      setCategories([]);
    } finally {
      setIsLoading(false);
    }
  };

  const openCreate = () => {
    setSelectedCategory(null);
    setForm(emptyForm);
    setIsEditorOpen(true);
  };

  const openEdit = (category: Category) => {
    setSelectedCategory(category);
    setForm({
      name: category.name,
      slug: category.slug,
      description: category.description ?? "",
      icon: category.icon ?? "",
      sort_order: category.sort_order
    });
    setIsEditorOpen(true);
  };

  const saveCategory = async () => {
    const payload = {
      ...form,
      name: form.name.trim(),
      slug: form.slug.trim(),
      description: form.description?.trim() || null,
      icon: form.icon?.trim() || null,
      sort_order: Number(form.sort_order) || 0
    };

    try {
      if (selectedCategory) {
        await adminApi.updateCategory(selectedCategory.id, payload);
      } else {
        await adminApi.createCategory(payload);
      }
      setIsEditorOpen(false);
      await fetchCategories();
    } catch (error) {
      console.error("保存分类失败:", error);
    }
  };

  const deleteCategory = async () => {
    if (!selectedCategory) return;
    try {
      await adminApi.deleteCategory(selectedCategory.id);
      setIsDeleteOpen(false);
      await fetchCategories();
    } catch (error) {
      console.error("删除分类失败:", error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">分类管理</h2>
          <p className="text-muted-foreground">维护插件分类、排序和展示图标</p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="mr-2 h-4 w-4" />
          新建分类
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
                  <TableHead>分类</TableHead>
                  <TableHead>Slug</TableHead>
                  <TableHead>插件数</TableHead>
                  <TableHead>排序</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {categories.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="py-8 text-center">
                      暂无分类
                    </TableCell>
                  </TableRow>
                ) : (
                  categories.map((category) => (
                    <TableRow key={category.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                            <FolderTree className="h-4 w-4 text-primary" />
                          </div>
                          <div>
                            <div className="font-medium">{category.name}</div>
                            <div className="max-w-md truncate text-sm text-muted-foreground">
                              {category.description || "无描述"}
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-sm">{category.slug}</TableCell>
                      <TableCell>{category.plugin_count ?? 0}</TableCell>
                      <TableCell>{category.sort_order}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button variant="ghost" size="icon" onClick={() => openEdit(category)}>
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-red-500 hover:text-red-500"
                            onClick={() => {
                              setSelectedCategory(category);
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
            <DialogTitle>{selectedCategory ? "编辑分类" : "新建分类"}</DialogTitle>
            <DialogDescription>分类会用于插件列表筛选和插件详情展示。</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>名称</Label>
                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>Slug</Label>
                <Input value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>描述</Label>
              <Textarea value={form.description ?? ""} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>图标</Label>
                <Input value={form.icon ?? ""} onChange={(e) => setForm({ ...form, icon: e.target.value })} />
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
            <Button onClick={saveCategory} disabled={!form.name.trim() || !form.slug.trim()}>保存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除分类</DialogTitle>
            <DialogDescription>确定删除“{selectedCategory?.name}”吗？</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteOpen(false)}>取消</Button>
            <Button variant="destructive" onClick={deleteCategory}>删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
