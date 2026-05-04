import * as accessApi from "@/services/admin/access";
import * as categoriesApi from "@/services/admin/categories";
import * as dashboardApi from "@/services/admin/dashboard";
import * as logsApi from "@/services/admin/logs";
import * as permissionsApi from "@/services/admin/permissions";
import * as pluginsApi from "@/services/admin/plugins";
import * as reviewApi from "@/services/admin/review";
import * as settingsApi from "@/services/admin/settings";
import * as signaturesApi from "@/services/admin/signatures";
import * as usersApi from "@/services/admin/users";
import * as zonesApi from "@/services/admin/zones";

export type {
  Category,
  CategoryPayload,
  DashboardStats,
  LogStats,
  Plugin,
  ReviewOverview,
  ReviewSubmission,
  Role,
  ServerKeyPair,
  SMTPSettings,
  SystemSetting,
  User,
  UserPermissions,
  ZoneAdminItem,
  ZonePayload
} from "@/services/admin/types";

export {
  canAccessAdminPermission,
  hasAnyAdminAccess
} from "@/services/admin/access";

export const adminApi = {
  ...accessApi,
  ...dashboardApi,
  ...usersApi,
  ...categoriesApi,
  ...zonesApi,
  ...signaturesApi,
  ...pluginsApi,
  ...reviewApi,
  ...permissionsApi,
  ...settingsApi,
  ...logsApi
};
