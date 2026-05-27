import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle2, MailCheck, RefreshCcw, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { authApi } from '@/services/auth';
import { getErrorMessage, notifySuccess, reportError } from '@/lib/error-reporting';
import type { User } from '@/services/types';

type VerifyState = 'checking' | 'success' | 'error' | 'idle';

const verificationRequests = new Map<string, Promise<User>>();

function verifyEmailOnce(token: string) {
  const existing = verificationRequests.get(token);
  if (existing) {
    return existing;
  }

  const request = authApi.verifyEmail(token).catch((error) => {
    verificationRequests.delete(token);
    throw error;
  });
  verificationRequests.set(token, request);
  return request;
}

export function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') ?? '';
  const emailParam = searchParams.get('email') ?? '';
  const [state, setState] = useState<VerifyState>(token ? 'checking' : 'idle');
  const [message, setMessage] = useState(token ? '正在验证邮箱...' : '验证链接缺少 token');
  const [email, setEmail] = useState(emailParam);
  const [isResending, setIsResending] = useState(false);

  useEffect(() => {
    if (!token) {
      setState('error');
      return;
    }

    let cancelled = false;
    verifyEmailOnce(token)
      .then((user) => {
        if (cancelled) return;
        setState('success');
        setMessage(`邮箱 ${user.email} 验证成功，现在可以登录插件市场。`);
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

  const resend = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!email.trim()) {
      setMessage('请输入注册邮箱后再重发验证邮件。');
      return;
    }

    setIsResending(true);
    try {
      const response = await authApi.resendVerificationEmailPublic({ email: email.trim() });
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
            <Button onClick={() => navigate('/login')} className="bg-primary text-primary-foreground">
              前往登录
            </Button>
          ) : (
            <form onSubmit={resend} className="space-y-3 text-left">
              <div className="space-y-2">
                <Label htmlFor="verify-email-resend" className="text-slate-200">
                  注册邮箱
                </Label>
                <Input
                  id="verify-email-resend"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  className="border-slate-700 bg-slate-950/50 text-white"
                  required
                />
              </div>
              <Button
                type="submit"
                disabled={isResending}
                className="w-full gap-2 bg-primary text-primary-foreground"
              >
                <RefreshCcw className="h-4 w-4" />
                {isResending ? '发送中...' : '重新发送验证邮件'}
              </Button>
            </form>
          )}
          <Link to="/" className="text-sm text-slate-400 hover:text-white">
            返回首页
          </Link>
        </div>
      </section>
    </main>
  );
}
