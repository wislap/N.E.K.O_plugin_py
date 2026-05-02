import type { MarketStats } from "./types";
import { pluginsApi } from "./plugins";

function recentMarketCount(items: Array<{ createdAt: string }>) {
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  return items.filter((item) => new Date(item.createdAt).getTime() >= weekAgo).length;
}

export const marketApi = {
  async getStats(): Promise<MarketStats> {
    const data = await pluginsApi.list({ page_size: 100 });
    const plugins = data.items;

    return {
      totalPlugins: data.total,
      totalDownloads: plugins.reduce((total, plugin) => total + plugin.downloads, 0),
      activeDevelopers: new Set(plugins.map((plugin) => plugin.author.name)).size,
      newPluginsThisWeek: recentMarketCount(plugins)
    };
  }
};
