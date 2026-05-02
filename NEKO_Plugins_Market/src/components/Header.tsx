import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Search, Github, Menu, X, Cat, LogOut, Package, Upload, ShieldCheck } from 'lucide-react';
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
import { authApi, type User as ApiUser } from '@/services/api';

export function Header() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentUser, setCurrentUser] = useState<ApiUser | null>(null);
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

    async function syncUser() {
      const token = localStorage.getItem('token');
      if (!token) {
        setCurrentUser(null);
        return;
      }

      const cached = localStorage.getItem('currentUser');
      if (cached) {
        try {
          setCurrentUser(JSON.parse(cached) as ApiUser);
        } catch {
          localStorage.removeItem('currentUser');
        }
      }

      try {
        const user = await authApi.getCurrentUser();
        if (isMounted) {
          setCurrentUser(user);
          localStorage.setItem('currentUser', JSON.stringify(user));
        }
      } catch {
        if (isMounted) {
          setCurrentUser(null);
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

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('currentUser');
    setCurrentUser(null);
    window.dispatchEvent(new Event('auth:changed'));
    navigate('/');
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
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    className="ml-2 flex items-center gap-2 rounded-full border border-white/10 bg-white/5 p-1 pr-3 text-sm text-slate-200 transition-colors hover:border-primary/40 hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-primary/40"
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
                  {currentUser.is_admin && (
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
                  {currentUser.is_admin && (
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
