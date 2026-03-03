import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login, getMe } from '../api';
import { useAuth } from '../context/AuthContext';
import './LoginPage.css';

export default function LoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { data } = await login(username, password);
      localStorage.setItem('token', data.access_token);
      const me = await getMe();
      signIn(data.access_token, me.data);
      navigate('/', { replace: true });
    } catch (err) {
      localStorage.removeItem('token');
      setError(err.response?.data?.detail || 'Error al iniciar sesión. Verifique sus credenciales.');
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
          <h1>Gestión de Facturas</h1>
        </div>
        <p className="login-subtitle">Inicie sesión en el sistema SGF</p>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="username">Usuario</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin"
              required
              autoFocus
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">Contraseña</label>
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
            {loading ? 'Ingresando…' : 'Iniciar Sesión'}
          </button>
        </form>

        <div className="login-hint">
          <strong>Cuentas predeterminadas:</strong><br/>
          admin / admin123 (Administrador) &nbsp;·&nbsp; maria / maria123 (Contador) &nbsp;·&nbsp; carlos / carlos123 (Asistente)
        </div>
      </div>
    </div>
  );
}
