import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Calendar,
  CheckCircle,
  Clock,
  ExternalLink,
  Github,
  Package,
  Plus,
  ShieldOff,
  XCircle
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { pluginsApi } from '@/services/plugins';
import type { Plugin } from '@/services/types';
import { listContainer, listItem, softReveal } from '@/lib/animations';
import { isDebugAuthEnabled } from '@/lib/debug';
import { getErrorMessage, reportError } from '@/lib/error-reporting';

const statusMeta: Record<string, { label: string; className: string; icon: typeof Clock }> = {
  pending: {
    label: '待审核',
    className: 'border-yellow-500/20 bg-yellow-500/10 text-yellow-300',
    icon: Clock
  },
  approved: {
    label: '已通过',
    className: 'border-green-500/20 bg-green-500/10 text-green-300',
    icon: CheckCircle
  },
  rejected: {
    label: '已拒绝',
    className: 'border-red-500/20 bg-red-500/10 text-red-300',
    icon: XCircle
  },
  disabled: {
    label: '已禁用',
    className: 'border-slate-500/20 bg-slate-500/10 text-slate-300',
    icon: ShieldOff
  }
};

function formatDate(value?: string | null) {
  if (!value) {
    return '-';
  }

  return new Date(value).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  });
}

function getReviewNote(plugin: Plugin) {
  return plugin.review_summary?.manual_review_notes || plugin.review_summary?.review_feedback || '';
}

export function MyPlugins() {
  const location = useLocation();
  const navigate = useNavigate();
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token && !isDebugAuthEnabled) {
      const next = `${location.pathname}${location.search}`;
      navigate(`/login?next=${encodeURIComponent(next)}`, { replace: true });
      return;
    }

    let isMounted = true;

    async function fetchPlugins() {
      try {
        setIsLoading(true);
        setErrorMessage('');
        const data = await pluginsApi.mine();
        if (isMounted) {
          setPlugins(data);
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(getErrorMessage(error, '我的插件加载失败'));
        }
        reportError(error, {
          title: '我的插件加载失败',
          context: {
            module: 'myPlugins',
            action: 'mine'
          }
        });
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    fetchPlugins();

    return () => {
      isMounted = false;
    };
  }, [location.pathname, location.search, navigate]);

  const stats = useMemo(() => ({
    total: plugins.length,
    pending: plugins.filter((plugin) => plugin.status === 'pending').length,
    approved: plugins.filter((plugin) => plugin.status === 'approved').length,
    rejected: plugins.filter((plugin) => plugin.status === 'rejected').length
  }), [plugins]);

  return (
    <main className="min-h-screen bg-[#0F0F1A] pt-24 pb-20">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-sm text-primary">
              <Package className="h-4 w-4" />
              我的提交
            </div>
            <h1 className="text-3xl font-bold text-white">我的插件</h1>
            <p className="mt-2 text-slate-400">查看你提交的插件和当前审核状态。</p>
          </div>
          <Link to="/upload">
            <Button className="bg-primary hover:bg-primary/90 text-primary-foreground">
              <Plus className="mr-2 h-4 w-4" />
              上传插件
            </Button>
          </Link>
        </div>

        <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
          {[
            ['全部', stats.total],
            ['待审核', stats.pending],
            ['已通过', stats.approved],
            ['已拒绝', stats.rejected]
          ].map(([label, value]) => (
            <div key={label} className="rounded-xl border border-slate-800/50 bg-[#1A1A2E] p-4">
              <div className="text-sm text-slate-500">{label}</div>
              <div className="mt-2 text-2xl font-bold text-white">{value}</div>
            </div>
          ))}
        </div>

        {isLoading ? (
          <motion.div variants={softReveal} initial="initial" animate="animate" className="py-20 text-center">
            <p className="text-lg text-slate-400">正在加载我的插件...</p>
          </motion.div>
        ) : errorMessage ? (
          <motion.div variants={softReveal} initial="initial" animate="animate" className="rounded-xl border border-red-500/20 bg-red-500/10 p-6 text-red-300">
            {errorMessage}
          </motion.div>
        ) : plugins.length === 0 ? (
          <motion.div variants={softReveal} initial="initial" animate="animate" className="rounded-2xl border border-slate-800/50 bg-[#1A1A2E] p-12 text-center">
            <Package className="mx-auto mb-4 h-12 w-12 text-slate-500" />
            <h2 className="text-xl font-semibold text-white">还没有提交插件</h2>
            <p className="mt-2 text-slate-400">上传你的第一个插件后，它会出现在这里。</p>
            <Link to="/upload" className="mt-6 inline-flex">
              <Button className="bg-primary hover:bg-primary/90 text-primary-foreground">
                <Plus className="mr-2 h-4 w-4" />
                去上传
              </Button>
            </Link>
          </motion.div>
        ) : (
          <motion.div variants={listContainer} initial="initial" animate="animate" className="space-y-4">
            {plugins.map((plugin) => {
              const meta = statusMeta[plugin.status] ?? statusMeta.pending;
              const StatusIcon = meta.icon;
              const reviewNote = getReviewNote(plugin);
              const reviewedAt = plugin.review_summary?.completed_at || plugin.review_summary?.manual_reviewed_at;

              return (
                <motion.article
                  key={plugin.id}
                  variants={listItem}
                  className="rounded-2xl border border-slate-800/50 bg-[#1A1A2E] p-5 transition-colors hover:border-primary/30"
                >
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div className="min-w-0">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <Badge variant="outline" className={meta.className}>
                          <StatusIcon className="mr-1 h-3 w-3" />
                          {meta.label}
                        </Badge>
                        <span className="text-xs font-mono text-slate-500">v{plugin.version}</span>
                      </div>
                      <h2 className="truncate text-xl font-semibold text-white">{plugin.name}</h2>
                      <p className="mt-1 line-clamp-2 text-sm text-slate-400">
                        {plugin.description || plugin.short_description || '暂无简介'}
                      </p>
                      <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-slate-500">
                        <span className="inline-flex items-center gap-1">
                          <Calendar className="h-4 w-4" />
                          提交于 {formatDate(plugin.created_at)}
                        </span>
                        {plugin.repo_url && (
                          <a
                            href={plugin.repo_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-slate-400 hover:text-white"
                          >
                            <Github className="h-4 w-4" />
                            GitHub
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                      </div>
                      {(reviewNote || reviewedAt) && (
                        <div className="mt-4 rounded-xl border border-slate-800/70 bg-slate-950/40 p-4">
                          <div className="mb-1 text-sm font-medium text-slate-300">
                            {plugin.status === 'rejected' ? '拒绝原因' : '审核意见'}
                          </div>
                          {reviewNote && (
                            <p className="whitespace-pre-wrap text-sm leading-6 text-slate-400">
                              {reviewNote}
                            </p>
                          )}
                          {reviewedAt && (
                            <div className="mt-2 text-xs text-slate-500">
                              审核时间 {formatDate(reviewedAt)}
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="flex shrink-0 items-center gap-2">
                      {plugin.status === 'approved' && (
                        <Link to={`/plugin/${plugin.id}`}>
                          <Button variant="outline" className="border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white">
                            查看页面
                          </Button>
                        </Link>
                      )}
                    </div>
                  </div>
                </motion.article>
              );
            })}
          </motion.div>
        )}
      </div>
    </main>
  );
}
