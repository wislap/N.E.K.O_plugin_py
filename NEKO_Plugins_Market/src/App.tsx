import { HashRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { PageTransition } from '@/components/PageTransition';
import { AppDiagnostics } from '@/components/AppDiagnostics';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { Toaster } from '@/components/ui/sonner';
import { Home } from '@/pages/Home';
import { Plugins } from '@/pages/Plugins';
import { PluginDetail } from '@/pages/PluginDetail';
import { Upload } from '@/pages/Upload';
import { Auth } from '@/pages/Auth';
import { VerifyEmail } from '@/pages/VerifyEmail';
import { MyPlugins } from '@/pages/MyPlugins';
import AdminLayout from '@/pages/admin/AdminLayout';
import AdminLogin from '@/pages/admin/Login';
import AdminDashboard from '@/pages/admin/Dashboard';
import AdminPlugins from '@/pages/admin/Plugins';
import ReviewOverview from '@/pages/admin/ReviewOverview';
import ReviewArchive from '@/pages/admin/ReviewArchive';
import AdminUsers from '@/pages/admin/Users';
import AdminPermissions from '@/pages/admin/Permissions';
import AdminSMTP from '@/pages/admin/SMTP';
import AdminSettings from '@/pages/admin/Settings';
import AdminLogs from '@/pages/admin/Logs';
import AdminChangePassword from '@/pages/admin/ChangePassword';
import AdminCategories from '@/pages/admin/Categories';
import AdminZones from '@/pages/admin/Zones';
import AdminSignatures from '@/pages/admin/Signatures';

function AdminRoutes() {
  return (
    <Routes>
      <Route path="/admin/login" element={<AdminLogin />} />
      <Route path="/admin/*" element={<AdminLayout />}>
        <Route index element={<AdminDashboard />} />
        <Route path="plugins" element={<Navigate to="/admin/review/workspace" replace />} />
        <Route path="review/overview" element={<ReviewOverview />} />
        <Route path="review/workspace" element={<AdminPlugins />} />
        <Route path="review/archive" element={<ReviewArchive />} />
        <Route path="users" element={<AdminUsers />} />
        <Route path="permissions" element={<AdminPermissions />} />
        <Route path="smtp" element={<AdminSMTP />} />
        <Route path="settings" element={<AdminSettings />} />
        <Route path="logs" element={<AdminLogs />} />
        <Route path="categories" element={<AdminCategories />} />
        <Route path="zones" element={<AdminZones />} />
        <Route path="signatures" element={<AdminSignatures />} />
        <Route path="change-password" element={<AdminChangePassword />} />
      </Route>
    </Routes>
  );
}

function PublicRoutes() {
  const location = useLocation();

  return (
    <>
      <Header />
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<PageTransition><Home /></PageTransition>} />
          <Route path="/plugins" element={<PageTransition><Plugins /></PageTransition>} />
          <Route path="/plugin/:id" element={<PageTransition><PluginDetail /></PageTransition>} />
          <Route path="/upload" element={<PageTransition><Upload /></PageTransition>} />
          <Route path="/my/plugins" element={<PageTransition><MyPlugins /></PageTransition>} />
          <Route path="/login" element={<PageTransition><Auth /></PageTransition>} />
          <Route path="/register" element={<PageTransition><Auth /></PageTransition>} />
          <Route path="/verify-email" element={<PageTransition><VerifyEmail /></PageTransition>} />
        </Routes>
      </AnimatePresence>
      <Footer />
    </>
  );
}

function MainLayout() {
  const location = useLocation();
  const isAdminRoute = location.pathname.startsWith('/admin');

  return isAdminRoute ? <AdminRoutes /> : <PublicRoutes />;
}

function App() {
  return (
    <HashRouter>
      <ErrorBoundary>
        <AppDiagnostics />
        <div className="min-h-screen bg-[#0F0F1A]">
          <MainLayout />
        </div>
        <Toaster richColors closeButton position="top-right" />
      </ErrorBoundary>
    </HashRouter>
  );
}

export default App;
