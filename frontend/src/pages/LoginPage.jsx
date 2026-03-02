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
      // Store token first so the axios interceptor sends it with the /me request
      localStorage.setItem('token', data.access_token);
      const me = await getMe();
      signIn(data.access_token, me.data);
      navigate('/', { replace: true });
    } catch (err) {
      localStorage.removeItem('token');
      setError(err.response?.data?.detail || 'Login failed. Check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-bg">
      <div className="login-card">
        <div className="login-logo">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
            <rect width="40" height="40" rx="10" fill="#4f46e5"/>
            <path d="M12 20l6 6 10-12" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <h1>Task Manager</h1>
        </div>
        <p className="login-subtitle">Sign in to your workspace</p>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="username">Username</label>
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
            <label htmlFor="password">Password</label>
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
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div className="login-hint">
          <strong>Default accounts:</strong><br/>
          admin / admin123 (owner) &nbsp;·&nbsp; alice / alice123 (member)
        </div>
      </div>
    </div>
  );
}
