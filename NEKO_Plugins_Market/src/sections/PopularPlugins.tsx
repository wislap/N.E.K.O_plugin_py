import { Link } from 'react-router-dom';
import { ArrowRight, TrendingUp } from 'lucide-react';
import { PluginCard } from '@/components/PluginCard';
import { getPopularPlugins } from '@/data';
import { Button } from '@/components/ui/button';

export function PopularPlugins() {
  const plugins = getPopularPlugins(6);

  return (
    <section className="py-20 bg-[#0a0a12]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-12">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="w-5 h-5 text-primary" />
              <span className="text-sm text-primary font-medium">热门</span>
            </div>
            <h2 className="text-3xl font-bold text-white">
              热门插件
            </h2>
          </div>
          <Link to="/plugins?sort=downloads">
            <Button variant="ghost" className="text-slate-400 hover:text-white group">
              查看全部
              <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
            </Button>
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {plugins.map((plugin) => (
            <PluginCard key={plugin.id} plugin={plugin} />
          ))}
        </div>
      </div>
    </section>
  );
}
