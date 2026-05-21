import type { Plugin as MarketPlugin, Rating, Review as MarketReview } from "@/types";
import type { Plugin, ReviewDto } from "./types";

function fallbackRating(): Rating {
  return {
    functionality: "B",
    security: "B",
    documentation: "B",
    ratedAt: new Date(0).toISOString()
  };
}

function zoneSlugFromId(zoneId?: number | null): MarketPlugin["zone"] {
  const zones: MarketPlugin["zone"][] = ["game", "companion", "function", "entertainment", "tool"];
  if (!zoneId || zoneId < 1 || zoneId > zones.length) {
    return "function";
  }
  return zones[zoneId - 1];
}

function githubOwner(repoUrl?: string | null) {
  if (!repoUrl) {
    return "";
  }

  try {
    const url = new URL(repoUrl);
    return url.hostname === "github.com" ? url.pathname.split("/").filter(Boolean)[0] ?? "" : "";
  } catch {
    return "";
  }
}

function githubProfile(repoUrl?: string | null) {
  const owner = githubOwner(repoUrl);
  return owner ? `https://github.com/${owner}` : "";
}

export function toMarketPlugin(plugin: Plugin): MarketPlugin {
  const description = plugin.description ?? plugin.short_description ?? "";
  const rating = fallbackRating();
  const latest = plugin.latest_version;

  return {
    id: String(plugin.id),
    slug: plugin.slug,
    name: plugin.name,
    description,
    // market-version-management spec：版本号与下载 URL 一律由 latest_version 决定。
    // 没有 latest_version 时返回空字符串，前端 UI 应展示"暂无可下载版本"，
    // **不再** fallback 到 repo_url（仓库主页不是合法插件包）。
    version: latest?.version ?? "",
    author: {
      name: plugin.author_name,
      avatar: plugin.icon_url ?? "",
      github: githubProfile(plugin.repo_url)
    },
    githubRepo: plugin.repo_url ?? "",
    downloadUrl: latest?.package_url ?? "",
    zone: (plugin.zone_slug as MarketPlugin["zone"] | null) ?? zoneSlugFromId(plugin.zone_id),
    tags: plugin.tags ?? [],
    downloads: plugin.download_count,
    likes: plugin.likes ?? 0,
    aiRating: rating,
    adminRating: rating,
    readme: plugin.readme ?? description,
    createdAt: plugin.created_at,
    updatedAt: plugin.updated_at,
    isRecommended: Boolean(plugin.is_featured)
  };
}

export function toMarketReview(review: ReviewDto): MarketReview {
  const userName = review.author?.display_name || review.author?.username || "匿名用户";

  return {
    id: String(review.id),
    pluginId: String(review.plugin_id),
    user: {
      name: userName,
      avatar: review.author?.avatar_url ?? ""
    },
    rating: review.rating,
    title: review.title ?? undefined,
    content: review.content ?? "",
    likes: 0,
    createdAt: review.created_at
  };
}
