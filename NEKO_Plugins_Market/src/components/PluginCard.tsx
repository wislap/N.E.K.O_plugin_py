import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Download, ThumbsUp, Github, Sparkles } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import type { Plugin } from '@/types';
import { getZoneById } from '@/lib/utils';
import { listItem } from '@/lib/animations';

interface PluginCardProps {
  plugin: Plugin;
}

const ratingColors: Record<string, string> = {
  S: '#FFD700',
  A: '#C084FC',
  B: '#60A5FA',
  C: '#4ADE80',
  D: '#9CA3AF',
};

export function PluginCard({ plugin }: PluginCardProps) {
  const navigate = useNavigate();
  const zone = getZoneById(plugin.zone);
  const summaryRating = plugin.adminRating ?? plugin.aiRating ?? null;

  const formatDownloads = (num: number): string => {
    if (num >= 10000) {
      return (num / 10000).toFixed(1) + 'w';
    }
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'k';
    }
    return num.toString();
  };

  return (
    <motion.div
      variants={listItem}
      whileHover={{ y: -4 }}
      whileTap={{ scale: 0.985 }}
      className="h-full"
    >
      <article
        role="link"
        tabIndex={0}
        onClick={() => navigate(`/plugin/${plugin.id}`)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            navigate(`/plugin/${plugin.id}`);
          }
        }}
        className="group block h-full cursor-pointer bg-[#1A1A2E] border border-slate-800/50 rounded-xl p-5 hover:border-primary/30 hover:shadow-[0_0_20px_oklch(var(--primary)/0.15)] transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              {plugin.isRecommended && (
                <Badge className="bg-gradient-to-r from-amber-500 to-orange-500 text-white text-xs px-2 py-0.5">
                  <Sparkles className="w-3 h-3 mr-1" />
                  推荐
                </Badge>
              )}
              <span
                className="text-xs font-medium px-2 py-0.5 rounded-full"
                style={{
                  backgroundColor: `${zone?.color}20`,
                  color: zone?.color,
                }}
              >
                {zone?.name}
              </span>
            </div>
            <h3 className="text-lg font-semibold text-white group-hover:text-primary transition-colors truncate">
              {plugin.name}
            </h3>
          </div>
          <div className="flex flex-col items-end gap-1 ml-2 shrink-0">
            <div className="flex items-center gap-1">
              {plugin.tags.slice(0, 2).map((tag) => (
                <Badge
                  key={tag}
                  variant="secondary"
                  className="px-1.5 py-0 text-[10px] leading-4 bg-slate-800/40 text-slate-400"
                >
                  {tag}
                </Badge>
              ))}
              {plugin.tags.length > 2 && (
                <Badge
                  variant="secondary"
                  className="px-1.5 py-0 text-[10px] leading-4 bg-slate-800/40 text-slate-400"
                >
                  +{plugin.tags.length - 2}
                </Badge>
              )}
            </div>
            <span className="text-sm text-slate-500 font-mono">v{plugin.version}</span>
          </div>
        </div>

        {/* Author */}
        <div className="flex items-center gap-2 mb-3">
          <Avatar className="w-5 h-5">
            <AvatarImage src={plugin.author.avatar} alt={plugin.author.name} />
            <AvatarFallback className="text-xs bg-primary text-primary-foreground">
              {plugin.author.name[0]}
            </AvatarFallback>
          </Avatar>
          <span className="text-sm text-slate-400">{plugin.author.name}</span>
        </div>

        {/* Description */}
        <p className="text-sm text-slate-400 line-clamp-3 mb-4 min-h-[60px]">
          {plugin.description}
        </p>

        {/* Rating Summary */}
        {summaryRating ? (
          <div className="flex items-center gap-2 mb-4 p-2 bg-[#0F0F1A] rounded-lg">
            {[
              ['功能', summaryRating.functionality],
              ['安全', summaryRating.security],
              ['文档', summaryRating.documentation],
            ].map(([label, grade]) => (
              <div key={label} className="flex items-center gap-1.5">
                <span className="text-xs text-slate-500">{label}</span>
                <span
                  className="w-5 h-5 rounded flex items-center justify-center text-xs font-bold"
                  style={{
                    backgroundColor: `${ratingColors[grade]}20`,
                    color: ratingColors[grade],
                  }}
                >
                  {grade}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="mb-4 rounded-lg bg-[#0F0F1A] p-2 text-xs text-slate-500">
            待评级
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-slate-800/50">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1 text-slate-400">
              <Download className="w-4 h-4" />
              <span className="text-sm">{formatDownloads(plugin.downloads)}</span>
            </div>
            <div className="flex items-center gap-1 text-primary">
              <ThumbsUp className="w-4 h-4" />
              <span className="text-sm">{formatDownloads(plugin.likes)}</span>
            </div>
          </div>
          <a
            href={plugin.githubRepo}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              window.open(plugin.githubRepo, '_blank', 'noopener,noreferrer');
            }}
            className="flex items-center gap-1 text-slate-500 hover:text-white transition-colors"
          >
            <Github className="w-4 h-4" />
            <span className="text-sm">仓库</span>
          </a>
        </div>
      </article>
    </motion.div>
  );
}
