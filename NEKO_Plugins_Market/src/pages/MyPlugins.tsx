import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Calendar,
  CheckCircle,
  Clock,
  Eye,
  ExternalLink,
  Github,
  MessageSquare,
  Package,
  Plus,
  ShieldOff,
  XCircle
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import { submissionsApi, type PluginSubmission, type PluginSubmissionDetail, type SubmissionReviewComment } from '@/services/submissions';
import { listContainer, softReveal } from '@/lib/animations';
import { isDebugAuthEnabled } from '@/lib/debug';
import { getErrorMessage, reportError } from '@/lib/error-reporting';

const statusMeta: Record<string, { label: string; className: string; icon: typeof Clock }> = {
  draft: {
    label: '草稿',
    className: 'border-slate-500/20 bg-slate-500/10 text-slate-300',
    icon: Clock
  },
  submitted: {
    label: '待审核',
    className: 'border-yellow-500/20 bg-yellow-500/10 text-yellow-300',
    icon: Clock
  },
  in_review: {
    label: '审核中',
    className: 'border-blue-500/20 bg-blue-500/10 text-blue-300',
    icon: Clock
  },
  closed_approved: {
    label: '已通过',
    className: 'border-green-500/20 bg-green-500/10 text-green-300',
    icon: CheckCircle
  },
  closed_rejected: {
    label: '已拒绝',
    className: 'border-red-500/20 bg-red-500/10 text-red-300',
    icon: XCircle
  },
  closed: {
    label: '已关闭',
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

function submissionStatusKey(submission: PluginSubmission) {
  if (submission.status !== 'closed') {
    return submission.status;
  }
  if (submission.decision === 'approved') return 'closed_approved';
  if (submission.decision === 'rejected') return 'closed_rejected';
  return 'closed';
}

function severityClass(severity: SubmissionReviewComment['severity']) {
  if (severity === 'critical') return 'border-red-500/30 bg-red-500/10 text-red-300';
  if (severity === 'major') return 'border-orange-500/30 bg-orange-500/10 text-orange-300';
  if (severity === 'minor') return 'border-blue-500/30 bg-blue-500/10 text-blue-300';
  return 'border-slate-500/30 bg-slate-500/10 text-slate-300';
}

export function MyPlugins() {
  const location = useLocation();
  const navigate = useNavigate();
  const searchParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const highlightedSubmissionId = Number(searchParams.get('submission') ?? 0);
  const [submissions, setSubmissions] = useState<PluginSubmission[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [activeView, setActiveView] = useState<'submissions' | 'published'>('submissions');
  const [selectedDetailId, setSelectedDetailId] = useState<number | null>(null);
  const [submissionDetail, setSubmissionDetail] = useState<PluginSubmissionDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token && !isDebugAuthEnabled) {
      const next = `${location.pathname}${location.search}`;
      navigate(`/login?next=${encodeURIComponent(next)}`, { replace: true });
      return;
    }

    let isMounted = true;

    async function fetchSubmissions() {
      try {
        setIsLoading(true);
        setErrorMessage('');
        const data = await submissionsApi.mine();
        if (isMounted) {
          setSubmissions(data.items);
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(getErrorMessage(error, '我的插件加载失败'));
        }
        reportError(error, {
          title: '我的插件加载失败',
          context: {
            module: 'myPlugins',
            action: 'submissionsMine'
          }
        });
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    fetchSubmissions();

    return () => {
      isMounted = false;
    };
  }, [location.pathname, location.search, navigate]);

  const stats = useMemo(() => ({
    total: submissions.length,
    pending: submissions.filter((submission) => submission.status === 'submitted' || submission.status === 'in_review').length,
    approved: submissions.filter((submission) => submission.decision === 'approved').length,
    rejected: submissions.filter((submission) => submission.decision === 'rejected').length
  }), [submissions]);

  const publishedSubmissions = useMemo(
    () => submissions.filter((submission) => submission.plugin_id && submission.decision === 'approved'),
    [submissions]
  );
  const visibleSubmissions = activeView === 'published' ? publishedSubmissions : submissions;

  const openSubmissionDetail = async (submissionId: number) => {
    setSelectedDetailId(submissionId);
    setDetailLoading(true);
    setDetailError('');
    setSubmissionDetail(null);

    try {
      const detail = await submissionsApi.detail(submissionId);
      setSubmissionDetail(detail);
    } catch (error) {
      setDetailError(getErrorMessage(error, '申请详情加载失败'));
      reportError(error, {
        title: '申请详情加载失败',
        context: {
          module: 'myPlugins',
          action: 'submissionDetail',
          submissionId
        }
      });
    } finally {
      setDetailLoading(false);
    }
  };

  const selectedSubmission = submissions.find((submission) => submission.id === selectedDetailId) ?? null;
  const detailFallbackSnapshot = selectedSubmission?.current_snapshot ?? null;
  const detailSnapshot = submissionDetail?.current_snapshot ?? detailFallbackSnapshot;
  const detailStatusMeta = statusMeta[submissionStatusKey(submissionDetail ?? selectedSubmission ?? { status: 'submitted' } as PluginSubmission)] ?? statusMeta.submitted;
  const detailComments = submissionDetail?.review_cases.flatMap((reviewCase) => reviewCase.comments) ?? [];

  return (
    <main className="min-h-screen bg-[#0F0F1A] pt-24 pb-20">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="mb-6 text-3xl font-bold text-white">我的插件申请</h1>

        <div className="mb-5 flex border-b border-slate-800">
          {[
            ['submissions', '审核申请', stats.total],
            ['published', '已发布插件', publishedSubmissions.length]
          ].map(([view, label, count]) => (
            <button
              key={view}
              type="button"
              onClick={() => setActiveView(view as 'submissions' | 'published')}
              className={`border-b-2 px-1 pb-3 pr-6 text-sm transition-colors ${
                activeView === view
                  ? 'border-primary text-primary'
                  : 'border-transparent text-slate-500 hover:text-slate-300'
              }`}
            >
              {label}
              <span className="ml-2 text-xs text-slate-500">{count}</span>
            </button>
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
        ) : submissions.length === 0 ? (
          <motion.div variants={softReveal} initial="initial" animate="animate" className="rounded-2xl border border-slate-800/50 bg-[#1A1A2E] p-12 text-center">
            <Package className="mx-auto mb-4 h-12 w-12 text-slate-500" />
            <h2 className="text-xl font-semibold text-white">还没有提交插件申请</h2>
            <p className="mt-2 text-slate-400">提交你的第一个插件申请后，它会出现在这里。</p>
            <Link to="/upload" className="mt-6 inline-flex">
              <Button className="bg-primary hover:bg-primary/90 text-primary-foreground">
                <Plus className="mr-2 h-4 w-4" />
                去提交申请
              </Button>
            </Link>
          </motion.div>
        ) : visibleSubmissions.length === 0 ? (
          <motion.div variants={softReveal} initial="initial" animate="animate" className="rounded-2xl border border-slate-800/50 bg-[#1A1A2E] p-12 text-center">
            <Package className="mx-auto mb-4 h-12 w-12 text-slate-500" />
            <h2 className="text-xl font-semibold text-white">还没有已发布插件</h2>
            <p className="mt-2 text-slate-400">审核通过并发布后，对应插件会出现在这里。</p>
          </motion.div>
        ) : (
          <motion.div variants={listContainer} initial="initial" animate="animate" className="space-y-3">
            {visibleSubmissions.map((submission) => {
              const snapshot = submission.current_snapshot;
              const meta = statusMeta[submissionStatusKey(submission)] ?? statusMeta.submitted;
              const StatusIcon = meta.icon;
              const closedAt = submission.closed_at;
              const isHighlighted = submission.id === highlightedSubmissionId;

              return (
                <article
                  key={submission.id}
                  className={`rounded-xl border bg-[#171728] p-4 opacity-100 transition-colors ${
                    isHighlighted
                      ? 'border-primary/80 shadow-[0_0_0_1px_rgba(96,165,250,0.25)]'
                      : 'border-slate-800/50 hover:border-primary/30'
                  }`}
                >
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <Badge variant="outline" className={meta.className}>
                          <StatusIcon className="mr-1 h-3 w-3" />
                          {meta.label}
                        </Badge>
                        {isHighlighted && (
                          <Badge variant="outline" className="border-primary/30 bg-primary/10 text-primary">
                            刚刚提交
                          </Badge>
                        )}
                        <span className="text-xs font-mono text-slate-500">申请 #{submission.id}</span>
                      </div>
                      <h2 className="truncate text-lg font-semibold text-white">{snapshot?.plugin_name ?? `提交 #${submission.id}`}</h2>
                      <p className="mt-1 line-clamp-1 text-sm text-slate-400">
                        {snapshot?.description || snapshot?.short_description || '暂无简介'}
                      </p>
                      <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-slate-500">
                        <span className="inline-flex items-center gap-1">
                          <Calendar className="h-4 w-4" />
                          提交于 {formatDate(submission.submitted_at ?? submission.created_at)}
                        </span>
                        {snapshot?.repo_url && (
                          <a
                            href={snapshot.repo_url}
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
                      <div className="mt-3 flex flex-wrap gap-2">
                        {(snapshot?.tags ?? []).map((tag) => (
                          <span key={tag} className="rounded-md border border-slate-800 bg-slate-950/60 px-2 py-1 text-xs text-slate-400">
                            {tag}
                          </span>
                        ))}
                      </div>
                      {closedAt && (
                        <div className="mt-4 rounded-xl border border-slate-800/70 bg-slate-950/40 p-4">
                          <div className="mb-1 text-sm font-medium text-slate-300">
                            审核状态
                          </div>
                          <div className="text-xs text-slate-500">
                            关闭时间 {formatDate(closedAt)}
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="flex shrink-0 items-center gap-2 lg:pt-7">
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => openSubmissionDetail(submission.id)}
                        className="border-primary/40 bg-primary/10 text-primary hover:bg-primary hover:text-primary-foreground"
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        查看详情
                      </Button>
                      {submission.plugin_id && submission.decision === 'approved' && (
                        <Link to={`/plugin/${submission.plugin_id}`}>
                          <Button variant="outline" className="border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white">
                            查看插件页
                          </Button>
                        </Link>
                      )}
                    </div>
                  </div>
                </article>
              );
            })}
          </motion.div>
        )}
      </div>

      <Dialog
        open={selectedDetailId !== null}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedDetailId(null);
            setSubmissionDetail(null);
            setDetailError('');
          }
        }}
      >
        <DialogContent className="max-h-[88vh] overflow-y-auto border-slate-800 bg-[#11111d] text-slate-100 sm:max-w-4xl">
          <DialogHeader>
            <DialogTitle className="pr-8 text-2xl">
              {detailSnapshot?.plugin_name ?? selectedSubmission?.current_snapshot?.plugin_name ?? '申请详情'}
            </DialogTitle>
            <DialogDescription>
              申请 #{selectedDetailId} 的提交快照、审核意见和处理记录。
            </DialogDescription>
          </DialogHeader>

          {detailLoading ? (
            <div className="space-y-3 py-8">
              <div className="h-6 w-48 animate-pulse rounded bg-slate-800" />
              <div className="h-28 animate-pulse rounded-xl bg-slate-800/70" />
              <div className="h-36 animate-pulse rounded-xl bg-slate-800/70" />
            </div>
          ) : detailError ? (
            <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-red-300">
              {detailError}
            </div>
          ) : (
            <div className="space-y-5">
              <section className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className={detailStatusMeta.className}>
                    {detailStatusMeta.label}
                  </Badge>
                  <span className="text-xs text-slate-500">
                    创建于 {formatDate(submissionDetail?.created_at ?? selectedSubmission?.created_at)}
                  </span>
                  <span className="text-xs text-slate-500">
                    提交于 {formatDate(submissionDetail?.submitted_at ?? selectedSubmission?.submitted_at)}
                  </span>
                </div>
                <p className="text-sm leading-6 text-slate-300">
                  {detailSnapshot?.description || detailSnapshot?.short_description || '暂无简介'}
                </p>
                <div className="mt-4 grid gap-3 text-sm md:grid-cols-2">
                  <div>
                    <div className="text-slate-500">插件 slug</div>
                    <div className="mt-1 font-mono text-slate-300">{detailSnapshot?.plugin_slug ?? '-'}</div>
                  </div>
                  <div>
                    <div className="text-slate-500">分区</div>
                    <div className="mt-1 text-slate-300">{detailSnapshot?.zone_slug ?? '-'}</div>
                  </div>
                  <div className="md:col-span-2">
                    <div className="text-slate-500">仓库</div>
                    {detailSnapshot?.repo_url ? (
                      <a
                        href={detailSnapshot.repo_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-1 inline-flex items-center gap-1 break-all text-primary hover:text-primary/80"
                      >
                        <Github className="h-4 w-4 shrink-0" />
                        {detailSnapshot.repo_url}
                        <ExternalLink className="h-3 w-3 shrink-0" />
                      </a>
                    ) : (
                      <div className="mt-1 text-slate-300">-</div>
                    )}
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {(detailSnapshot?.tags ?? []).map((tag) => (
                    <span key={tag} className="rounded-md border border-slate-800 bg-slate-950 px-2 py-1 text-xs text-slate-400">
                      {tag}
                    </span>
                  ))}
                </div>
              </section>

              <section className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <h3 className="flex items-center gap-2 font-semibold text-white">
                    <MessageSquare className="h-4 w-4 text-primary" />
                    审核意见
                  </h3>
                  {submissionDetail?.review_counts && (
                    <div className="text-xs text-slate-500">
                      未解决 {submissionDetail.review_counts.unresolved}
                    </div>
                  )}
                </div>
                {detailComments.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-slate-800 p-5 text-center text-sm text-slate-500">
                    暂无审核意见
                  </div>
                ) : (
                  <div className="space-y-3">
                    {detailComments.map((comment) => (
                      <div key={comment.id} className="rounded-lg border border-slate-800 bg-[#151527] p-3">
                        <div className="mb-2 flex flex-wrap items-center gap-2">
                          <Badge variant="outline" className={severityClass(comment.severity)}>
                            {comment.severity}
                          </Badge>
                          <span className="text-xs text-slate-500">{comment.target_area}</span>
                          {comment.target_ref && <span className="text-xs text-slate-500">{comment.target_ref}</span>}
                          {comment.is_resolved && (
                            <Badge variant="outline" className="border-green-500/30 bg-green-500/10 text-green-300">
                              已解决
                            </Badge>
                          )}
                        </div>
                        <p className="whitespace-pre-wrap text-sm leading-6 text-slate-300">{comment.body}</p>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <section className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
                <h3 className="mb-3 font-semibold text-white">处理记录</h3>
                {!submissionDetail?.events.length ? (
                  <div className="text-sm text-slate-500">暂无记录</div>
                ) : (
                  <div className="space-y-3">
                    {submissionDetail.events.map((event) => (
                      <div key={event.id} className="flex items-start gap-3 text-sm">
                        <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-primary" />
                        <div>
                          <div className="text-slate-300">{event.event_type}</div>
                          <div className="text-xs text-slate-500">{formatDate(event.created_at)}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              {submissionDetail?.plugin_id && submissionDetail.decision === 'approved' && (
                <div className="flex justify-end">
                  <Link to={`/plugin/${submissionDetail.plugin_id}`}>
                    <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
                      查看已发布插件
                    </Button>
                  </Link>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </main>
  );
}
