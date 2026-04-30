import { HashRouter, Routes, Route, useLocation } from 'react-router-dom';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { Home } from '@/pages/Home';
import { Plugins } from '@/pages/Plugins';
import { PluginDetail } from '@/pages/PluginDetail';
import { Upload } from '@/pages/Upload';
import AdminLayout from '@/pages/admin/AdminLayout';
import AdminLogin from '@/pages/admin/Login';
import AdminDashboard from '@/pages/admin/Dashboard';
import AdminPlugins from '@/pages/admin/Plugins';
import AdminUsers from '@/pages/admin/Users';
import AdminPermissions from '@/pages/admin/Permissions';
import AdminSMTP from '@/pages/admin/SMTP';
import AdminSettings from '@/pages/admin/Settings';
import AdminLogs from '@/pages/admin/Logs';

function MainLayout() {
  const location = useLocation();
  const isAdminRoute = location.pathname.startsWith('/admin');

  if (isAdminRoute) {
    return (
      <Routes>
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin/*" element={<AdminLayout />}>
          <Route index element={<AdminDashboard />} />
          <Route path="plugins" element={<AdminPlugins />} />
          <Route path="users" element={<AdminUsers />} />
          <Route path="permissions" element={<AdminPermissions />} />
          <Route path="smtp" element={<AdminSMTP />} />
          <Route path="settings" element={<AdminSettings />} />
          <Route path="logs" element={<AdminLogs />} />
        </Route>
      </Routes>
    );
  }

  return (
    <>
      <Header />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/plugins" element={<Plugins />} />
        <Route path="/plugin/:id" element={<PluginDetail />} />
        <Route path="/upload" element={<Upload />} />
      </Routes>
      <Footer />
    </>
  );
}

function App() {
  return (
    <HashRouter>
      <div className="min-h-screen bg-[#0F0F1A]">
        <MainLayout />
      </div>
    </HashRouter>
  );
}

export default App;
