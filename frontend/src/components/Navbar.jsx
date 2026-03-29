import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Navbar.css';

const ROLE_COLORS = {
  plataforma_admin: '#7c2d12',
  administrador: '#059669',
  contador: '#0e7490',
  asistente: '#7c3aed',
};

const ROLE_LABELS = {
  plataforma_admin: 'Plataforma',
  administrador: 'Admin',
  contador: 'Contador',
  asistente: 'Asistente',
};

export default function Navbar() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    signOut();
    navigate('/login', { replace: true });
  };

  const isPlatform = user?.role === 'plataforma_admin';

  return (
    <nav className="navbar">
      <Link to={user ? (isPlatform ? '/app/plataforma/dashboard' : '/app') : '/'} className="navbar-brand">
        <svg width="26" height="26" viewBox="0 0 40 40" fill="none">
          <rect width="40" height="40" rx="10" fill="#0e7490"/>
          <path d="M10 14h20M10 20h20M10 26h14" stroke="white" strokeWidth="2.5" strokeLinecap="round"/>
        </svg>
        SGF — Facturas
      </Link>
      {user && !isPlatform && (
        <div className="navbar-links">
          <Link to="/app" className="nav-link">Facturas</Link>
          <Link to="/app/dashboard" className="nav-link">Dashboard</Link>
          <Link to="/app/reportes" className="nav-link">Reportes</Link>
          <Link to="/app/users" className="nav-link">Usuarios</Link>
          <Link to="/app/billing" className="nav-link">Suscripcion</Link>
        </div>
      )}
      {user && isPlatform && (
        <div className="navbar-links">
          <Link to="/app/organizaciones" className="nav-link">Organizaciones</Link>
          <Link to="/app/plataforma/dashboard" className="nav-link">Dashboard</Link>
          <Link to="/app/plataforma/reportes" className="nav-link">Reportes</Link>
        </div>
      )}

      <div className="navbar-right">
        {user && (
          <>
            <span className="navbar-user">
              <span
                className="role-badge"
                style={{ background: ROLE_COLORS[user.role] || '#6b7280' }}
              >
                {ROLE_LABELS[user.role] || user.role}
              </span>
              <span className="navbar-user-text">
                {user.username}
                {user.organization?.name && (
                  <span className="navbar-org"> · {user.organization.name}</span>
                )}
              </span>
            </span>
            <button className="btn btn-secondary btn-sm" onClick={handleLogout}>
              Cerrar Sesión
            </button>
          </>
        )}
      </div>
    </nav>
  );
}
