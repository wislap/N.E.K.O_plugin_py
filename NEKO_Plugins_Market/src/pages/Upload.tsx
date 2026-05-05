import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Upload as UploadIcon,
  Github,
  Info,
  CheckCircle,
  AlertCircle,
  ChevronLeft,
  Folder,
  FileText,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { zones } from '@/data';
import { submissionsApi } from '@/services/submissions';
import { isDebugAuthEnabled } from '@/lib/debug';
import { getErrorMessage, notifySuccess, reportError } from '@/lib/error-reporting';

const standardTags = [
  '游戏', '查询', '攻略', '辅助', '陪玩', '互动', '情感', '增强',
  '功能', '工具', '系统', '监控', '娱乐', '音乐', '视频', '笑话',
  '开发', '代码', 'API', 'AI', '图像', '生成', '翻译', '语言',
  '学习', '日程', '任务', '管理', '提醒', '天气', '统计', '数据',
];

export function Upload() {
  const location = useLocation();
  const navigate = useNavigate();
  const [githubUrl, setGithubUrl] = useState('');
  const [pluginName, setPluginName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedZone, setSelectedZone] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const slugify = (value: string) =>
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9\u4e00-\u9fa5]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 100);

  const hasUploadAccess = isDebugAuthEnabled || Boolean(localStorage.getItem('token'));

  useEffect(() => {
    if (!hasUploadAccess) {
      const next = `${location.pathname}${location.search}`;
      navigate(`/login?next=${encodeURIComponent(next)}`, { replace: true });
    }
  }, [hasUploadAccess, location.pathname, location.search, navigate]);

  const handleTagToggle = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag)
        ? prev.filter((t) => t !== tag)
        : [...prev, tag]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage('');

    try {
      await submissionsApi.createAndSubmit({
        plugin_name: pluginName.trim(),
        plugin_slug: slugify(pluginName),
        description: description.trim() || undefined,
        short_description: description.trim().slice(0, 255) || undefined,
        repo_url: githubUrl.trim(),
        zone_slug: selectedZone,
        tags: selectedTags,
        metadata: {
          source: 'web_upload'
        }
      }, '用户从上传页提交申请');
      notifySuccess('插件申请已提交审核', {
        context: {
          module: 'upload',
          action: 'createSubmission',
          pluginName: pluginName.trim(),
          repoUrl: githubUrl.trim()
        }
      });
      setShowSuccess(true);
    } catch (error) {
      const message = getErrorMessage(error, '上传失败，请稍后重试');
      setErrorMessage(message);
      reportError(error, {
        title: '上传插件失败',
        context: {
          module: 'upload',
          action: 'createSubmission',
          pluginName: pluginName.trim(),
          repoUrl: githubUrl.trim(),
          zoneSlug: selectedZone,
          tagCount: selectedTags.length
        }
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const isFormValid =
    githubUrl.trim() &&
    pluginName.trim() &&
    selectedZone &&
    selectedTags.length > 0;

  if (!hasUploadAccess) {
    return (
      <main className="min-h-screen bg-[#0F0F1A] pt-24 pb-20">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-slate-400 text-lg">正在确认登录状态...</p>
        </div>
      </main>
    );
  }

  if (showSuccess) {
    return (
      <main className="min-h-screen bg-[#0F0F1A] pt-24 pb-20">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="bg-[#1A1A2E] border border-slate-800/50 rounded-2xl p-12">
            <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="w-10 h-10 text-green-500" />
            </div>
            <h1 className="text-2xl font-bold text-white mb-4">
              插件上传成功！
            </h1>
            <p className="text-slate-400 mb-8">
              你的插件已提交审核，审核通过后将上架到插件市场。
              <br />
              我们会通过邮件通知你审核结果。
            </p>
            <div className="flex items-center justify-center gap-4">
              <Link to="/plugins">
                <Button className="bg-primary hover:bg-primary/90 text-primary-foreground">
                  浏览插件
                </Button>
              </Link>
              <Link to="/">
                <Button variant="outline" className="border-slate-700 text-slate-300 hover:bg-slate-800">
                  返回首页
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#0F0F1A] pt-24 pb-20">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Back Button */}
        <Link
          to="/plugins"
          className="inline-flex items-center text-slate-400 hover:text-white mb-6 transition-colors"
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          返回插件列表
        </Link>

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">上传插件</h1>
          <p className="text-slate-400">
            将你的插件分享到 N.E.K.O. 社区
          </p>
        </div>

        {/* Info Card */}
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4 mb-8">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-400 mt-0.5" />
            <div>
              <h3 className="text-blue-400 font-medium mb-1">上传须知</h3>
              <ul className="text-sm text-slate-400 space-y-1">
                <li>• 插件必须托管在 GitHub 上，仓库名格式为 n.e.k.o_plugin_xxx</li>
                <li>• 仓库需要包含 README.md 和必要的配置文件</li>
                <li>• 插件将通过 AI 和管理员双重审核</li>
                <li>• 审核通常需要 1-3 个工作日</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-8">
          {errorMessage && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-300">
              {errorMessage}
            </div>
          )}

          {/* GitHub Repository */}
          <div className="bg-[#1A1A2E] border border-slate-800/50 rounded-2xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
                <Github className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">
                  GitHub 仓库
                </h3>
                <p className="text-sm text-slate-500">插件源代码仓库地址</p>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <Label htmlFor="github-url" className="text-slate-300">
                  仓库 URL <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="github-url"
                  type="url"
                  placeholder="https://github.com/username/n.e.k.o_plugin_demo"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  className="mt-2 bg-[#0F0F1A] border-slate-700 text-slate-200 placeholder:text-slate-600"
                  required
                />
              </div>
            </div>
          </div>

          {/* Plugin Info */}
          <div className="bg-[#1A1A2E] border border-slate-800/50 rounded-2xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
                <FileText className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">插件信息</h3>
                <p className="text-sm text-slate-500">插件的基本信息</p>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <Label htmlFor="plugin-name" className="text-slate-300">
                  插件名称 <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="plugin-name"
                  type="text"
                  placeholder="输入插件名称"
                  value={pluginName}
                  onChange={(e) => setPluginName(e.target.value)}
                  className="mt-2 bg-[#0F0F1A] border-slate-700 text-slate-200 placeholder:text-slate-600"
                  required
                />
              </div>
              <div>
                <Label htmlFor="description" className="text-slate-300">
                  简介 <span className="text-slate-500">(可选)</span>
                </Label>
                <Textarea
                  id="description"
                  placeholder="简短描述插件的功能..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="mt-2 bg-[#0F0F1A] border-slate-700 text-slate-200 placeholder:text-slate-600 min-h-[100px]"
                />
              </div>
            </div>
          </div>

          {/* Zone & Tags */}
          <div className="bg-[#1A1A2E] border border-slate-800/50 rounded-2xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center">
                <Folder className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">分类与标签</h3>
                <p className="text-sm text-slate-500">选择插件所属分类和标签</p>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <Label htmlFor="zone" className="text-slate-300">
                  分区 <span className="text-red-500">*</span>
                </Label>
                <Select value={selectedZone} onValueChange={setSelectedZone}>
                  <SelectTrigger className="mt-2 bg-[#0F0F1A] border-slate-700 text-slate-200">
                    <SelectValue placeholder="选择分区" />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1A1A2E] border-slate-700">
                    {zones.map((zone) => (
                      <SelectItem
                        key={zone.id}
                        value={zone.id}
                        className="text-slate-200 focus:bg-primary/20 focus:text-white"
                      >
                        {zone.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-slate-300 mb-2 block">
                  标签 <span className="text-red-500">*</span>
                  <span className="text-slate-500 ml-1">(至少选择一个)</span>
                </Label>
                <div className="flex flex-wrap gap-2 mt-2">
                  {standardTags.map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => handleTagToggle(tag)}
                      className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                        selectedTags.includes(tag)
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-[#0F0F1A] text-slate-400 border border-slate-700 hover:border-primary/50 hover:text-slate-300'
                      }`}
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Submit */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-slate-500">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">提交即表示同意服务条款</span>
            </div>
            <Button
              type="submit"
              disabled={!isFormValid || isSubmitting}
              className="bg-gradient-to-r from-primary to-accent hover:opacity-95 text-primary-foreground px-8 py-6 text-lg disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                  上传中...
                </>
              ) : (
                <>
                  <UploadIcon className="w-5 h-5 mr-2" />
                  上传插件
                </>
              )}
            </Button>
          </div>
        </form>

        {/* Requirements */}
        <Separator className="my-12 bg-slate-800/50" />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <h3 className="text-lg font-semibold text-white mb-4">
              插件开发指南
            </h3>
            <ul className="space-y-2 text-slate-400">
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-500 mt-1" />
                <span>阅读官方插件开发文档</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-500 mt-1" />
                <span>使用官方提供的 SDK</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-500 mt-1" />
                <span>遵循代码规范和安全要求</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-500 mt-1" />
                <span>编写完整的 README 文档</span>
              </li>
            </ul>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white mb-4">
              审核流程
            </h3>
            <ul className="space-y-2 text-slate-400">
              <li className="flex items-start gap-2">
                <span className="w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center mt-0.5">
                  1
                </span>
                <span>提交插件信息</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center mt-0.5">
                  2
                </span>
                <span>AI 自动分析评级</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center mt-0.5">
                  3
                </span>
                <span>管理员人工审核</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center mt-0.5">
                  4
                </span>
                <span>审核通过后上架</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </main>
  );
}
