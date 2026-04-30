import pluginsData from './plugins.json';
import type { Plugin, Review, Zone, Stats } from '@/types';

export const plugins: Plugin[] = pluginsData.plugins as Plugin[];
export const reviews: Review[] = pluginsData.reviews as Review[];
export const zones: Zone[] = pluginsData.zones as Zone[];
export const stats: Stats = pluginsData.stats as Stats;

export function getPluginById(id: string): Plugin | undefined {
  return plugins.find(p => p.id === id);
}

export function getReviewsByPluginId(pluginId: string): Review[] {
  return reviews.filter(r => r.pluginId === pluginId);
}

export function getPluginsByZone(zoneId: string): Plugin[] {
  return plugins.filter(p => p.zone === zoneId);
}

export function getRecommendedPlugins(): Plugin[] {
  return plugins.filter(p => p.isRecommended);
}

export function getPopularPlugins(limit: number = 6): Plugin[] {
  return [...plugins]
    .sort((a, b) => b.downloads - a.downloads)
    .slice(0, limit);
}

export function getLatestPlugins(limit: number = 6): Plugin[] {
  return [...plugins]
    .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
    .slice(0, limit);
}

export function searchPlugins(query: string): Plugin[] {
  const lowerQuery = query.toLowerCase();
  return plugins.filter(p => 
    p.name.toLowerCase().includes(lowerQuery) ||
    p.description.toLowerCase().includes(lowerQuery) ||
    p.tags.some(tag => tag.toLowerCase().includes(lowerQuery))
  );
}