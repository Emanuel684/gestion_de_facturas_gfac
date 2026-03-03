import { useState, useEffect, useCallback } from 'react';
import { getUsers } from '../api';
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
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modalOpen, setModalOpen] = useState(false);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const resp = await getUsers();
      setUsers(resp.data);
    } catch {
      setError('Error al cargar usuarios.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const isAdmin = user?.role === 'administrador';

  const handleUserCreated = (newUser) => {
    setUsers((prev) => [...prev, newUser].sort((a, b) => a.username.localeCompare(b.username)));
    setModalOpen(false);
  };

  return (
    <>
      <Navbar />
      <main className="users-main">
        <div className="users-header">
          <div>
            <h2 className="users-title">👥 Usuarios</h2>
            <p className="users-sub">
              {users.length} usuario{users.length !== 1 ? 's' : ''} activo{users.length !== 1 ? 's' : ''}
            </p>
          </div>
          {isAdmin && (
            <button className="btn btn-primary" onClick={() => setModalOpen(true)}>
              ＋ Nuevo Usuario
            </button>
          )}
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {loading ? (
          <div className="spinner-center"><div className="spinner" /></div>
        ) : users.length === 0 ? (
          <div className="empty-state">
            <p>No se encontraron usuarios.</p>
          </div>
        ) : (
          <div className="users-grid">
            {users.map((u) => (
              <div key={u.id} className="user-card">
                <div className="user-card-header">
                  <span className={`role-tag ${ROLE_COLORS[u.role] || ''}`}>
                    {ROLE_LABELS[u.role] || u.role}
                  </span>
                  <span className={`status-dot ${u.is_active ? 'active' : 'inactive'}`}
                        title={u.is_active ? 'Activo' : 'Inactivo'} />
                </div>
                <h3 className="user-name">{u.username}</h3>
                <p className="user-email">{u.email}</p>
                <p className="user-since">
                  Desde {new Date(u.created_at).toLocaleDateString('es-CO')}
                </p>
              </div>
            ))}
          </div>
        )}
      </main>

      {modalOpen && (
        <UserModal
          onSuccess={handleUserCreated}
          onClose={() => setModalOpen(false)}
        />
      )}
    </>
  );
}
