import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Cat, Loader2, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getErrorMessage, reportError } from '@/lib/error-reporting';
import { post } from '@/services/api';

interface OAuthAuthorizeResponse {
  redirect_url: string;
  expires_in: number;
}

function paramValue(params: URLSearchParams, key: string): string {
  return params.get(key)?.trim() || '';
}

export function OAuthAuthorize() {
  const location = useLocation();
  const navigate = useNavigate();
  const [redirectUrl, setRedirectUrl] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [isAuthorizing, setIsAuthorizing] = useState(true);

  const params = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const payload = useMemo(() => ({
    client_id: paramValue(params, 'client_id'),
    redirect_uri: paramValue(params, 'redirect_uri'),
    state: paramValue(params, 'state'),
    code_challenge: paramValue(params, 'code_challenge'),
    code_challenge_method: paramValue(params, 'code_challenge_method') || 'S256',
    response_type: paramValue(params, 'response_type') || 'code',
    scope: paramValue(params, 'scope') || 'read write',
  }), [params]);
  const missingParams = useMemo(
    () => ['client_id', 'redirect_uri', 'state', 'code_challenge']
      .filter((key) => !payload[key as keyof typeof payload]),
    [payload],
  );
  const validationError = missingParams.length > 0
    ? `OAuth 请求缺少参数：${missingParams.join(', ')}`
    : '';
  const showAuthorizing = isAuthorizing && !validationError;

  useEffect(() => {
    const token = localStorage.getItem('token');
    const next = `${location.pathname}${location.search}`;
    if (!token) {
      navigate(`/login?next=${encodeURIComponent(next)}`, { replace: true });
      return;
    }

    if (validationError) return;

    let cancelled = false;
    async function authorize() {
      setIsAuthorizing(true);
      setErrorMessage('');
      try {
        const response = await post<OAuthAuthorizeResponse>('/oauth/authorize/accept', payload);
        if (cancelled) return;
        setRedirectUrl(response.redirect_url);
        window.location.href = response.redirect_url;
      } catch (error) {
        if (cancelled) return;
        setErrorMessage(getErrorMessage(error, '授权失败，请稍后重试。'));
        reportError(error, {
          title: 'OAuth 授权失败',
          context: { module: 'oauth', action: 'authorizeDesktop' }
        });
      } finally {
        if (!cancelled) setIsAuthorizing(false);
      }
    }

    void authorize();
    return () => {
      cancelled = true;
    };
  }, [location.pathname, location.search, navigate, payload, validationError]);

  return (
    <main className="min-h-screen bg-[#0F0F1A] pt-24 pb-20">
      <div className="mx-auto flex max-w-lg flex-col items-center px-4 text-center sm:px-6">
        <Link to="/" className="mb-8 flex items-center justify-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent">
            <Cat className="h-6 w-6 text-white" />
          </div>
          <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-2xl font-bold text-transparent">
            N.E.K.O.
          </span>
        </Link>

        <div className="w-full rounded-2xl border border-slate-800/80 bg-[#1A1A2E]/90 p-8 shadow-2xl">
          <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15 text-primary">
            {showAuthorizing ? <Loader2 className="h-7 w-7 animate-spin" /> : <ShieldCheck className="h-7 w-7" />}
          </div>
          <h1 className="mb-3 text-2xl font-semibold text-white">
            授权 N.E.K.O 桌面端
          </h1>
          <p className="mb-6 text-sm leading-6 text-slate-300">
            Market 正在为本地插件管理器签发登录授权。完成后浏览器会尝试唤起 N.E.K.O。
          </p>

          {validationError || errorMessage ? (
            <div className="mb-6 rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">
              {validationError || errorMessage}
            </div>
          ) : null}

          {redirectUrl ? (
            <Button className="w-full" onClick={() => { window.location.href = redirectUrl; }}>
              重新打开 N.E.K.O
            </Button>
          ) : (
            <Button className="w-full" disabled>
              {showAuthorizing ? '正在授权...' : '等待授权'}
            </Button>
          )}
        </div>
      </div>
    </main>
  );
}
