import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Navbar.css';

const ROLE_COLORS = { owner: '#059669', member: '#4f46e5' };

export default function Navbar() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    signOut();
    navigate('/login', { replace: true });
  };

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand">
        <svg width="26" height="26" viewBox="0 0 40 40" fill="none">
          <rect width="40" height="40" rx="10" fill="#4f46e5"/>
          <path d="M12 20l6 6 10-12" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        Task Manager
      </Link>

      <div className="navbar-right">
        {user && (
          <>
            <span className="navbar-user">
              <span
                className="role-badge"
                style={{ background: ROLE_COLORS[user.role] }}
              >
                {user.role}
              </span>
              {user.username}
            </span>
            <button className="btn btn-secondary btn-sm" onClick={handleLogout}>
              Sign out
            </button>
          </>
        )}
      </div>
    </nav>
  );
}
