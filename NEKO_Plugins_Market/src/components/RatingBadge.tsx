import type { Rating } from '@/types';

interface RatingBadgeProps {
  rating: Rating;
  showDetails?: boolean;
}

const ratingColors: Record<string, string> = {
  S: '#FFD700',
  A: '#C084FC',
  B: '#60A5FA',
  C: '#4ADE80',
  D: '#9CA3AF',
};

export function RatingBadge({
  rating,
  showDetails = false,
}: RatingBadgeProps) {
  if (!showDetails) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-400">安全</span>
        <span
          className="w-5 h-5 rounded flex items-center justify-center text-xs font-bold"
          style={{
            backgroundColor: `${ratingColors[rating.security]}20`,
            color: ratingColors[rating.security],
          }}
        >
          {rating.security}
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <span className="text-sm text-slate-400 w-20">功能性</span>
        <span
          className="w-6 h-6 rounded flex items-center justify-center text-sm font-bold"
          style={{
            backgroundColor: `${ratingColors[rating.functionality]}20`,
            color: ratingColors[rating.functionality],
          }}
        >
          {rating.functionality}
        </span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-sm text-slate-400 w-20">安全性</span>
        <span
          className="w-6 h-6 rounded flex items-center justify-center text-sm font-bold"
          style={{
            backgroundColor: `${ratingColors[rating.security]}20`,
            color: ratingColors[rating.security],
          }}
        >
          {rating.security}
        </span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-sm text-slate-400 w-20">文档完善度</span>
        <span
          className="w-6 h-6 rounded flex items-center justify-center text-sm font-bold"
          style={{
            backgroundColor: `${ratingColors[rating.documentation]}20`,
            color: ratingColors[rating.documentation],
          }}
        >
          {rating.documentation}
        </span>
      </div>
    </div>
  );
}