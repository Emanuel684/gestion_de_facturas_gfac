import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { createUser, updateUser } from '../api';
import './InvoiceModal.css';
import './UserModal.css';

const ROLES = ['administrador', 'contador', 'asistente'];

function formatApiError(err, fallback) {
  const d = err.response?.data?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join(' ');
  return fallback;
}

const emptyForm = () => ({
  username: '',
  email: '',
  password: '',
  role: 'asistente',
  is_active: true,
});

export default function UserModal({ user = null, onSuccess, onClose }) {
  const { t } = useTranslation(['modals']);
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
      setError(t('modals:user.validationUsernameMin'));
      return;
    }
    if (!isEdit && form.password.length < 6) {
      setError(t('modals:user.validationPasswordMin'));
      return;
    }
    if (isEdit && form.password.length > 0 && form.password.length < 6) {
      setError(t('modals:user.validationPasswordEditMin'));
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
      setError(formatApiError(err, t('modals:user.saveError')));
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
          <h2>{isEdit ? t('modals:editUser') : t('modals:newUser')}</h2>
          <button type="button" className="modal-close" onClick={onClose} aria-label={t('modals:close')}>
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="um-username">{t('modals:user.username')}</label>
              <input
                id="um-username"
                type="text"
                value={form.username}
                onChange={set('username')}
                placeholder={t('modals:user.usernamePlaceholder')}
                required
                autoFocus
              />
            </div>
            <div className="form-group">
              <label htmlFor="um-role">{t('modals:user.role')}</label>
              <select id="um-role" value={form.role} onChange={set('role')}>
                {ROLES.map((roleValue) => (
                  <option key={roleValue} value={roleValue}>
                    {t(`modals:user.roles.${roleValue === 'administrador' ? 'admin' : roleValue === 'contador' ? 'accountant' : 'assistant'}`)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="um-email">{t('modals:user.email')}</label>
            <input
              id="um-email"
              type="email"
              value={form.email}
              onChange={set('email')}
              placeholder={t('modals:user.emailPlaceholder')}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="um-password">{isEdit ? t('modals:user.newPassword') : t('modals:user.password')}</label>
            <input
              id="um-password"
              type="password"
              value={form.password}
              onChange={set('password')}
              placeholder={isEdit ? t('modals:user.newPasswordPlaceholder') : t('modals:user.passwordPlaceholder')}
              required={!isEdit}
              minLength={isEdit ? undefined : 6}
              autoComplete={isEdit ? 'new-password' : 'new-password'}
            />
          </div>

          {isEdit && (
            <label className="user-modal-checkbox">
              <input type="checkbox" checked={form.is_active} onChange={set('is_active')} />
              <span>{t('modals:user.activeUserHint')}</span>
            </label>
          )}

          {error && <div className="alert alert-error">{error}</div>}

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              {t('modals:cancel')}
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? t('modals:saving') : isEdit ? t('modals:saveChanges') : t('modals:createUser')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
