import { Link } from 'react-router-dom';
import { ArrowRight, Clock } from 'lucide-react';
import { PluginCard } from '@/components/PluginCard';
import { getLatestPlugins } from '@/data';
import { Button } from '@/components/ui/button';

export function LatestPlugins() {
  const plugins = getLatestPlugins(6);

  return (
    <section className="py-20 bg-[#0F0F1A]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-12">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-5 h-5 text-primary" />
              <span className="text-sm text-primary font-medium">最新</span>
            </div>
            <h2 className="text-3xl font-bold text-white">
              最新上传
            </h2>
          </div>
          <Link to="/plugins?sort=latest">
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
