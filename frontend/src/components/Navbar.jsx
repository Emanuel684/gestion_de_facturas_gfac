import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../theme/ThemeContext';
import {
  getNotificationsPage,
  getNotificationsUnreadCount,
  markAllNotificationsAsRead,
  markNotificationAsRead,
} from '../api';
import './Navbar.css';

const ROLE_LABELS = {
  plataforma_admin: 'rolePlatform',
  administrador: 'roleAdmin',
  contador: 'roleAccountant',
  asistente: 'roleAssistant',
};

const ROLE_CLASSNAMES = {
  plataforma_admin: 'role-platform',
  administrador: 'role-admin',
  contador: 'role-accountant',
  asistente: 'role-assistant',
};

export default function Navbar() {
  const { t, i18n } = useTranslation(['common', 'navbar']);
  const { theme, toggleTheme } = useTheme();
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
          <rect width="40" height="40" rx="10" fill="var(--color-primary)" />
          <path
            d="M10 14h20M10 20h20M10 26h14"
            stroke="var(--color-on-primary)"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
        </svg>
        {t('navbar:brand')}
      </Link>

      {user && (
        <>
          <button
            type="button"
            className="navbar-menu-btn"
            aria-expanded={menuOpen}
            aria-controls="navbar-mobile-panel"
            aria-label={menuOpen ? t('navbar:closeMenu') : t('navbar:openMenu')}
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
                  {t('navbar:invoices')}
                </Link>
                <Link to="/app/dashboard" className="nav-link" onClick={closeMenu}>
                  {t('navbar:dashboard')}
                </Link>
                <Link to="/app/reportes" className="nav-link" onClick={closeMenu}>
                  {t('navbar:reports')}
                </Link>
                <Link to="/app/users" className="nav-link" onClick={closeMenu}>
                  {t('navbar:users')}
                </Link>
                <Link to="/app/billing" className="nav-link" onClick={closeMenu}>
                  {t('navbar:billing')}
                </Link>
              </div>
            )}
            {isPlatform && (
              <div className="navbar-links">
                <Link to="/app/organizaciones" className="nav-link" onClick={closeMenu}>
                  {t('navbar:organizations')}
                </Link>
                <Link to="/app/plataforma/dashboard" className="nav-link" onClick={closeMenu}>
                  {t('navbar:dashboard')}
                </Link>
                <Link to="/app/plataforma/reportes" className="nav-link" onClick={closeMenu}>
                  {t('navbar:reports')}
                </Link>
              </div>
            )}

            <div className="navbar-right">
              <button
                type="button"
                className="theme-toggle-btn"
                onClick={toggleTheme}
                aria-label={t('common:theme')}
                title={t('common:theme')}
              >
                {theme === 'dark' ? t('common:lightMode') : t('common:darkMode')}
              </button>
              <select
                className="nav-link"
                aria-label={t('common:language')}
                value={i18n.resolvedLanguage?.startsWith('en') ? 'en' : 'es'}
                onChange={(e) => i18n.changeLanguage(e.target.value)}
              >
                <option value="es">{t('common:spanish')}</option>
                <option value="en">{t('common:english')}</option>
              </select>
              {!isPlatform && (
                <div className="notifications-wrap">
                  <button
                    type="button"
                    className="notifications-btn"
                    aria-label={t('navbar:notifications')}
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
                        <strong>{t('navbar:updates')}</strong>
                        <button type="button" className="notifications-mark-all" onClick={handleMarkAllRead}>
                          {t('navbar:markAll')}
                        </button>
                      </div>
                      {notifications.length === 0 ? (
                        <p className="notifications-empty">{t('navbar:emptyNotifications')}</p>
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
                                    {t('navbar:markRead')}
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
                  className={`role-badge ${ROLE_CLASSNAMES[user.role] ?? ''}`}
                >
                  {ROLE_LABELS[user.role] ? t(`navbar:${ROLE_LABELS[user.role]}`) : user.role}
                </span>
                <span className="navbar-user-text">
                  {user.username}
                  {user.organization?.name && (
                    <span className="navbar-org"> · {user.organization.name}</span>
                  )}
                </span>
              </span>
              <button type="button" className="btn btn-secondary btn-sm" onClick={handleLogout}>
                {t('common:closeSession')}
              </button>
            </div>
          </div>
          {menuOpen && (
            <button
              type="button"
              className="navbar-backdrop"
              aria-label={t('navbar:closeMenu')}
              onClick={closeMenu}
            />
          )}
        </>
      )}
    </nav>
  );
}
