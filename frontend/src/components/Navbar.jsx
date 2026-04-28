import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  getNotificationsPage,
  getNotificationsUnreadCount,
  markAllNotificationsAsRead,
  markNotificationAsRead,
} from '../api';
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
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const handleLogout = async () => {
    setMenuOpen(false);
    await signOut();
    navigate('/login', { replace: true });
  };

  const closeMenu = () => setMenuOpen(false);
  const isPlatform = user?.role === 'plataforma_admin';

  const refreshUnread = async () => {
    if (!user || isPlatform) return;
    try {
      const resp = await getNotificationsUnreadCount();
      setUnreadCount(resp.data.unread || 0);
    } catch {
      /* ignore */
    }
  };

  const refreshNotifications = async () => {
    if (!user || isPlatform) return;
    try {
      const resp = await getNotificationsPage({ page: 0, pageSize: 12 });
      setNotifications(resp.data.items || []);
    } catch {
      /* ignore */
    }
  };

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
      if (window.matchMedia('(min-width: 901px)').matches) setMenuOpen(false);
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [menuOpen]);

  useEffect(() => {
    if (!user || isPlatform) return undefined;
    refreshUnread();
    const id = window.setInterval(refreshUnread, 30000);
    return () => window.clearInterval(id);
  }, [user, isPlatform]);

  useEffect(() => {
    if (!notifOpen) return;
    refreshNotifications();
    refreshUnread();
  }, [notifOpen]);

  useEffect(() => {
    if (!notifOpen) return undefined;
    const onDocClick = (e) => {
      if (!e.target.closest('.notifications-wrap')) {
        setNotifOpen(false);
      }
    };
    document.addEventListener('click', onDocClick);
    return () => document.removeEventListener('click', onDocClick);
  }, [notifOpen]);

  const handleMarkRead = async (id) => {
    try {
      await markNotificationAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n))
      );
      await refreshUnread();
    } catch {
      /* ignore */
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true, read_at: new Date().toISOString() })));
      setUnreadCount(0);
    } catch {
      /* ignore */
    }
  };

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
              {!isPlatform && (
                <div className="notifications-wrap">
                  <button
                    type="button"
                    className="notifications-btn"
                    aria-label="Notificaciones"
                    onClick={(e) => {
                      e.stopPropagation();
                      setNotifOpen((v) => !v);
                    }}
                  >
                    <span className="notifications-icon" aria-hidden>🔔</span>
                    {unreadCount > 0 && (
                      <span className="notifications-badge">{unreadCount > 99 ? '99+' : unreadCount}</span>
                    )}
                  </button>
                  {notifOpen && (
                    <div className="notifications-panel">
                      <div className="notifications-header">
                        <strong>Novedades</strong>
                        <button type="button" className="notifications-mark-all" onClick={handleMarkAllRead}>
                          Marcar todas
                        </button>
                      </div>
                      {notifications.length === 0 ? (
                        <p className="notifications-empty">No hay notificaciones.</p>
                      ) : (
                        <ul className="notifications-list">
                          {notifications.map((n) => (
                            <li key={n.id} className={`notifications-item ${n.is_read ? '' : 'is-unread'}`}>
                              <div className="notifications-item-top">
                                <strong>{n.title}</strong>
                                {!n.is_read && (
                                  <button
                                    type="button"
                                    className="notifications-read-one"
                                    onClick={() => handleMarkRead(n.id)}
                                  >
                                    Marcar leída
                                  </button>
                                )}
                              </div>
                              <p>{n.message}</p>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </div>
              )}
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
