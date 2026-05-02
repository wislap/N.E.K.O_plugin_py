import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Gamepad2, Heart, Music, Settings, Sparkles, Wrench, Zap } from 'lucide-react';
import type { Zone } from '@/types';
import { listItem } from '@/lib/animations';

const iconMap: Record<string, React.ComponentType<{ className?: string; style?: React.CSSProperties }>> = {
  Gamepad2,
  Heart,
  Settings,
  Sparkles,
  Zap,
  Music,
  Wrench,
};

interface ZoneCardProps {
  zone: Zone;
}

export function ZoneCard({ zone }: ZoneCardProps) {
  const Icon = iconMap[zone.icon] || Zap;

  return (
    <motion.div
      variants={listItem}
      whileHover={{ y: -4 }}
      whileTap={{ scale: 0.985 }}
    >
      <Link
        to={`/plugins?zone=${zone.id}`}
        className="group block p-6 bg-[#1A1A2E] border border-slate-800/50 rounded-xl hover:border-primary/30 transition-all duration-300 hover:shadow-[0_0_30px_oklch(var(--primary)/0.15)]"
      >
        <div
          className="w-14 h-14 rounded-xl flex items-center justify-center mb-4 transition-transform group-hover:scale-110"
          style={{ backgroundColor: `${zone.color}20` }}
        >
          <Icon className="w-7 h-7" style={{ color: zone.color }} />
        </div>
        <h3 className="text-lg font-semibold text-white mb-1 group-hover:text-primary transition-colors">
          {zone.name}
        </h3>
        <p className="text-sm text-slate-400 mb-3">{zone.description}</p>
        <div className="flex items-center gap-2">
          <span
            className="text-sm font-medium"
            style={{ color: zone.color }}
          >
            {zone.pluginCount}
          </span>
          <span className="text-sm text-slate-500">个插件</span>
        </div>
      </Link>
    </motion.div>
  );
}
