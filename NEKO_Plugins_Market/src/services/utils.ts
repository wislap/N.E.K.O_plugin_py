import type { Role } from "./types";

export function normalizePlugins<T>(data: T[] | { items: T[] }) {
  return Array.isArray(data) ? data : data.items;
}

export function queryString(params: Record<string, unknown>) {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  });

  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export function recentCount(items: Array<{ created_at: string }>) {
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  return items.filter((item) => new Date(item.created_at).getTime() >= weekAgo).length;
}

export function roleCodeFromName(name: string) {
  const normalized = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return `custom_${normalized || Date.now()}`;
}

export function toRole(group: {
  id: number;
  code: string;
  name: string;
  description?: string | null;
  is_system?: boolean;
  permissions?: Array<{ code: string }>;
}): Role {
  return {
    id: group.id,
    code: group.code,
    name: group.name,
    description: group.description ?? "",
    permissions: group.permissions?.map((permission) => permission.code) ?? [],
    user_count: 0,
    is_system: group.is_system ?? false
  };
}
