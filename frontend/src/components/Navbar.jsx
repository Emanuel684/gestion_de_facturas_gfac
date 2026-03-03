import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Navbar.css';

const ROLE_COLORS = {
  administrador: '#059669',
  contador: '#0e7490',
  asistente: '#7c3aed',
};

const ROLE_LABELS = {
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

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand">
        <svg width="26" height="26" viewBox="0 0 40 40" fill="none">
          <rect width="40" height="40" rx="10" fill="#0e7490"/>
          <path d="M10 14h20M10 20h20M10 26h14" stroke="white" strokeWidth="2.5" strokeLinecap="round"/>
        </svg>
        SGF — Facturas
      </Link>      {user && (
        <div className="navbar-links">
          <Link to="/" className="nav-link">Facturas</Link>
          <Link to="/users" className="nav-link">Usuarios</Link>
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
              {user.username}
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
