import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Cat, Eye, EyeOff, Lock, Mail, Sparkles, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { authApi } from '@/services/auth';
import { softReveal } from '@/lib/animations';
import { isDebugAuthEnabled } from '@/lib/debug';
import { getErrorMessage, notifySuccess, reportError } from '@/lib/error-reporting';

type AuthMode = 'login' | 'register';

const PASSWORD_SYMBOLS = '!@#$%&*?';
const COMMON_LEAKED_PASSWORDS = new Set([
  '123456',
  '12345678',
  '123456789',
  'password',
  'password123',
  'qwerty',
  '111111',
  'admin123',
  'root',
  'root123'
]);

function createStrongPassword() {
  const groups = [
    'ABCDEFGHJKLMNPQRSTUVWXYZ',
    'abcdefghijkmnopqrstuvwxyz',
    '23456789',
    PASSWORD_SYMBOLS
  ];
  const allChars = groups.join('');
  const values = new Uint32Array(18);
  crypto.getRandomValues(values);

  const chars = groups.map((group, index) => group[values[index] % group.length]);
  for (let index = chars.length; index < values.length; index += 1) {
    chars.push(allChars[values[index] % allChars.length]);
  }

  return chars
    .map((char, index) => ({ char, sort: values[index] }))
    .sort((left, right) => left.sort - right.sort)
    .map(({ char }) => char)
    .join('');
}

function storeSession(response: Awaited<ReturnType<typeof authApi.login>>) {
  localStorage.setItem('token', response.access_token);
  localStorage.setItem('refreshToken', response.refresh_token);
  localStorage.setItem('currentUser', JSON.stringify(response.user));
  window.dispatchEvent(new Event('auth:changed'));
}

export function Auth() {
  const location = useLocation();
  const navigate = useNavigate();
  const searchParams = new URLSearchParams(location.search);
  const requestedNext = searchParams.get('next') || '/upload';
  const nextPath = requestedNext.startsWith('/') && !requestedNext.startsWith('//') ? requestedNext : '/upload';
  const nextQuery = `?next=${encodeURIComponent(nextPath)}`;
  const [mode, setMode] = useState<AuthMode>(location.pathname === '/register' ? 'register' : 'login');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const nextMode = location.pathname === '/register' ? 'register' : 'login';
    setMode(nextMode);
    setErrorMessage('');
  }, [location.pathname]);

  const submit = async (event: React.FormEvent, targetMode: AuthMode) => {
    event.preventDefault();
    setErrorMessage('');
    const password = targetMode === 'login' ? loginPassword : registerPassword;

    if (targetMode === 'register' && COMMON_LEAKED_PASSWORDS.has(password.trim().toLowerCase())) {
      setErrorMessage('这个密码过于常见，建议使用“生成强密码”后再注册。');
      return;
    }

    setIsSubmitting(true);

    try {
      const response = targetMode === 'login'
        ? await authApi.login({ username, password })
        : await authApi.register({
            username,
            email,
            password,
            display_name: displayName.trim() || undefined
      });

      storeSession(response);
      notifySuccess(targetMode === 'login' ? '登录成功' : '注册成功', {
        description: targetMode === 'register'
          ? response.verification_email_sent
            ? '验证邮件已发送，请检查邮箱。'
            : '账号已创建；当前邮件服务未启用，可稍后在账号内重发验证邮件。'
          : undefined,
        context: {
          module: 'auth',
          action: targetMode
        }
      });
      navigate(nextPath, { replace: true });
    } catch (error) {
      const message = getErrorMessage(error, '操作失败，请稍后重试');
      setErrorMessage(message);
      reportError(error, {
        title: targetMode === 'login' ? '登录失败' : '注册失败',
        context: {
          module: 'auth',
          action: targetMode,
          username,
          email: targetMode === 'register' ? email : undefined
        }
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const generatePassword = () => {
    setRegisterPassword(createStrongPassword());
    setShowPassword(true);
    setErrorMessage('');
  };

  const debugLogin = async () => {
    setErrorMessage('');
    setIsSubmitting(true);

    try {
      const response = await authApi.debugLogin();
      storeSession(response);
      notifySuccess('调试登录成功', {
        context: {
          module: 'auth',
          action: 'debugLogin'
        }
      });
      navigate(nextPath, { replace: true });
    } catch (error) {
      const message = getErrorMessage(error, '调试登录失败');
      setErrorMessage(message);
      reportError(error, {
        title: '调试登录失败',
        context: {
          module: 'auth',
          action: 'debugLogin'
        }
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const isRegister = mode === 'register';

  return (
    <main className="min-h-screen bg-[#0F0F1A] pt-24 pb-20">
      <div className="max-w-md mx-auto px-4 sm:px-6">
        <Link to="/" className="flex items-center justify-center gap-3 mb-8">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
            <Cat className="w-6 h-6 text-white" />
          </div>
          <span className="text-2xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
            N.E.K.O.
          </span>
        </Link>

        <div className="bg-[#1A1A2E] border border-slate-800/50 rounded-2xl p-6 shadow-xl overflow-hidden">
          <div className="mb-6 flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-white">
                {isRegister ? '创建账号' : '登录账号'}
              </h1>
              <p className="text-sm text-slate-400 mt-2">
                {isRegister ? '注册后即可提交插件进入审核流程' : '登录后可以上传插件并管理提交记录'}
              </p>
            </div>

            <div className="relative grid w-32 shrink-0 grid-cols-2 rounded-full bg-[#0F0F1A] p-1">
              <motion.div
                layout
                className={`absolute bottom-1 top-1 w-[calc(50%-4px)] rounded-full bg-primary ${
                  isRegister ? 'left-[calc(50%+0px)]' : 'left-1'
                }`}
                transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
              />
              <Link
                to={`/login${nextQuery}`}
                className={`relative z-10 rounded-full px-3 py-1.5 text-center text-sm font-medium transition-colors ${
                  !isRegister ? 'text-primary-foreground' : 'text-slate-400 hover:text-white'
                }`}
              >
                登录
              </Link>
              <Link
                to={`/register${nextQuery}`}
                className={`relative z-10 rounded-full px-3 py-1.5 text-center text-sm font-medium transition-colors ${
                  isRegister ? 'text-primary-foreground' : 'text-slate-400 hover:text-white'
                }`}
              >
                注册
              </Link>
            </div>
          </div>

          <AnimatePresence>
            {errorMessage && (
              <motion.div
                variants={softReveal}
                initial="initial"
                animate="animate"
                exit="exit"
                className="mb-4 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300"
              >
                {errorMessage}
              </motion.div>
            )}
          </AnimatePresence>

          <div className="overflow-hidden">
            <motion.div
              className="flex"
              animate={{ x: isRegister ? '-100%' : '0%' }}
              transition={{ duration: 0.34, ease: [0.22, 1, 0.36, 1] }}
            >
              <form
                onSubmit={(event) => submit(event, 'login')}
                className="min-w-full space-y-4 pr-0"
                aria-hidden={isRegister}
                autoComplete="on"
              >
                <div className="space-y-2">
                  <Label htmlFor="username" className="text-slate-300">
                    用户名
                  </Label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                    <Input
                      id="username"
                      name="username"
                      value={username}
                      onChange={(event) => setUsername(event.target.value)}
                      placeholder="用户名或邮箱"
                      className="pl-10 bg-[#0F0F1A] border-slate-700 text-slate-200"
                      autoComplete="username"
                      required
                      tabIndex={isRegister ? -1 : 0}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password" className="text-slate-300">
                    密码
                  </Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                    <Input
                      id="password"
                      name="current-password"
                      type={showPassword ? 'text' : 'password'}
                      value={loginPassword}
                      onChange={(event) => setLoginPassword(event.target.value)}
                      placeholder="请输入密码"
                      className="pl-10 pr-10 bg-[#0F0F1A] border-slate-700 text-slate-200"
                      autoComplete="current-password"
                      required
                      tabIndex={isRegister ? -1 : 0}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((value) => !value)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-200"
                      aria-label={showPassword ? '隐藏密码' : '显示密码'}
                      tabIndex={isRegister ? -1 : 0}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full bg-gradient-to-r from-primary to-accent hover:opacity-95 text-primary-foreground py-6"
                  tabIndex={isRegister ? -1 : 0}
                >
                  {isSubmitting && !isRegister ? '处理中...' : '登录'}
                </Button>
              </form>

              <form
                onSubmit={(event) => submit(event, 'register')}
                className="min-w-full space-y-4 pl-0"
                aria-hidden={!isRegister}
                autoComplete="on"
              >
                <div className="space-y-2">
                  <Label htmlFor="register-username" className="text-slate-300">
                    用户名
                  </Label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                    <Input
                      id="register-username"
                      name="username"
                      value={username}
                      onChange={(event) => setUsername(event.target.value)}
                      placeholder="至少 3 个字符"
                      className="pl-10 bg-[#0F0F1A] border-slate-700 text-slate-200"
                      autoComplete="username"
                      required
                      minLength={3}
                      tabIndex={isRegister ? 0 : -1}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email" className="text-slate-300">
                    邮箱
                  </Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                    <Input
                      id="email"
                      name="email"
                      type="email"
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      placeholder="you@example.com"
                      className="pl-10 bg-[#0F0F1A] border-slate-700 text-slate-200"
                      autoComplete="email"
                      required
                      tabIndex={isRegister ? 0 : -1}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="display-name" className="text-slate-300">
                    昵称
                  </Label>
                  <Input
                    id="display-name"
                    name="nickname"
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                    placeholder="可选"
                    className="bg-[#0F0F1A] border-slate-700 text-slate-200"
                    autoComplete="nickname"
                    tabIndex={isRegister ? 0 : -1}
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-3">
                    <Label htmlFor="register-password" className="text-slate-300">
                      密码
                    </Label>
                    <button
                      type="button"
                      onClick={generatePassword}
                      className="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary/80"
                      tabIndex={isRegister ? 0 : -1}
                    >
                      <Sparkles className="h-3.5 w-3.5" />
                      生成强密码
                    </button>
                  </div>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                    <Input
                      id="register-password"
                      name="new-password"
                      type={showPassword ? 'text' : 'password'}
                      value={registerPassword}
                      onChange={(event) => setRegisterPassword(event.target.value)}
                      placeholder="至少 6 个字符"
                      className="pl-10 pr-10 bg-[#0F0F1A] border-slate-700 text-slate-200"
                      autoComplete="new-password"
                      required
                      minLength={6}
                      tabIndex={isRegister ? 0 : -1}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((value) => !value)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-200"
                      aria-label={showPassword ? '隐藏密码' : '显示密码'}
                      tabIndex={isRegister ? 0 : -1}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full bg-gradient-to-r from-primary to-accent hover:opacity-95 text-primary-foreground py-6"
                  tabIndex={isRegister ? 0 : -1}
                >
                  {isSubmitting && isRegister ? '处理中...' : '注册并登录'}
                </Button>
              </form>
            </motion.div>
          </div>

          <div className="mt-5 text-center text-sm text-slate-400">
            {isRegister ? '已有账号？' : '还没有账号？'}
            <Link
              to={`${isRegister ? '/login' : '/register'}${nextQuery}`}
              className="ml-2 text-primary hover:text-primary/80"
            >
              {isRegister ? '去登录' : '去注册'}
            </Link>
          </div>

          {isDebugAuthEnabled && (
            <div className="mt-5 border-t border-slate-800/70 pt-5">
              <Button
                type="button"
                variant="outline"
                onClick={debugLogin}
                disabled={isSubmitting}
                className="w-full border-amber-500/30 bg-amber-500/10 text-amber-200 hover:bg-amber-500/15 hover:text-amber-100"
              >
                调试模式：一键登录
              </Button>
              <p className="mt-2 text-center text-xs text-slate-500">
                仅用于本地开发，关闭 VITE_DEBUG_AUTH 后隐藏。
              </p>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
