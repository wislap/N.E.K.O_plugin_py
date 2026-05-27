import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Search, Github, Menu, X, Cat, LogOut, Package, Upload, ShieldCheck, Bell } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { authApi } from '@/services/auth';
import { notificationsApi } from '@/services/notifications';
import type { Notification, User as ApiUser } from '@/services/types';
import { adminApi, hasAnyAdminAccess } from '@/services/adminApi';
import { logError, reportError } from '@/lib/error-reporting';

export function Header() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentUser, setCurrentUser] = useState<ApiUser | null>(null);
  const [canAccessAdmin, setCanAccessAdmin] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function fetchNotifications(options: { includeList?: boolean } = {}) {
      if (!currentUser) {
        setNotifications([]);
        setUnreadCount(0);
        return;
      }

      try {
        const includeList = options.includeList ?? notifications.length > 0;
        const [items, unread] = await Promise.all([
          includeList ? notificationsApi.list(8) : Promise.resolve(null),
          notificationsApi.unreadCount()
        ]);
        if (isMounted) {
          if (items) {
            setNotifications(items);
          }
          setUnreadCount(unread.count);
        }
      } catch (error) {
        logError(error, {
          title: '通知加载失败',
          severity: 'warn',
          context: {
            module: 'header',
            action: 'fetchNotifications'
          }
        });
        if (isMounted) {
          setNotifications([]);
          setUnreadCount(0);
        }
      }
    }

    const fetchUnreadIfVisible = () => {
      if (document.visibilityState === 'visible') {
        void fetchNotifications();
      }
    };
    const fetchAllNotifications = () => {
      if (document.visibilityState === 'visible') {
        void fetchNotifications({ includeList: true });
      }
    };

    fetchUnreadIfVisible();
    const timer = window.setInterval(fetchUnreadIfVisible, 90000);
    window.addEventListener('notifications:changed', fetchAllNotifications);
    document.addEventListener('visibilitychange', fetchUnreadIfVisible);

    return () => {
      isMounted = false;
      window.clearInterval(timer);
      window.removeEventListener('notifications:changed', fetchAllNotifications);
      document.removeEventListener('visibilitychange', fetchUnreadIfVisible);
    };
  }, [currentUser, notifications.length]);

  useEffect(() => {
    let isMounted = true;

    async function syncUser() {
      const token = localStorage.getItem('token');
      if (!token) {
        setCurrentUser(null);
        setCanAccessAdmin(false);
        return;
      }

      const cached = localStorage.getItem('currentUser');
      if (cached) {
        try {
          setCurrentUser(JSON.parse(cached) as ApiUser);
        } catch (error) {
          logError(error, {
            title: '本地用户缓存解析失败',
            severity: 'warn',
            context: {
              module: 'header',
              action: 'parseCachedUser'
            }
          });
          localStorage.removeItem('currentUser');
        }
      }

      try {
        const [user, permissions] = await Promise.all([
          authApi.getCurrentUser(),
          adminApi.getMyPermissions().catch(() => null)
        ]);
        if (isMounted) {
          setCurrentUser(user);
          setCanAccessAdmin(hasAnyAdminAccess(permissions));
          localStorage.setItem('currentUser', JSON.stringify(user));
        }
      } catch (error) {
        logError(error, {
          title: '登录状态同步失败',
          severity: 'warn',
          context: {
            module: 'header',
            action: 'syncUser'
          }
        });
        if (isMounted) {
          setCurrentUser(null);
          setCanAccessAdmin(false);
          localStorage.removeItem('token');
          localStorage.removeItem('refreshToken');
          localStorage.removeItem('currentUser');
        }
      }
    }

    syncUser();
    window.addEventListener('auth:changed', syncUser);
    window.addEventListener('storage', syncUser);

    return () => {
      isMounted = false;
      window.removeEventListener('auth:changed', syncUser);
      window.removeEventListener('storage', syncUser);
    };
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/plugins?search=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  const navLinks = [
    { label: '首页', href: '/' },
    { label: '插件', href: '/plugins' },
    { label: '上传', href: '/upload' },
    { label: '文档', href: 'https://project-neko.online/plugins/', external: true },
  ];
  const authedNavLinks = currentUser
    ? [...navLinks.slice(0, 3), { label: '我的插件', href: '/my/plugins' }, navLinks[3]]
    : navLinks;

  const logout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      logError(error, {
        title: '登出同步失败',
        severity: 'warn',
        context: {
          module: 'header',
          action: 'logout'
        }
      });
    }
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('currentUser');
    setCurrentUser(null);
    setNotifications([]);
    setUnreadCount(0);
    window.dispatchEvent(new Event('auth:changed'));
    navigate('/');
  };

  const openNotification = async (notification: Notification) => {
    if (!notification.is_read) {
      try {
        await notificationsApi.markRead(notification.id);
      } catch (error) {
        logError(error, {
          title: '通知标记已读失败',
          severity: 'warn',
          context: {
            module: 'header',
            action: 'markNotificationRead',
            notificationId: notification.id
          }
        });
      }
      setUnreadCount((count) => Math.max(0, count - 1));
      setNotifications((items) =>
        items.map((item) =>
          item.id === notification.id ? { ...item, is_read: true } : item
        )
      );
    }

    if (notification.target_url) {
      navigate(notification.target_url);
    }
  };

  const markAllNotificationsRead = async () => {
    try {
      await notificationsApi.markAllRead();
      setUnreadCount(0);
      setNotifications((items) => items.map((item) => ({ ...item, is_read: true })));
    } catch (error) {
      reportError(error, {
        title: '全部通知标记已读失败',
        context: {
          module: 'header',
          action: 'markAllNotificationsRead'
        }
      });
    }
  };

  const userLabel = currentUser?.display_name || currentUser?.username;
  const userInitial = userLabel?.slice(0, 1).toUpperCase() || 'U';

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled
          ? 'bg-[#0F0F1A]/90 backdrop-blur-lg shadow-lg'
          : 'bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center group-hover:shadow-[0_0_20px_oklch(var(--primary)/0.5)] transition-shadow">
              <Cat className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
              N.E.K.O.
            </span>
          </Link>

          {/* Desktop Search */}
          <form onSubmit={handleSearch} className="hidden md:flex flex-1 max-w-md mx-8">
            <div className="relative w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                type="text"
                placeholder="搜索插件..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-[#1A1A2E] border-slate-700 text-slate-200 placeholder:text-slate-500 focus:border-ring focus:ring-ring/20 rounded-full"
              />
            </div>
          </form>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {authedNavLinks.map((link) => (
              link.external ? (
                <a
                  key={link.label}
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white transition-colors rounded-lg hover:bg-white/5"
                >
                  {link.label}
                </a>
              ) : (
                <Link
                  key={link.label}
                  to={link.href}
                  className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white transition-colors rounded-lg hover:bg-white/5"
                >
                  {link.label}
                </Link>
              )
            ))}
            <a
              href="https://github.com/Project-N-E-K-O/N.E.K.O"
              target="_blank"
              rel="noopener noreferrer"
              className="ml-2 p-2 text-slate-300 hover:text-white transition-colors rounded-lg hover:bg-white/5"
            >
              <Github className="w-5 h-5" />
            </a>
            {currentUser ? (
              <div className="ml-2 flex items-center gap-2">
                <DropdownMenu onOpenChange={(open) => {
                  if (open) {
                    window.dispatchEvent(new Event('notifications:changed'));
                  }
                }}>
                  <DropdownMenuTrigger asChild>
                    <button
                      type="button"
                      className="relative rounded-full border border-white/10 bg-white/5 p-2 text-slate-300 transition-colors hover:border-primary/40 hover:bg-white/10 hover:text-white focus:outline-none focus:ring-2 focus:ring-primary/40"
                      aria-label="打开通知"
                    >
                      <Bell className="h-5 w-5" />
                      {unreadCount > 0 && (
                        <span className="absolute -right-1 -top-1 min-w-5 rounded-full bg-primary px-1.5 text-center text-[10px] font-bold leading-5 text-primary-foreground">
                          {unreadCount > 99 ? '99+' : unreadCount}
                        </span>
                      )}
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    align="end"
                    sideOffset={10}
                    className="w-80 border-slate-800 bg-[#111827]/95 p-2 text-slate-200 shadow-2xl shadow-black/40 backdrop-blur-xl"
                  >
                    <DropdownMenuLabel className="flex items-center justify-between px-3 py-2">
                      <span>通知</span>
                      {unreadCount > 0 && (
                        <button
                          type="button"
                          onClick={markAllNotificationsRead}
                          className="text-xs font-normal text-primary hover:text-primary/80"
                        >
                          全部已读
                        </button>
                      )}
                    </DropdownMenuLabel>
                    <DropdownMenuSeparator className="bg-slate-800" />
                    {notifications.length === 0 ? (
                      <div className="px-3 py-8 text-center text-sm text-slate-500">
                        暂无通知
                      </div>
                    ) : (
                      notifications.map((notification) => (
                        <DropdownMenuItem
                          key={notification.id}
                          className="cursor-pointer items-start rounded-lg px-3 py-3 text-slate-300 focus:bg-white/10 focus:text-white"
                          onClick={() => openNotification(notification)}
                        >
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              {!notification.is_read && (
                                <span className="h-2 w-2 shrink-0 rounded-full bg-primary" />
                              )}
                              <span className="truncate text-sm font-medium text-white">
                                {notification.title}
                              </span>
                            </div>
                            {notification.content && (
                              <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-400">
                                {notification.content}
                              </p>
                            )}
                          </div>
                        </DropdownMenuItem>
                      ))
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button
                      type="button"
                      className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 p-1 pr-3 text-sm text-slate-200 transition-colors hover:border-primary/40 hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-primary/40"
                      aria-label="打开用户菜单"
                    >
                      <Avatar className="h-8 w-8">
                        <AvatarImage src={currentUser.avatar_url ?? undefined} alt={userLabel} />
                        <AvatarFallback className="bg-primary text-primary-foreground text-sm">
                          {userInitial}
                        </AvatarFallback>
                      </Avatar>
                      <span className="hidden max-w-28 truncate lg:inline">{userLabel}</span>
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    align="end"
                    sideOffset={10}
                    className="w-64 border-slate-800 bg-[#111827]/95 p-2 text-slate-200 shadow-2xl shadow-black/40 backdrop-blur-xl"
                  >
                  <DropdownMenuLabel className="px-3 py-2">
                    <div className="flex items-center gap-3">
                      <Avatar className="h-10 w-10">
                        <AvatarImage src={currentUser.avatar_url ?? undefined} alt={userLabel} />
                        <AvatarFallback className="bg-primary text-primary-foreground">
                          {userInitial}
                        </AvatarFallback>
                      </Avatar>
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold text-white">{userLabel}</div>
                        <div className="truncate text-xs font-normal text-slate-400">{currentUser.email}</div>
                      </div>
                    </div>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator className="bg-slate-800" />
                  <DropdownMenuItem
                    className="cursor-pointer rounded-lg px-3 py-2 text-slate-300 focus:bg-white/10 focus:text-white"
                    onClick={() => navigate('/my/plugins')}
                  >
                    <Package className="h-4 w-4" />
                    我的插件
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="cursor-pointer rounded-lg px-3 py-2 text-slate-300 focus:bg-white/10 focus:text-white"
                    onClick={() => navigate('/upload')}
                  >
                    <Upload className="h-4 w-4" />
                    上传插件
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="cursor-pointer rounded-lg px-3 py-2 text-slate-300 focus:bg-white/10 focus:text-white"
                    onClick={logout}
                  >
                    <LogOut className="h-4 w-4" />
                    退出登录
                  </DropdownMenuItem>
                  {canAccessAdmin && (
                    <>
                      <DropdownMenuSeparator className="bg-slate-800" />
                      <DropdownMenuItem
                        className="cursor-pointer rounded-lg border border-primary/20 bg-primary/10 px-3 py-2 text-primary focus:bg-primary/20 focus:text-primary"
                        onClick={() => navigate('/admin')}
                      >
                        <ShieldCheck className="h-4 w-4" />
                        管理员面板
                      </DropdownMenuItem>
                    </>
                  )}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            ) : (
              <div className="ml-2 flex items-center gap-2">
                <Link to="/login">
                  <Button variant="ghost" className="text-slate-300 hover:text-white hover:bg-white/5">
                    登录
                  </Button>
                </Link>
                <Link to="/register">
                  <Button className="bg-primary hover:bg-primary/90 text-primary-foreground">
                    注册
                  </Button>
                </Link>
              </div>
            )}
          </nav>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden p-2 text-slate-300 hover:text-white"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-slate-800">
            <form onSubmit={handleSearch} className="mb-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  type="text"
                  placeholder="搜索插件..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-[#1A1A2E] border-slate-700 text-slate-200 placeholder:text-slate-500 rounded-lg"
                />
              </div>
            </form>
            <nav className="flex flex-col gap-2">
              {authedNavLinks.map((link) => (
                link.external ? (
                  <a
                    key={link.label}
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                  >
                    {link.label}
                  </a>
                ) : (
                  <Link
                    key={link.label}
                    to={link.href}
                    className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    {link.label}
                  </Link>
                )
              ))}
              <a
                href="https://github.com/Project-N-E-K-O/N.E.K.O"
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white hover:bg-white/5 rounded-lg transition-colors flex items-center gap-2"
              >
                <Github className="w-4 h-4" />
                GitHub
              </a>
              {currentUser ? (
                <>
                  {canAccessAdmin && (
                    <Link
                      to="/admin"
                      onClick={() => setIsMobileMenuOpen(false)}
                      className="px-4 py-2 text-sm font-medium text-primary hover:text-primary hover:bg-primary/10 rounded-lg transition-colors flex items-center gap-2"
                    >
                      <ShieldCheck className="w-4 h-4" />
                      管理员面板
                    </Link>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      logout();
                      setIsMobileMenuOpen(false);
                    }}
                    className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white hover:bg-white/5 rounded-lg transition-colors flex items-center gap-2"
                  >
                    <LogOut className="w-4 h-4" />
                    退出登录
                  </button>
                </>
              ) : (
                <div className="grid grid-cols-2 gap-2 px-4 pt-2">
                  <Link
                    to="/login"
                    onClick={() => setIsMobileMenuOpen(false)}
                    className="rounded-lg border border-slate-700 px-3 py-2 text-center text-sm text-slate-300 hover:bg-white/5"
                  >
                    登录
                  </Link>
                  <Link
                    to="/register"
                    onClick={() => setIsMobileMenuOpen(false)}
                    className="rounded-lg bg-primary px-3 py-2 text-center text-sm text-primary-foreground"
                  >
                    注册
                  </Link>
                </div>
              )}
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}
