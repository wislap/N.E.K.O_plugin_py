export interface Author {
  name: string;
  avatar: string;
  github: string;
}

export interface Rating {
  functionality: 'S' | 'A' | 'B' | 'C' | 'D';
  security: 'S' | 'A' | 'B' | 'C' | 'D';
  documentation: 'S' | 'A' | 'B' | 'C' | 'D';
  ratedAt: string;
}

export interface Plugin {
  id: string;
  slug: string;
  name: string;
  description: string;
  version: string;
  author: Author;
  githubRepo: string;
  downloadUrl?: string;
  zone: 'game' | 'companion' | 'function' | 'entertainment' | 'tool';
  tags: string[];
  downloads: number;
  likes: number;
  likedByCurrentUser?: boolean;
  aiRating?: Rating | null;
  adminRating?: Rating | null;
  readme: string;
  createdAt: string;
  updatedAt: string;
  isRecommended?: boolean;
}

export interface Review {
  id: string;
  pluginId: string;
  user: {
    name: string;
    avatar: string;
  };
  title?: string;
  content: string;
  createdAt: string;
}

export interface Zone {
  id: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  pluginCount: number;
}

export interface Stats {
  totalPlugins: number;
  totalDownloads: number;
  activeDevelopers: number;
  newPluginsThisWeek: number;
}
