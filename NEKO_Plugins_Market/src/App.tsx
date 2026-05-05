import { lazy, Suspense, type ReactNode } from 'react';
import { HashRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { PageTransition } from '@/components/PageTransition';
import { AppDiagnostics } from '@/components/AppDiagnostics';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { Toaster } from '@/components/ui/sonner';

const Home = lazy(() => import('@/pages/Home').then((module) => ({ default: module.Home })));
const Plugins = lazy(() => import('@/pages/Plugins').then((module) => ({ default: module.Plugins })));
const PluginDetail = lazy(() => import('@/pages/PluginDetail').then((module) => ({ default: module.PluginDetail })));
const Upload = lazy(() => import('@/pages/Upload').then((module) => ({ default: module.Upload })));
const Auth = lazy(() => import('@/pages/Auth').then((module) => ({ default: module.Auth })));
const VerifyEmail = lazy(() => import('@/pages/VerifyEmail').then((module) => ({ default: module.VerifyEmail })));
const MyPlugins = lazy(() => import('@/pages/MyPlugins').then((module) => ({ default: module.MyPlugins })));
const AdminApp = lazy(() => import('@/admin/AdminApp').then((module) => ({ default: module.AdminApp })));

function PageFallback() {
  return (
    <div className="mx-auto flex min-h-[60vh] w-full max-w-7xl flex-col gap-4 px-4 py-10 sm:px-6 lg:px-8">
      <div className="h-8 w-56 animate-pulse rounded-md bg-slate-800/80" />
      <div className="grid gap-4 md:grid-cols-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={index} className="h-32 animate-pulse rounded-xl border border-slate-800/70 bg-[#1A1A2E]" />
        ))}
      </div>
    </div>
  );
}

function withPublicSuspense(element: ReactNode) {
  return <PageTransition><Suspense fallback={<PageFallback />}>{element}</Suspense></PageTransition>;
}

function PublicRoutes() {
  const location = useLocation();

  return (
    <>
      <Header />
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={withPublicSuspense(<Home />)} />
          <Route path="/plugins" element={withPublicSuspense(<Plugins />)} />
          <Route path="/plugin/:id" element={withPublicSuspense(<PluginDetail />)} />
          <Route path="/upload" element={withPublicSuspense(<Upload />)} />
          <Route path="/my/plugins" element={withPublicSuspense(<MyPlugins />)} />
          <Route path="/login" element={withPublicSuspense(<Auth />)} />
          <Route path="/register" element={withPublicSuspense(<Auth />)} />
          <Route path="/verify-email" element={withPublicSuspense(<VerifyEmail />)} />
        </Routes>
      </AnimatePresence>
      <Footer />
    </>
  );
}

function MainLayout() {
  const location = useLocation();
  const isAdminRoute = location.pathname.startsWith('/admin');

  return isAdminRoute
    ? <Suspense fallback={<PageFallback />}><AdminApp /></Suspense>
    : <PublicRoutes />;
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
