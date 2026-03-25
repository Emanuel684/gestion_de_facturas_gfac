import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * @param {object} props
 * @param {boolean} [props.tenantOnly] — block plataforma_admin (facturas / usuarios tenant)
 * @param {boolean} [props.platformOnly] — only plataforma_admin (gestión de organizaciones)
 */
export default function ProtectedRoute({ children, tenantOnly, platformOnly }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="spinner-center"><div className="spinner" /></div>;
  if (!user) return <Navigate to="/login" replace />;

  if (tenantOnly && user.role === 'plataforma_admin') {
    return <Navigate to="/app/organizaciones" replace />;
  }
  if (platformOnly && user.role !== 'plataforma_admin') {
    return <Navigate to="/app" replace />;
  }

  return children;
}
