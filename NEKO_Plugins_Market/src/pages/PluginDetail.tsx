import { useState, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import {
  Download,
  ThumbsUp,
  Github,
  Calendar,
  ExternalLink,
  ChevronLeft,
  Sparkles,
  Shield,
  Bot,
  MessageSquare,
  Plug,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
// RatingBadge component removed - ratings now displayed inline
import { formatDate, formatNumber, getZoneById } from '@/lib/utils';
import { marked } from 'marked';
import 'highlight.js/styles/github-dark.css';
import { pluginsApi } from '@/services/plugins';
import { reviewsApi } from '@/services/reviews';
import { versionsApi } from '@/services/versions';
import { nekoBridge } from '@/lib/neko-bridge';
import type { Plugin, Review } from '@/types';
import type { PluginVersion } from '@/services/types';
import { getErrorMessage, logError, notifySuccess, reportError } from '@/lib/error-reporting';

const ratingColors: Record<string, string> = {
  S: '#FFD700',
  A: '#C084FC',
  B: '#60A5FA',
  C: '#4ADE80',
  D: '#9CA3AF',
};

export function PluginDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('readme');
  const [reviewContent, setReviewContent] = useState('');
  const [reviewTitle, setReviewTitle] = useState('');
  const [reviewRating, setReviewRating] = useState(5);
  const [plugin, setPlugin] = useState<Plugin | null>(null);
  const [pluginReviews, setPluginReviews] = useState<Review[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [reviewError, setReviewError] = useState('');
  const [nekoOnline, setNekoOnline] = useState<boolean | null>(null);
  const [installStatus, setInstallStatus] = useState<'idle' | 'installing' | 'success' | 'error'>('idle');
  const [installMessage, setInstallMessage] = useState('');
  const [latestVersion, setLatestVersion] = useState<PluginVersion | null>(null);
  const zone = plugin ? getZoneById(plugin.zone) : undefined;

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [id]);

  useEffect(() => {
    let isMounted = true;

    async function fetchPlugin() {
      if (!id) {
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setErrorMessage('');
        const data = await pluginsApi.getById(id);
        const reviews = await reviewsApi.list(id);
        // 并行拉取版本信息，失败不影响详情展示
        let versions: PluginVersion[] = [];
        try {
          versions = await versionsApi.list(Number(id));
        } catch {
          versions = [];
        }
        if (isMounted) {
          setPlugin(data);
          setPluginReviews(reviews.items);
          if (versions.length > 0) {
            const matched = versions.find((v) => v.version === data.version) || versions[0];
            setLatestVersion(matched);
          }
        }
      } catch (error) {
        if (isMounted) {
          setPlugin(null);
          setErrorMessage(getErrorMessage(error, '插件详情加载失败'));
        }
        reportError(error, {
          title: '插件详情加载失败',
          context: {
            module: 'pluginDetail',
            action: 'load',
            pluginId: id
          }
        });
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    fetchPlugin();

    return () => {
      isMounted = false;
    };
  }, [id]);

  // 探测 N.E.K.O 客户端是否在线
  useEffect(() => {
    nekoBridge.probe().then((status) => {
      setNekoOnline(!!status);
    });
  }, []);

  const handleDownload = async () => {
    if (!plugin || isDownloading) {
      return;
    }

    setIsDownloading(true);
    try {
      await pluginsApi.recordDownload(plugin.id);
      setPlugin({
        ...plugin,
        downloads: plugin.downloads + 1
      });
    } catch (error) {
      logError(error, {
        title: '下载计数记录失败',
        severity: 'warn',
        context: {
          module: 'pluginDetail',
          action: 'recordDownload',
          pluginId: plugin.id
        }
      });
    } finally {
      setIsDownloading(false);
    }

    const target = plugin.downloadUrl || plugin.githubRepo;
    if (target) {
      window.open(target, '_blank', 'noopener,noreferrer');
    }
  };

  const submitReview = async () => {
    if (!plugin || isSubmittingReview) {
      return;
    }

    const token = localStorage.getItem('token');
    if (!token) {
      navigate(`/login?next=${encodeURIComponent(`/plugin/${plugin.id}`)}`);
      return;
    }

    setReviewError('');
    setIsSubmittingReview(true);
    try {
      const review = await reviewsApi.create(plugin.id, {
        rating: reviewRating,
        title: reviewTitle.trim() || undefined,
        content: reviewContent.trim() || undefined
      });
      setPluginReviews((items) => [review, ...items]);
      setReviewTitle('');
      setReviewContent('');
      setReviewRating(5);
      notifySuccess('评论已提交', {
        context: {
          module: 'pluginDetail',
          action: 'createReview',
          pluginId: plugin.id
        }
      });
    } catch (error) {
      const message = getErrorMessage(error, '评论提交失败');
      setReviewError(message);
      reportError(error, {
        title: '评论提交失败',
        context: {
          module: 'pluginDetail',
          action: 'createReview',
          pluginId: plugin.id,
          rating: reviewRating
        }
      });
    } finally {
      setIsSubmittingReview(false);
    }
  };

  if (isLoading) {
    return (
      <main className="min-h-screen bg-[#0F0F1A] pt-24 pb-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-slate-400 text-lg">正在加载插件详情...</p>
        </div>
      </main>
    );
  }

  if (!plugin) {
    return (
      <main className="min-h-screen bg-[#0F0F1A] pt-24 pb-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-2xl font-bold text-white mb-4">插件未找到</h1>
          <p className="text-slate-400 mb-6">{errorMessage || '该插件不存在或已被删除'}</p>
          <Link to="/plugins">
            <Button className="bg-primary hover:bg-primary/90 text-primary-foreground">
              <ChevronLeft className="w-4 h-4 mr-2" />
              返回插件列表
            </Button>
          </Link>
        </div>
      </main>
    );
  }

  const readmeHtml = marked(plugin.readme);

  return (
    <main className="min-h-screen bg-[#0F0F1A] pt-24 pb-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Back Button */}
        <Link
          to="/plugins"
          className="inline-flex items-center text-slate-400 hover:text-white mb-6 transition-colors"
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          返回插件列表
        </Link>

        {/* Header */}
        <div className="bg-[#1A1A2E] border border-slate-800/50 rounded-2xl p-6 md:p-8 mb-8">
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Left: Plugin Info */}
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-4">
                {plugin.isRecommended && (
                  <Badge className="bg-gradient-to-r from-amber-500 to-orange-500 text-white">
                    <Sparkles className="w-3 h-3 mr-1" />
                    推荐
                  </Badge>
                )}
                <Badge
                  className="text-xs"
                  style={{
                    backgroundColor: `${zone?.color}20`,
                    color: zone?.color,
                  }}
                >
                  {zone?.name}
                </Badge>
                <span className="text-slate-500 text-sm font-mono">
                  v{plugin.version}
                </span>
              </div>

              <h1 className="text-3xl md:text-4xl font-bold text-white mb-4">
                {plugin.name}
              </h1>

              <p className="text-slate-400 text-lg mb-6">
                {plugin.description}
              </p>

              {/* Author */}
              <div className="flex items-center gap-3 mb-6">
                <Avatar className="w-10 h-10">
                  <AvatarImage
                    src={plugin.author.avatar}
                    alt={plugin.author.name}
                  />
                  <AvatarFallback className="bg-primary text-primary-foreground">
                    {plugin.author.name[0]}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-white font-medium">
                      {plugin.author.name}
                    </span>
                    <a
                      href={plugin.author.github}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-slate-400 hover:text-white transition-colors"
                    >
                      <Github className="w-4 h-4" />
                    </a>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-slate-500">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      更新于 {formatDate(plugin.updatedAt)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Tags */}
              <div className="flex flex-wrap gap-2">
                {plugin.tags.map((tag) => (
                  <Badge
                    key={tag}
                    variant="secondary"
                    className="bg-slate-800/50 text-slate-400"
                  >
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Right: Stats & Actions */}
            <div className="lg:w-80 space-y-4">
              <div className="bg-[#0F0F1A] rounded-xl p-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center">
                    <div className="flex items-center justify-center gap-1 text-primary mb-1">
                      <ThumbsUp className="w-5 h-5" />
                      <span className="text-2xl font-bold">
                        {formatNumber(plugin.likes)}
                      </span>
                    </div>
                    <span className="text-slate-500 text-sm">点赞</span>
                  </div>
                  <div className="text-center">
                    <div className="flex items-center justify-center gap-1 text-primary mb-1">
                      <Download className="w-5 h-5" />
                      <span className="text-2xl font-bold">
                        {formatNumber(plugin.downloads)}
                      </span>
                    </div>
                    <span className="text-slate-500 text-sm">次下载</span>
                  </div>
                </div>
              </div>

              <Button
                className="w-full bg-gradient-to-r from-primary to-accent hover:opacity-95 text-primary-foreground py-6"
                onClick={async () => {
                  if (!plugin) return;

                  if (nekoOnline && nekoBridge.hasToken) {
                    // 一键安装到本地 N.E.K.O
                    setInstallStatus('installing');
                    setInstallMessage('正在安装...');
                    const packageUrl = latestVersion?.package_url || latestVersion?.download_url || plugin.downloadUrl || plugin.githubRepo || '';
                    const taskId = await nekoBridge.install(
                      {
                        package_url: packageUrl,
                        package_sha256: latestVersion?.package_sha256 || '',
                        payload_hash: latestVersion?.payload_hash || undefined,
                        plugin_id: String(plugin.id),
                        version: latestVersion?.version || plugin.version,
                      },
                      (task) => {
                        setInstallMessage(task.message);
                        if (task.status === 'completed') {
                          setInstallStatus('success');
                          notifySuccess('插件已安装到 N.E.K.O', {
                            context: { module: 'pluginDetail', action: 'nekoInstall' }
                          });
                        } else if (task.status === 'failed') {
                          setInstallStatus('error');
                          setInstallMessage(task.error || '安装失败');
                        }
                      },
                    );
                    if (!taskId) {
                      // fallback 到 URI scheme / 下载
                      setInstallStatus('idle');
                      handleDownload();
                    }
                  } else {
                    // 没有连接 N.E.K.O，走原有下载逻辑
                    handleDownload();
                  }
                }}
                disabled={isDownloading || installStatus === 'installing'}
              >
                {installStatus === 'installing' ? (
                  <>
                    <Plug className="w-5 h-5 mr-2 animate-pulse" />
                    {installMessage || '安装中...'}
                  </>
                ) : installStatus === 'success' ? (
                  <>
                    <Plug className="w-5 h-5 mr-2" />
                    ✓ 已安装
                  </>
                ) : nekoOnline ? (
                  <>
                    <Plug className="w-5 h-5 mr-2" />
                    安装到 N.E.K.O
                  </>
                ) : (
                  <>
                    <Download className="w-5 h-5 mr-2" />
                    {isDownloading ? '正在记录...' : '安装插件'}
                  </>
                )}
              </Button>

              {nekoOnline !== null && (
                <div className="flex items-center justify-center gap-2 text-xs text-slate-500">
                  <span className={`w-2 h-2 rounded-full ${nekoOnline ? 'bg-green-500' : 'bg-slate-600'}`} />
                  {nekoOnline ? 'N.E.K.O 客户端已连接' : 'N.E.K.O 未检测到（将下载安装包）'}
                </div>
              )}

              <a
                href={plugin.githubRepo}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button
                  variant="outline"
                  className="w-full border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white py-6"
                >
                  <Github className="w-5 h-5 mr-2" />
                  查看源码
                  <ExternalLink className="w-4 h-4 ml-2" />
                </Button>
              </a>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-[#1A1A2E] border border-slate-800/50 p-1 mb-6">
            <TabsTrigger
              value="readme"
              className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground text-slate-400"
            >
              README
            </TabsTrigger>
            <TabsTrigger
              value="ratings"
              className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground text-slate-400"
            >
              评级
            </TabsTrigger>
            <TabsTrigger
              value="reviews"
              className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground text-slate-400"
            >
              评论 ({pluginReviews.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="readme" className="mt-0">
            <div className="bg-[#1A1A2E] border border-slate-800/50 rounded-2xl p-6 md:p-8">
              <div
                className="prose prose-invert max-w-none"
                dangerouslySetInnerHTML={{ __html: readmeHtml }}
              />
            </div>
          </TabsContent>

          <TabsContent value="ratings" className="mt-0">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* AI Rating */}
              <div className="bg-[#1A1A2E] border border-slate-800/50 rounded-2xl p-6">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
                    <Bot className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white">
                      AI 智能评级
                    </h3>
                    <p className="text-sm text-slate-500">
                      基于代码分析和功能评估
                    </p>
                  </div>
                </div>
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 bg-[#0F0F1A] rounded-lg">
                    <span className="text-slate-400">功能性</span>
                    <span
                      className="w-8 h-8 rounded-lg flex items-center justify-center text-lg font-bold"
                      style={{
                        backgroundColor: `${ratingColors[plugin.aiRating.functionality]}20`,
                        color: ratingColors[plugin.aiRating.functionality],
                      }}
                    >
                      {plugin.aiRating.functionality}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-[#0F0F1A] rounded-lg">
                    <span className="text-slate-400">安全性</span>
                    <span
                      className="w-8 h-8 rounded-lg flex items-center justify-center text-lg font-bold"
                      style={{
                        backgroundColor: `${ratingColors[plugin.aiRating.security]}20`,
                        color: ratingColors[plugin.aiRating.security],
                      }}
                    >
                      {plugin.aiRating.security}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-[#0F0F1A] rounded-lg">
                    <span className="text-slate-400">文档完善度</span>
                    <span
                      className="w-8 h-8 rounded-lg flex items-center justify-center text-lg font-bold"
                      style={{
                        backgroundColor: `${ratingColors[plugin.aiRating.documentation]}20`,
                        color: ratingColors[plugin.aiRating.documentation],
                      }}
                    >
                      {plugin.aiRating.documentation}
                    </span>
                  </div>
                </div>
                <p className="text-sm text-slate-500 mt-4">
                  评级时间: {plugin.aiRating.ratedAt}
                </p>
              </div>

              {/* Admin Rating */}
              <div className="bg-[#1A1A2E] border border-slate-800/50 rounded-2xl p-6">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
                    <Shield className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white">
                      官方评级
                    </h3>
                    <p className="text-sm text-slate-500">
                      管理员人工审核评级
                    </p>
                  </div>
                </div>
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 bg-[#0F0F1A] rounded-lg">
                    <span className="text-slate-400">功能性</span>
                    <span
                      className="w-8 h-8 rounded-lg flex items-center justify-center text-lg font-bold"
                      style={{
                        backgroundColor: `${ratingColors[plugin.adminRating.functionality]}20`,
                        color: ratingColors[plugin.adminRating.functionality],
                      }}
                    >
                      {plugin.adminRating.functionality}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-[#0F0F1A] rounded-lg">
                    <span className="text-slate-400">安全性</span>
                    <span
                      className="w-8 h-8 rounded-lg flex items-center justify-center text-lg font-bold"
                      style={{
                        backgroundColor: `${ratingColors[plugin.adminRating.security]}20`,
                        color: ratingColors[plugin.adminRating.security],
                      }}
                    >
                      {plugin.adminRating.security}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-[#0F0F1A] rounded-lg">
                    <span className="text-slate-400">文档完善度</span>
                    <span
                      className="w-8 h-8 rounded-lg flex items-center justify-center text-lg font-bold"
                      style={{
                        backgroundColor: `${ratingColors[plugin.adminRating.documentation]}20`,
                        color: ratingColors[plugin.adminRating.documentation],
                      }}
                    >
                      {plugin.adminRating.documentation}
                    </span>
                  </div>
                </div>
                <p className="text-sm text-slate-500 mt-4">
                  评级时间: {plugin.adminRating.ratedAt}
                </p>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="reviews" className="mt-0">
            <div className="space-y-6">
              {/* Write Review */}
              <div className="bg-[#1A1A2E] border border-slate-800/50 rounded-2xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4">
                  发表评论
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="text-sm text-slate-400 mb-2 block">
                      评分
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {[5, 4, 3, 2, 1].map((rating) => (
                        <button
                          key={rating}
                          type="button"
                          onClick={() => setReviewRating(rating)}
                          className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                            reviewRating === rating
                              ? 'border-primary bg-primary text-primary-foreground'
                              : 'border-slate-700 text-slate-400 hover:bg-slate-800 hover:text-white'
                          }`}
                        >
                          {rating} 分
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="text-sm text-slate-400 mb-2 block">
                      标题
                    </label>
                    <input
                      value={reviewTitle}
                      onChange={(e) => setReviewTitle(e.target.value)}
                      placeholder="一句话总结体验"
                      className="w-full rounded-md border border-slate-700 bg-[#0F0F1A] px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/20"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-slate-400 mb-2 block">
                      评论内容
                    </label>
                    <Textarea
                      value={reviewContent}
                      onChange={(e) => setReviewContent(e.target.value)}
                      placeholder="分享你对这个插件的使用体验..."
                      className="bg-[#0F0F1A] border-slate-700 text-slate-200 placeholder:text-slate-600 min-h-[100px]"
                    />
                  </div>
                  {reviewError && (
                    <p className="text-sm text-red-400">{reviewError}</p>
                  )}
                  <Button
                    className="bg-primary hover:bg-primary/90 text-primary-foreground"
                    onClick={submitReview}
                    disabled={isSubmittingReview || (!reviewTitle.trim() && !reviewContent.trim())}
                  >
                    <MessageSquare className="w-4 h-4 mr-2" />
                    {isSubmittingReview ? '提交中...' : '发表评论'}
                  </Button>
                </div>
              </div>

              {/* Reviews List */}
              {pluginReviews.length > 0 ? (
                pluginReviews.map((review) => (
                  <div
                    key={review.id}
                    className="bg-[#1A1A2E] border border-slate-800/50 rounded-2xl p-6"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <Avatar className="w-10 h-10">
                          <AvatarImage
                            src={review.user.avatar}
                            alt={review.user.name}
                          />
                          <AvatarFallback className="bg-primary text-primary-foreground">
                            {review.user.name[0]}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <span className="text-white font-medium">
                            {review.user.name}
                          </span>
                          <p className="text-sm text-slate-500">
                            {formatDate(review.createdAt)}
                          </p>
                        </div>
                      </div>
                    </div>
                    {review.title && (
                      <h4 className="mb-2 font-medium text-white">{review.title}</h4>
                    )}
                    <p className="text-slate-300 mb-4">{review.content || '未填写评论内容'}</p>
                    <div className="flex items-center gap-4">
                      <span className="rounded-full bg-primary/10 px-2 py-1 text-xs text-primary">
                        {review.rating ?? 5} 分
                      </span>
                      <button className="flex items-center gap-1.5 text-slate-500 hover:text-primary transition-colors">
                        <ThumbsUp className="w-4 h-4" />
                        <span className="text-sm">{review.likes}</span>
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-12 bg-[#1A1A2E] border border-slate-800/50 rounded-2xl">
                  <MessageSquare className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                  <p className="text-slate-400">暂无评论，来发表第一条评论吧！</p>
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </main>
  );
}
