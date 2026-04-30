import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { zones } from '@/data';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getZoneById(zoneId: string) {
  return zones.find((z) => z.id === zoneId);
}

export function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
}

export function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days === 0) {
    const hours = Math.floor(diff / (1000 * 60 * 60));
    if (hours === 0) {
      const minutes = Math.floor(diff / (1000 * 60));
      return minutes === 0 ? '刚刚' : `${minutes} 分钟前`;
    }
    return `${hours} 小时前`;
  }
  if (days < 7) {
    return `${days} 天前`;
  }
  if (days < 30) {
    return `${Math.floor(days / 7)} 周前`;
  }
  
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}