export interface User {
  id: number;
  username: string;
  email: string;
  display_name?: string | null;
  avatar_url?: string | null;
  is_admin: boolean;
  is_active: boolean;
  must_change_password: boolean;
  email_verified_at?: string | null;
  is_email_verified: boolean;
  created_at: string;
  updated_at?: string;
}

export interface LatestVersion {
  version: string;
  channel: "stable" | "beta";
  package_url: string;
  package_sha256: string;
  payload_hash: string | null;
  created_at: string;
}

export interface Plugin {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  short_description?: string | null;
  author_id: number;
  author_name: string;
  // 注意：market-version-management 重构后不再有 version / download_url 顶层字段；
  // 当前最新版统一通过 latest_version 子对象暴露，可能为 null。
  latest_version: LatestVersion | null;
  icon_url?: string | null;
  repo_url?: string | null;
  readme?: string | null;
  zone_id?: number | null;
  zone_slug?: string | null;
  tags?: string[];
  download_count: number;
  likes: number;
  rating_average: number;
  rating_count: number;
  status: "approved" | "disabled" | string;
  is_featured: number;
  created_at: string;
  updated_at: string;
  published_at?: string | null;
}

export interface UserPluginInstall {
  id: number;
  plugin_id: number;
  version?: string | null;
  channel?: string | null;
  package_sha256?: string | null;
  payload_hash?: string | null;
  installed_plugin_id?: string | null;
  client_id: string;
  installed_at: string;
  last_seen_at: string;
}

export interface UserPluginInstallCreate {
  plugin_id: number;
  version?: string | null;
  channel?: string | null;
  package_sha256?: string | null;
  payload_hash?: string | null;
  installed_plugin_id?: string | null;
  client_id?: string;
}

export interface Role {
  id: number;
  code?: string;
  name: string;
  description: string;
  permissions: string[];
  user_count: number;
  is_system?: boolean;
}

export interface DashboardStats {
  totalUsers: number;
  totalPlugins: number;
  pendingPlugins: number;
  approvedPlugins: number;
  rejectedPlugins: number;
  recentUsers: number;
  recentPlugins: number;
}

export interface MarketStats {
  totalPlugins: number;
  totalDownloads: number;
  activeDevelopers: number;
  newPluginsThisWeek: number;
}

export interface SMTPSettings {
  host: string;
  port: number;
  user: string;
  password?: string;
  ssl: boolean;
  tls: boolean;
  from_email: string;
  enabled: boolean;
}

export interface SystemSetting {
  key: string;
  value: string | number | boolean | null;
  description?: string | null;
  group?: string | null;
  is_encrypted?: boolean;
  updated_at?: string;
}

export interface Notification {
  id: number;
  user_id: number;
  type: string;
  title: string;
  content?: string | null;
  target_url?: string | null;
  is_read: boolean;
  created_at: string;
  read_at?: string | null;
}

export interface LogStats {
  review_logs?: number;
  sandbox_logs?: number;
  permission_audit_logs?: number;
  total_logs?: number;
  [key: string]: number | string | undefined;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  display_name?: string;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

export interface LoginResponse {
  user: User;
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RegisterResponse {
  user: User;
  verification_email_sent?: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token?: string | null;
  token_type: string;
}

export interface ResendVerificationResponse {
  already_verified: boolean;
  verification_email_sent: boolean;
  message: string;
}

export interface PublicResendVerificationRequest {
  email: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page?: number;
  page_size?: number;
  total_pages?: number;
  has_next?: boolean;
  has_prev?: boolean;
}

export type RequestBody = unknown;

export type VerificationStatus = "unverified" | "pending" | "passed" | "failed";

export interface PluginVersion {
  id: number;
  plugin_id: number;
  version: string;
  channel: "stable" | "beta" | string;
  is_latest: boolean;
  yanked_at: string | null;
  yanked_reason: string | null;
  yanked_by: number | null;
  published_by: number | null;
  changelog?: string | null;
  download_url?: string | null;
  min_app_version?: string | null;
  max_app_version?: string | null;
  source_repo_url?: string | null;
  source_commit?: string | null;
  release_tag?: string | null;
  release_url?: string | null;
  actions_run_url?: string | null;
  package_url?: string | null;
  package_sha256?: string | null;
  payload_hash?: string | null;
  neko_repo?: string | null;
  neko_ref?: string | null;
  neko_commit?: string | null;
  verification_status: VerificationStatus | string;
  verification_summary?: string | null;
  created_at: string;
}

export interface VersionPublishRequest {
  release_url: string;
  channel?: "stable" | "beta";
  changelog?: string | null;
}

export interface VersionReleaseCandidate {
  tag_name: string;
  name?: string | null;
  release_url: string;
  published_at?: string | null;
  draft: boolean;
  prerelease: boolean;
  asset_names: string[];
  has_package_asset: boolean;
}

export interface VersionYankRequest {
  reason: string;
}

export interface VersionYankResponse {
  yanked: PluginVersion;
  promoted: PluginVersion | null;
}

export interface ReviewCreateRequest {
  rating: number;
  title?: string;
  content?: string;
}

export type PluginQuery = {
  q?: string;
  category?: string;
  author?: string;
  sort_by?: "created_at" | "download_count" | "rating_average" | "name";
  sort_order?: "asc" | "desc";
  featured_only?: boolean;
  page?: number;
  page_size?: number;
};

export interface ReviewDto {
  id: number;
  plugin_id: number;
  rating: number;
  title?: string | null;
  content?: string | null;
  created_at: string;
  author?: {
    username: string;
    display_name?: string | null;
    avatar_url?: string | null;
  } | null;
}
