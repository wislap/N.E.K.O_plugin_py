import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Download, Users, Package, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { stats as fallbackStats } from '@/data';
import { formatNumber } from '@/lib/utils';
import { isDebugDataEnabled } from '@/lib/debug';
import { marketApi } from '@/services/market';
import type { MarketStats } from '@/services/types';
import { logError } from '@/lib/error-reporting';

const emptyStats: MarketStats = {
  totalPlugins: 0,
  totalDownloads: 0,
  activeDevelopers: 0,
  newPluginsThisWeek: 0,
};

export function Hero() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [stats, setStats] = useState<MarketStats>(
    isDebugDataEnabled ? fallbackStats : emptyStats
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const primaryOklch = getComputedStyle(document.documentElement)
      .getPropertyValue('--primary')
      .trim();

    const probe = document.createElement('div');
    probe.style.position = 'fixed';
    probe.style.left = '-9999px';
    probe.style.top = '-9999px';
    probe.style.color = `oklch(${primaryOklch} / 1)`;
    document.body.appendChild(probe);

    const primaryColor = getComputedStyle(probe).color;

    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Particle system
    const particles: Array<{
      x: number;
      y: number;
      vx: number;
      vy: number;
      size: number;
      opacity: number;
    }> = [];

    for (let i = 0; i < 50; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        size: Math.random() * 2 + 1,
        opacity: Math.random() * 0.5 + 0.2,
      });
    }

    let animationId: number;

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      particles.forEach((particle) => {
        particle.x += particle.vx;
        particle.y += particle.vy;

        if (particle.x < 0 || particle.x > canvas.width) particle.vx *= -1;
        if (particle.y < 0 || particle.y > canvas.height) particle.vy *= -1;

        ctx.beginPath();
        ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
        ctx.globalAlpha = particle.opacity;
        ctx.fillStyle = primaryColor;
        ctx.fill();
        ctx.globalAlpha = 1;
      });

      // Draw connections
      particles.forEach((p1, i) => {
        particles.slice(i + 1).forEach((p2) => {
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 150) {
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.globalAlpha = 0.1 * (1 - dist / 150);
            ctx.strokeStyle = primaryColor;
            ctx.stroke();
            ctx.globalAlpha = 1;
          }
        });
      });

      animationId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      cancelAnimationFrame(animationId);
      probe.remove();
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    marketApi.getStats()
      .then((data) => {
        if (isMounted) {
          setStats(data);
        }
      })
      .catch((error) => {
        logError(error, {
          title: '首页统计加载失败',
          severity: 'warn',
          context: {
            module: 'home',
            action: 'loadMarketStats',
            fallbackEnabled: isDebugDataEnabled
          }
        });
        if (isMounted && isDebugDataEnabled) {
          setStats(fallbackStats);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const statItems = [
    { icon: Package, value: stats.totalPlugins, label: '插件总数' },
    { icon: Download, value: stats.totalDownloads, label: '总下载量' },
    { icon: Users, value: stats.activeDevelopers, label: '活跃开发者' },
  ];

  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#0F0F1A] via-[#1a0f2e] to-[#0F0F1A]" />

      {/* Particle canvas */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 pointer-events-none"
      />

      {/* Gradient orbs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-[128px]" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent/20 rounded-full blur-[128px]" />

      {/* Content */}
      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-32 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary/10 border border-primary/20 rounded-full mb-8">
          <Sparkles className="w-4 h-4 text-primary" />
          <span className="text-sm text-primary/80">
            本周新增 {stats.newPluginsThisWeek} 个插件
          </span>
        </div>

        <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold mb-6">
          <span className="bg-gradient-to-r from-white via-primary/30 to-accent/30 bg-clip-text text-transparent">
            N.E.K.O.
          </span>
          <br />
          <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
            插件市场
          </span>
        </h1>

        <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto mb-10">
          扩展你的 AI 伙伴，让 N.E.K.O. 更强大。
          <br />
          发现、分享和安装社区创作的插件。
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
          <Link to="/plugins">
            <Button
              size="lg"
                className="bg-gradient-to-r from-primary to-accent hover:opacity-95 text-primary-foreground px-8 py-6 text-lg rounded-xl shadow-[0_0_30px_oklch(var(--primary)/0.3)] hover:shadow-[0_0_40px_oklch(var(--primary)/0.5)] transition-all"
            >
              浏览插件
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
          </Link>
          <Link to="/upload">
            <Button
              size="lg"
              variant="outline"
              className="border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white px-8 py-6 text-lg rounded-xl"
            >
              上传插件
            </Button>
          </Link>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-8 max-w-2xl mx-auto">
          {statItems.map((item) => (
            <div key={item.label} className="text-center">
              <div className="flex items-center justify-center gap-2 mb-2">
                <item.icon className="w-5 h-5 text-primary" />
                <span className="text-2xl sm:text-3xl font-bold text-white">
                  {formatNumber(item.value)}
                </span>
              </div>
              <span className="text-sm text-slate-500">{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
