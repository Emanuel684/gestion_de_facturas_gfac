import { createContext, useContext, useState, useEffect } from 'react';
import { getMe, logout } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem('user')); } catch { return null; }
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe()
      .then((r) => {
        setUser(r.data);
        sessionStorage.setItem('user', JSON.stringify(r.data));
      })
      .catch(() => {
        sessionStorage.removeItem('token');
        sessionStorage.removeItem('user');
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const signIn = (token, userData) => {
    if (token) {
      sessionStorage.setItem('token', token);
    }
    sessionStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
  };

  const signOut = async () => {
    try {
      await logout();
    } catch {
      /* ignore */
    }
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('user');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
