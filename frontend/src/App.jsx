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
import './App.css';

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
            path="/app/organizaciones"
            element={
              <ProtectedRoute platformOnly>
                <OrganizationsPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
