import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Send,
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
  const [errorMessage, setErrorMessage] = useState('');

  const slugify = (value: string) =>
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9\u4e00-\u9fa5]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 100);

  const hasUploadAccess = isDebugAuthEnabled || Boolean(localStorage.getItem('token'));
  const trimmedGithubUrl = githubUrl.trim();
  const repoName = trimmedGithubUrl.match(/^https:\/\/github\.com\/[^/\s]+\/([^/\s?#]+)\/?$/i)?.[1] ?? '';
  const isGithubRepoUrl = /^https:\/\/github\.com\/[^/\s]+\/[^/\s?#]+\/?$/i.test(trimmedGithubUrl);
  const hasValidRepoName = repoName ? /^n\.e\.k\.o_plugin_[a-z_][a-z0-9_]*$/.test(repoName) : false;
  const repoPluginId = hasValidRepoName ? repoName.replace(/^n\.e\.k\.o_plugin_/, '') : '';

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
        : prev.length >= 5
          ? prev
          : [...prev, tag]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage('');

    try {
      const submission = await submissionsApi.createAndSubmit({
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
      notifySuccess('审核申请已提交', {
        context: {
          module: 'upload',
          action: 'createSubmission',
          pluginName: pluginName.trim(),
          repoUrl: githubUrl.trim()
        }
      });
      navigate(`/my/plugins?submission=${submission.id}`, { replace: true });
    } catch (error) {
      const message = getErrorMessage(error, '提交申请失败，请稍后重试');
      setErrorMessage(message);
      reportError(error, {
        title: '提交插件申请失败',
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
    isGithubRepoUrl &&
    hasValidRepoName &&
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
          <h1 className="text-3xl font-bold text-white mb-2">提交插件申请</h1>
          <p className="text-slate-400">
            提交 GitHub 仓库和插件信息，进入 N.E.K.O. 插件审核队列。
          </p>
        </div>

        {/* Info Card */}
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4 mb-8">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-400 mt-0.5" />
            <div>
              <h3 className="text-blue-400 font-medium mb-1">提交须知</h3>
              <ul className="text-sm text-slate-400 space-y-1">
                <li>• 插件必须是独立 GitHub 仓库，仓库名固定为 n.e.k.o_plugin_&lt;plugin_id&gt;</li>
                <li>• 推荐使用 neko-plugin init-repo &lt;plugin_id&gt; 生成仓库骨架</li>
                <li>• 推送 v* 标签后，release.yml 会上传 .neko-plugin 到 GitHub Release</li>
                <li>• 审核通过后，还需要用 GitHub Release URL 发布首个可安装版本</li>
                <li>• 审核员会围绕代码、命名、描述、仓库可信度留下意见</li>
                <li>• 你可以在“我的插件”里持续查看申请状态</li>
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
                {trimmedGithubUrl && (!isGithubRepoUrl || !hasValidRepoName) && (
                  <p className="mt-2 text-sm text-red-300">
                    请输入 GitHub 仓库地址，仓库名需要符合 n.e.k.o_plugin_&lt;plugin_id&gt;，plugin_id 只能包含小写字母、数字和下划线，且不能以数字开头。
                  </p>
                )}
                {hasValidRepoName && (
                  <p className="mt-2 text-sm text-green-300">
                    仓库命名符合提交规则，对应 plugin_id: {repoPluginId}
                  </p>
                )}
                <div className="mt-4 rounded-xl border border-slate-800 bg-[#0F0F1A] p-4 text-sm text-slate-400">
                  <p className="mb-2 text-slate-300">推荐准备流程：</p>
                  <pre className="whitespace-pre-wrap font-mono text-xs leading-5 text-slate-300">
{`neko-plugin init-repo ${repoPluginId || '<plugin_id>'}
git remote add origin https://github.com/<owner>/n.e.k.o_plugin_${repoPluginId || '<plugin_id>'}
git tag v0.1.0
git push origin v0.1.0`}
                  </pre>
                </div>
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
                <p className="text-sm text-slate-500">这些内容会生成本次审核申请快照</p>
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
                {pluginName.trim() && (
                  <p className="mt-2 text-sm text-slate-500">
                    申请 slug: {slugify(pluginName) || '-'}
                  </p>
                )}
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
                <p className="text-sm text-slate-500">帮助审核员和用户理解插件用途</p>
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
                  <span className="text-slate-500 ml-1">(选择 1-5 个)</span>
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
                <p className="mt-2 text-sm text-slate-500">
                  已选择 {selectedTags.length}/5
                </p>
              </div>
            </div>
          </div>

          {/* Submit */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-slate-500">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">提交后会创建一条可追踪的审核申请</span>
            </div>
            <Button
              type="submit"
              disabled={!isFormValid || isSubmitting}
              className="bg-gradient-to-r from-primary to-accent hover:opacity-95 text-primary-foreground px-8 py-6 text-lg disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                  提交中...
                </>
              ) : (
                <>
                  <Send className="w-5 h-5 mr-2" />
                  提交审核申请
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
              申请前检查
            </h3>
            <ul className="space-y-2 text-slate-400">
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-500 mt-1" />
                <span>仓库名是 n.e.k.o_plugin_&lt;plugin_id&gt;，plugin.toml 中的 id 与后缀一致</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-500 mt-1" />
                <span>根目录包含 plugin.toml、README.md、pyproject.toml 和测试文件</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-500 mt-1" />
                <span>.github/workflows/release.yml 已生成，并能通过 check -r --market-release</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-500 mt-1" />
                <span>GitHub Release assets 中已有 &lt;plugin_id&gt;.neko-plugin</span>
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
                <span>创建审核申请</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center mt-0.5">
                  2
                </span>
                <span>进入待审核队列</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center mt-0.5">
                  3
                </span>
                <span>审核员添加意见并给出结论</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center mt-0.5">
                  4
                </span>
                <span>通过后填 GitHub Release URL，发布首个 stable 版本</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </main>
  );
}
