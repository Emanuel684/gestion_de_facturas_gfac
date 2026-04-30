import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { getUsers, deleteUser } from '../api';
import { useAuth } from '../context/AuthContext';
import UserModal from '../components/UserModal';
import Navbar from '../components/Navbar';
import './UsersPage.css';

const ROLE_LABELS = {
  administrador: 'Administrador',
  contador: 'Contador',
  asistente: 'Asistente',
};

const ROLE_COLORS = {
  administrador: 'role-admin',
  contador: 'role-contador',
  asistente: 'role-asistente',
};

export default function UsersPage() {
  const { t, i18n } = useTranslation(['users']);
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  /** `undefined` = modal cerrado; `null` = crear; objeto = editar */
  const [modalUser, setModalUser] = useState(undefined);
  const [deletingId, setDeletingId] = useState(null);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const resp = await getUsers();
      setUsers(resp.data);
    } catch {
      setError(t('users:loadError'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const isAdmin = user?.role === 'administrador';

  const handleUserSaved = (saved) => {
    setUsers((prev) => {
      const exists = prev.some((x) => x.id === saved.id);
      const next = exists ? prev.map((x) => (x.id === saved.id ? saved : x)) : [...prev, saved];
      return next.sort((a, b) => a.username.localeCompare(b.username));
    });
    setModalUser(undefined);
  };

  const handleDeleteUser = async (u) => {
    if (u.id === user?.id) return;
    const msg = t('users:confirmDelete', { username: u.username });
    if (!window.confirm(msg)) return;
    setDeletingId(u.id);
    try {
      await deleteUser(u.id);
      await fetchUsers();
    } catch (err) {
      const d = err.response?.data?.detail;
      const text = typeof d === 'string' ? d : Array.isArray(d) ? d.map((e) => e.msg).join(' ') : t('users:deleteError');
      alert(text);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <>
      <Navbar />
      <main className="users-main">
        <div className="users-header">
          <div>
            <h2 className="users-title">👥 {t('users:title')}</h2>
            <p className="users-sub">
              {t('users:activeUsers', { count: users.length })}
            </p>
          </div>
          {isAdmin && (
            <button className="btn btn-primary" onClick={() => setModalUser(null)}>
              ＋ {t('users:newUser')}
            </button>
          )}
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {loading ? (
          <div className="spinner-center"><div className="spinner" /></div>
        ) : users.length === 0 ? (
          <div className="empty-state">
            <p>{t('users:noneFound')}</p>
          </div>
        ) : (
          <div className="users-grid">
            {users.map((u) => (
              <div key={u.id} className="user-card">
                <div className="user-card-header">
                  <span className={`role-tag ${ROLE_COLORS[u.role] || ''}`}>
                    {ROLE_LABELS[u.role] || u.role}
                  </span>
                  <div className="user-card-header-right">
                    {isAdmin && (
                      <button
                        type="button"
                        className="user-edit-btn"
                        title={t('users:editUser')}
                        onClick={() => setModalUser(u)}
                      >
                        {t('users:editUser')}
                      </button>
                    )}
                    {isAdmin && u.id !== user?.id && (
                      <button
                        type="button"
                        className="user-delete-btn"
                        title={t('users:deleteUser')}
                        disabled={deletingId === u.id}
                        onClick={() => handleDeleteUser(u)}
                      >
                        ✕
                      </button>
                    )}
                    <span
                      className={`status-dot ${u.is_active ? 'active' : 'inactive'}`}
                      title={u.is_active ? t('users:active') : t('users:inactive')}
                    />
                  </div>
                </div>
                <h3 className="user-name">{u.username}</h3>
                <p className="user-email">{u.email}</p>
                <p className="user-since">
                  {t('users:since')} {new Date(u.created_at).toLocaleDateString(i18n.resolvedLanguage === 'en' ? 'en-US' : 'es-CO')}
                </p>
              </div>
            ))}
          </div>
        )}
      </main>

      {modalUser !== undefined && (
        <UserModal
          key={modalUser === null ? 'new' : modalUser.id}
          user={modalUser}
          onSuccess={handleUserSaved}
          onClose={() => setModalUser(undefined)}
        />
      )}
    </>
  );
}
