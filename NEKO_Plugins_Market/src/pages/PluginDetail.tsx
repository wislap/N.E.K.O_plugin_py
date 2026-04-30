import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
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
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
// RatingBadge component removed - ratings now displayed inline
import { getPluginById, getReviewsByPluginId } from '@/data';
import { formatDate, formatNumber, getZoneById } from '@/lib/utils';
import { marked } from 'marked';
import 'highlight.js/styles/github-dark.css';

const ratingColors: Record<string, string> = {
  S: '#FFD700',
  A: '#C084FC',
  B: '#60A5FA',
  C: '#4ADE80',
  D: '#9CA3AF',
};

export function PluginDetail() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState('readme');
  const [reviewContent, setReviewContent] = useState('');

  const plugin = id ? getPluginById(id) : undefined;
  const pluginReviews = id ? getReviewsByPluginId(id) : [];
  const zone = plugin ? getZoneById(plugin.zone) : undefined;

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [id]);

  if (!plugin) {
    return (
      <main className="min-h-screen bg-[#0F0F1A] pt-24 pb-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-2xl font-bold text-white mb-4">插件未找到</h1>
          <p className="text-slate-400 mb-6">该插件不存在或已被删除</p>
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
              >
                <Download className="w-5 h-5 mr-2" />
                安装插件
              </Button>

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
                      评论内容
                    </label>
                    <Textarea
                      value={reviewContent}
                      onChange={(e) => setReviewContent(e.target.value)}
                      placeholder="分享你对这个插件的使用体验..."
                      className="bg-[#0F0F1A] border-slate-700 text-slate-200 placeholder:text-slate-600 min-h-[100px]"
                    />
                  </div>
                  <Button className="bg-primary hover:bg-primary/90 text-primary-foreground">
                    <MessageSquare className="w-4 h-4 mr-2" />
                    发表评论
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
                    <p className="text-slate-300 mb-4">{review.content}</p>
                    <div className="flex items-center gap-4">
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
