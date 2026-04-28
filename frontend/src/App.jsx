import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import InvoicesPage from './pages/InvoicesPage';
import UsersPage from './pages/UsersPage';
import OrganizationsPage from './pages/OrganizationsPage';
import SignupPage from './pages/SignupPage';
import MockCheckoutPage from './pages/MockCheckoutPage';
import BillingPage from './pages/BillingPage';
import DashboardPage from './pages/DashboardPage';
import ReportsPage from './pages/ReportsPage';
import PlatformDashboardPage from './pages/PlatformDashboardPage';
import PlatformReportsPage from './pages/PlatformReportsPage';
import OrganizationDetailPage from './pages/OrganizationDetailPage';
import { useAuth } from './context/AuthContext';
import './App.css';

function FallbackRedirect() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="spinner-center"><div className="spinner" /></div>;
  }

  if (!user) {
    return <Navigate to="/" replace />;
  }

  if (user.role === 'plataforma_admin') {
    return <Navigate to="/app/plataforma/dashboard" replace />;
  }

  return <Navigate to="/app" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/checkout/mock/:sessionToken" element={<MockCheckoutPage />} />
          <Route
            path="/app"
            element={
              <ProtectedRoute tenantOnly>
                <InvoicesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/users"
            element={
              <ProtectedRoute tenantOnly>
                <UsersPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/billing"
            element={
              <ProtectedRoute tenantOnly>
                <BillingPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/dashboard"
            element={
              <ProtectedRoute tenantOnly>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/reportes"
            element={
              <ProtectedRoute tenantOnly>
                <ReportsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/organizaciones"
            element={
              <ProtectedRoute platformOnly>
                <OrganizationsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/organizaciones/:organizationId"
            element={
              <ProtectedRoute platformOnly>
                <OrganizationDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/plataforma/dashboard"
            element={
              <ProtectedRoute platformOnly>
                <PlatformDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app/plataforma/reportes"
            element={
              <ProtectedRoute platformOnly>
                <PlatformReportsPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<FallbackRedirect />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
