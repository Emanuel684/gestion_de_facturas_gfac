import { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { publicSignup } from '../api';
import './SignupPage.css';

const PLAN_OPTIONS = [
  { value: 'basico', label: 'Básico' },
  { value: 'profesional', label: 'Profesional' },
  { value: 'empresarial', label: 'Empresarial' },
];

export default function SignupPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    name: '',
    slug: '',
    plan_tier: params.get('plan') || 'basico',
    admin_username: '',
    admin_email: '',
    admin_password: '',
  });

  useEffect(() => {
    const plan = params.get('plan');
    if (plan && ['basico', 'profesional', 'empresarial'].includes(plan)) {
      setForm((p) => ({ ...p, plan_tier: plan }));
    }
  }, [params]);

  const handleChange = (e) =>
    setForm((p) => ({ ...p, [e.target.name]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const { data } = await publicSignup(form);
      navigate(`/checkout/mock/${data.checkout_session_token}`, { replace: true });
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(
        typeof d === 'string'
          ? d
          : Array.isArray(d)
            ? d.map((x) => x.msg || JSON.stringify(x)).join(' ')
            : 'No se pudo crear la cuenta. Revise los datos e intente de nuevo.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="signup-bg">
      <div className="signup-card">
        <div className="signup-logo">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden>
            <rect width="40" height="40" rx="10" fill="#0e7490" />
            <path
              d="M10 14h20M10 20h20M10 26h14"
              stroke="white"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </svg>
          <h1>Crear cuenta empresarial</h1>
        </div>
        <p className="signup-subtitle">
          Registre su organización, defina el administrador y continúe al pago del plan elegido.
        </p>

        <form onSubmit={onSubmit} className="signup-form" noValidate>
          <div className="signup-section">
            <div className="signup-section-title">Organización</div>
            <div className="form-group">
              <label htmlFor="name">Nombre de la organización</label>
              <input
                id="name"
                name="name"
                type="text"
                value={form.name}
                onChange={handleChange}
                placeholder="Ej. Mi empresa S.A.S."
                required
                autoComplete="organization"
                autoFocus
              />
            </div>
            <div className="signup-row">
              <div className="form-group">
                <label htmlFor="slug">Identificador (slug)</label>
                <input
                  id="slug"
                  name="slug"
                  type="text"
                  value={form.slug}
                  onChange={handleChange}
                  placeholder="mi-empresa"
                  required
                  autoComplete="off"
                  spellCheck="false"
                />
              </div>
              <div className="form-group">
                <label htmlFor="plan_tier">Plan</label>
                <select
                  id="plan_tier"
                  name="plan_tier"
                  value={form.plan_tier}
                  onChange={handleChange}
                >
                  {PLAN_OPTIONS.map((p) => (
                    <option key={p.value} value={p.value}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <p className="signup-hint">
              El slug se usa en la URL de acceso (solo letras minúsculas, números y guiones).
            </p>
          </div>

          <div className="signup-section">
            <div className="signup-section-title">Administrador</div>
            <div className="form-group">
              <label htmlFor="admin_username">Usuario</label>
              <input
                id="admin_username"
                name="admin_username"
                type="text"
                value={form.admin_username}
                onChange={handleChange}
                placeholder="admin"
                required
                autoComplete="username"
              />
            </div>
            <div className="form-group">
              <label htmlFor="admin_email">Correo electrónico</label>
              <input
                id="admin_email"
                name="admin_email"
                type="email"
                value={form.admin_email}
                onChange={handleChange}
                placeholder="admin@empresa.com"
                required
                autoComplete="email"
              />
            </div>
            <div className="form-group">
              <label htmlFor="admin_password">Contraseña</label>
              <input
                id="admin_password"
                name="admin_password"
                type="password"
                value={form.admin_password}
                onChange={handleChange}
                placeholder="••••••••"
                required
                autoComplete="new-password"
                minLength={6}
              />
            </div>
          </div>

          {error && <div className="alert alert-error">{error}</div>}

          <button className="btn btn-primary btn-full" disabled={loading} type="submit">
            {loading ? 'Creando cuenta…' : 'Continuar al pago'}
          </button>
        </form>

        <div className="signup-footer">
          <div className="signup-footer-row">
            <Link to="/">← Volver al inicio</Link>
            <span aria-hidden>·</span>
            <Link to="/login">¿Ya tiene cuenta? Iniciar sesión</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
