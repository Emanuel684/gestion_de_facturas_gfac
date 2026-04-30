import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { login, getMe } from '../api';
import { useAuth } from '../context/AuthContext';
import './LoginPage.css';

export default function LoginPage() {
  const { t } = useTranslation(['auth']);
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [organizationSlug, setOrganizationSlug] = useState('demo');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('user');
    try {
      const { data } = await login(organizationSlug.trim(), username, password);
      sessionStorage.setItem('token', data.access_token);
      const me = await getMe();
      signIn(data.access_token, me.data);
      if (me.data.role === 'plataforma_admin') {
        navigate('/app/organizaciones', { replace: true });
      } else {
        navigate('/app', { replace: true });
      }
    } catch (err) {
      sessionStorage.removeItem('token');
      sessionStorage.removeItem('user');
      const d = err.response?.data?.detail;
      setError(typeof d === 'string' ? d : 'Error al iniciar sesión. Verifique organización y credenciales.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-bg">
      <div className="login-card">
        <div className="login-logo">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
            <rect width="40" height="40" rx="10" fill="#0e7490"/>
            <path d="M10 14h20M10 20h20M10 26h14" stroke="white" strokeWidth="2.5" strokeLinecap="round"/>
          </svg>
          <h1>{t('auth:loginTitle')}</h1>
        </div>
        <p className="login-subtitle">{t('auth:loginSubtitle')}</p>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="org">{t('auth:organization')}</label>
            <input
              id="org"
              type="text"
              value={organizationSlug}
              onChange={(e) => setOrganizationSlug(e.target.value)}
              placeholder="demo"
              required
              autoFocus
            />
          </div>
          <div className="form-group">
            <label htmlFor="username">{t('auth:user')}</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">{t('auth:password')}</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>

          {error && <div className="alert alert-error">{error}</div>}

          <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
            {loading ? t('auth:loginLoading') : t('auth:loginButton')}
          </button>
        </form>

        {import.meta.env.DEV && (
          <div className="login-hint">
            <strong>Demo cliente:</strong> organización <code>demo</code> — admin / admin123 · maria / maria123 · carlos / carlos123
            <br />
            <strong>Plataforma:</strong> organización <code>plataforma</code> — super / super123
          </div>
        )}

        <p className="login-back">
          <Link to="/">← {t('auth:loginBack')}</Link>
        </p>
      </div>
    </div>
  );
}
