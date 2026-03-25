import { useState, useEffect } from 'react';
import { createUser, updateUser } from '../api';
import './InvoiceModal.css';
import './UserModal.css';

const ROLES = [
  { value: 'administrador', label: 'Administrador' },
  { value: 'contador', label: 'Contador' },
  { value: 'asistente', label: 'Asistente' },
];

function formatApiError(err) {
  const d = err.response?.data?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join(' ');
  return 'Error al guardar el usuario.';
}

const emptyForm = () => ({
  username: '',
  email: '',
  password: '',
  role: 'asistente',
  is_active: true,
});

export default function UserModal({ user = null, onSuccess, onClose }) {
  const isEdit = Boolean(user);

  const [form, setForm] = useState(() => (isEdit ? null : emptyForm()));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isEdit && user) {
      setForm({
        username: user.username,
        email: user.email,
        password: '',
        role: user.role,
        is_active: user.is_active,
      });
    } else if (!isEdit) {
      setForm(emptyForm());
    }
  }, [isEdit, user]);

  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const set = (field) => (e) => {
    const v = field === 'is_active' ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [field]: v }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!form) return;

    if (form.username.trim().length < 3) {
      setError('El nombre de usuario debe tener al menos 3 caracteres.');
      return;
    }
    if (!isEdit && form.password.length < 6) {
      setError('La contraseña debe tener al menos 6 caracteres.');
      return;
    }
    if (isEdit && form.password.length > 0 && form.password.length < 6) {
      setError('Si cambia la contraseña, debe tener al menos 6 caracteres.');
      return;
    }

    setLoading(true);
    try {
      if (isEdit) {
        const payload = {
          username: form.username.trim(),
          email: form.email.trim(),
          role: form.role,
          is_active: form.is_active,
        };
        if (form.password.length >= 6) {
          payload.password = form.password;
        }
        const resp = await updateUser(user.id, payload);
        onSuccess(resp.data);
      } else {
        const resp = await createUser({
          username: form.username.trim(),
          email: form.email.trim(),
          password: form.password,
          role: form.role,
        });
        onSuccess(resp.data);
      }
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  if (!form) {
    return (
      <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
        <div className="modal-box">
          <div className="spinner-center" style={{ padding: '2rem' }}>
            <div className="spinner" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box">
        <div className="modal-header">
          <h2>{isEdit ? 'Editar usuario' : 'Nuevo usuario'}</h2>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Cerrar">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="um-username">Usuario *</label>
              <input
                id="um-username"
                type="text"
                value={form.username}
                onChange={set('username')}
                placeholder="nombre_usuario"
                required
                autoFocus
              />
            </div>
            <div className="form-group">
              <label htmlFor="um-role">Rol *</label>
              <select id="um-role" value={form.role} onChange={set('role')}>
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="um-email">Email *</label>
            <input
              id="um-email"
              type="email"
              value={form.email}
              onChange={set('email')}
              placeholder="usuario@empresa.com"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="um-password">{isEdit ? 'Nueva contraseña' : 'Contraseña *'}</label>
            <input
              id="um-password"
              type="password"
              value={form.password}
              onChange={set('password')}
              placeholder={isEdit ? 'Dejar vacío para no cambiar' : 'Mínimo 6 caracteres'}
              required={!isEdit}
              minLength={isEdit ? undefined : 6}
              autoComplete={isEdit ? 'new-password' : 'new-password'}
            />
          </div>

          {isEdit && (
            <label className="user-modal-checkbox">
              <input type="checkbox" checked={form.is_active} onChange={set('is_active')} />
              <span>Usuario activo (puede iniciar sesión)</span>
            </label>
          )}

          {error && <div className="alert alert-error">{error}</div>}

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Guardando…' : isEdit ? 'Guardar cambios' : 'Crear usuario'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
