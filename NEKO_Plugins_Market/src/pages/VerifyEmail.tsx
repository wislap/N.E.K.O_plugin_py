import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle2, MailCheck, RefreshCcw, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { authApi } from '@/services/auth';
import { getErrorMessage, notifySuccess, reportError } from '@/lib/error-reporting';

type VerifyState = 'checking' | 'success' | 'error' | 'idle';

export function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') ?? '';
  const [state, setState] = useState<VerifyState>(token ? 'checking' : 'idle');
  const [message, setMessage] = useState(token ? '正在验证邮箱...' : '验证链接缺少 token');
  const [isResending, setIsResending] = useState(false);

  useEffect(() => {
    if (!token) {
      setState('error');
      return;
    }

    let cancelled = false;
    authApi.verifyEmail(token)
      .then((user) => {
        if (cancelled) return;
        localStorage.setItem('currentUser', JSON.stringify(user));
        window.dispatchEvent(new Event('auth:changed'));
        setState('success');
        setMessage('邮箱验证成功，可以继续使用插件市场。');
        notifySuccess('邮箱验证成功');
      })
      .catch((error) => {
        if (cancelled) return;
        setState('error');
        setMessage(getErrorMessage(error, '邮箱验证失败，请重新发送验证邮件。'));
        reportError(error, {
          title: '邮箱验证失败',
          context: { module: 'auth', action: 'verifyEmail' }
        });
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  const resend = async () => {
    setIsResending(true);
    try {
      const response = await authApi.resendVerificationEmail();
      setMessage(response.message);
      notifySuccess(response.message);
    } catch (error) {
      const errorMessage = getErrorMessage(error, '重发验证邮件失败');
      setMessage(errorMessage);
      reportError(error, {
        title: '重发验证邮件失败',
        context: { module: 'auth', action: 'resendVerificationEmail' }
      });
    } finally {
      setIsResending(false);
    }
  };

  const icon = state === 'success'
    ? <CheckCircle2 className="h-12 w-12 text-emerald-300" />
    : state === 'error'
      ? <XCircle className="h-12 w-12 text-red-300" />
      : <MailCheck className="h-12 w-12 text-primary" />;

  return (
    <main className="min-h-screen bg-[#0F0F1A] px-4 py-28">
      <section className="mx-auto max-w-md rounded-2xl border border-slate-800/60 bg-[#1A1A2E] p-6 text-center shadow-xl">
        <div className="mb-4 flex justify-center">{icon}</div>
        <h1 className="text-2xl font-bold text-white">邮箱验证</h1>
        <p className="mt-3 text-sm leading-6 text-slate-300">{message}</p>

        <div className="mt-6 flex flex-col gap-3">
          {state === 'success' ? (
            <Button onClick={() => navigate('/upload')} className="bg-primary text-primary-foreground">
              继续提交插件
            </Button>
          ) : (
            <Button
              type="button"
              onClick={resend}
              disabled={isResending}
              className="gap-2 bg-primary text-primary-foreground"
            >
              <RefreshCcw className="h-4 w-4" />
              {isResending ? '发送中...' : '重新发送验证邮件'}
            </Button>
          )}
          <Link to="/" className="text-sm text-slate-400 hover:text-white">
            返回首页
          </Link>
        </div>
      </section>
    </main>
  );
}
