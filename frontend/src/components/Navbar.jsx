import { useState, useEffect } from 'react';
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
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = () => {
    setMenuOpen(false);
    signOut();
    navigate('/login', { replace: true });
  };

  const closeMenu = () => setMenuOpen(false);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const onKey = (e) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [menuOpen]);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const onResize = () => {
      if (window.innerWidth >= 900) setMenuOpen(false);
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [menuOpen]);

  const isPlatform = user?.role === 'plataforma_admin';

  return (
    <nav className="navbar">
      <Link
        to={user ? (isPlatform ? '/app/plataforma/dashboard' : '/app') : '/'}
        className="navbar-brand"
        onClick={closeMenu}
      >
        <svg width="26" height="26" viewBox="0 0 40 40" fill="none" aria-hidden>
          <rect width="40" height="40" rx="10" fill="#0e7490" />
          <path
            d="M10 14h20M10 20h20M10 26h14"
            stroke="white"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
        </svg>
        SGF — Facturas
      </Link>

      {user && (
        <>
          <button
            type="button"
            className="navbar-menu-btn"
            aria-expanded={menuOpen}
            aria-controls="navbar-mobile-panel"
            aria-label={menuOpen ? 'Cerrar menú' : 'Abrir menú'}
            onClick={() => setMenuOpen((o) => !o)}
          >
            <span className={`navbar-menu-icon ${menuOpen ? 'is-open' : ''}`} aria-hidden />
          </button>
          <div
            id="navbar-mobile-panel"
            className={`navbar-collapse ${menuOpen ? 'is-open' : ''}`}
          >
            {!isPlatform && (
              <div className="navbar-links">
                <Link to="/app" className="nav-link" onClick={closeMenu}>
                  Facturas
                </Link>
                <Link to="/app/dashboard" className="nav-link" onClick={closeMenu}>
                  Dashboard
                </Link>
                <Link to="/app/reportes" className="nav-link" onClick={closeMenu}>
                  Reportes
                </Link>
                <Link to="/app/users" className="nav-link" onClick={closeMenu}>
                  Usuarios
                </Link>
                <Link to="/app/billing" className="nav-link" onClick={closeMenu}>
                  Suscripción
                </Link>
              </div>
            )}
            {isPlatform && (
              <div className="navbar-links">
                <Link to="/app/organizaciones" className="nav-link" onClick={closeMenu}>
                  Organizaciones
                </Link>
                <Link to="/app/plataforma/dashboard" className="nav-link" onClick={closeMenu}>
                  Dashboard
                </Link>
                <Link to="/app/plataforma/reportes" className="nav-link" onClick={closeMenu}>
                  Reportes
                </Link>
              </div>
            )}

            <div className="navbar-right">
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
              <button type="button" className="btn btn-secondary btn-sm" onClick={handleLogout}>
                Cerrar Sesión
              </button>
            </div>
          </div>
          {menuOpen && (
            <button
              type="button"
              className="navbar-backdrop"
              aria-label="Cerrar menú"
              onClick={closeMenu}
            />
          )}
        </>
      )}
    </nav>
  );
}
