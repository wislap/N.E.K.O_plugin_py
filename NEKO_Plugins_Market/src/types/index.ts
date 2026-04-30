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
  name: string;
  description: string;
  version: string;
  author: Author;
  githubRepo: string;
  zone: 'game' | 'companion' | 'function' | 'entertainment' | 'tool';
  tags: string[];
  downloads: number;
  likes: number;
  aiRating: Rating;
  adminRating: Rating;
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
  content: string;
  likes: number;
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