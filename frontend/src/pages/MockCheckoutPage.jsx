import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { completePublicCheckout, getPublicCheckout } from '../api';
import { useAuth } from '../context/AuthContext';
import './MockCheckoutPage.css';

function formatCurrency(amount, currency = 'COP') {
  const n = typeof amount === 'string' ? parseFloat(amount, 10) : amount;
  if (Number.isNaN(n)) return String(amount);
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: currency || 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(n);
}

const STATUS_LABELS = {
  created: 'Pendiente de pago',
  completed: 'Completado',
  expired: 'Expirado',
};

export default function MockCheckoutPage() {
  const { t } = useTranslation(['auth']);
  const { sessionToken } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    setError('');
    getPublicCheckout(sessionToken)
      .then((r) => setSession(r.data))
      .catch(() => setError('No se pudo cargar la sesión de pago. Revise el enlace o solicite uno nuevo.'))
      .finally(() => setLoading(false));
  }, [sessionToken]);

  const complete = async (outcome) => {
    setActionLoading(true);
    setMessage('');
    try {
      await completePublicCheckout(sessionToken, outcome);
      if (outcome === 'paid') {
        setMessage(
          user
            ? 'Pago registrado correctamente. Redirigiendo a facturación…'
            : 'Pago aprobado. Ya puede iniciar sesión.'
        );
        setTimeout(() => {
          navigate(user ? '/app/billing' : '/login', { replace: true });
        }, 1400);
      } else {
        setMessage('El pago fue rechazado (simulación). Puede intentar de nuevo si la sesión sigue activa.');
      }
    } catch (err) {
      const d = err.response?.data?.detail;
      setMessage(typeof d === 'string' ? d : 'No se pudo procesar el pago.');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="checkout-mock-bg">
        <div className="spinner-center">
          <div className="spinner" />
        </div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="checkout-mock-bg">
        <div className="checkout-mock-card">
          <div className="checkout-mock-logo">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden>
              <rect width="40" height="40" rx="10" fill="#0e7490" />
              <path
                d="M10 14h20M10 20h20M10 26h14"
                stroke="white"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            </svg>
          <h1>{t('auth:mockUnavailable', { defaultValue: 'Pago no disponible' })}</h1>
          </div>
          <p className="checkout-mock-sub">{error || 'No se encontró la sesión de checkout.'}</p>
          <p className="checkout-mock-footer">
            <Link to={user ? '/app/billing' : '/'}>{user ? '← Volver a facturación' : '← Volver al inicio'}</Link>
          </p>
        </div>
      </div>
    );
  }

  const isExpired = session.status === 'expired';
  const isDone = session.status === 'completed';
  const canAct = session.status === 'created' && !isExpired && !isDone;

  return (
    <div className="checkout-mock-bg">
      <div className="checkout-mock-card">
        <div className="checkout-mock-logo">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden>
            <rect width="40" height="40" rx="10" fill="#0e7490" />
            <path
              d="M10 14h20M10 20h20M10 26h14"
              stroke="white"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </svg>
          <h1>{t('auth:mockTitle')}</h1>
        </div>
        <p className="checkout-mock-sub">
          {t('auth:mockSubtitle')}
        </p>

        <p className="checkout-mock-detail">
          <strong>Plan:</strong> {session.plan_tier}
        </p>
        <p className="checkout-mock-detail">
          <strong>Monto:</strong> {formatCurrency(session.amount, session.currency)}
        </p>
        <p className="checkout-mock-detail">
          <strong>Estado:</strong> {STATUS_LABELS[session.status] || session.status}
        </p>
        {isExpired && (
          <div className="alert alert-error">Esta sesión expiró. Genere un nuevo pago desde facturación o registro.</div>
        )}
        {isDone && (
          <div className="checkout-mock-msg-info">Esta sesión ya fue procesada.</div>
        )}

        {message && (
          <div
            className={
              message.includes('correctamente') || message.includes('aprobado')
                ? 'checkout-mock-msg-ok'
                : 'alert alert-error'
            }
          >
            {message}
          </div>
        )}

        <div className="checkout-mock-actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => complete('paid')}
            disabled={actionLoading || !canAct}
          >
            {actionLoading ? 'Procesando…' : 'Simular pago exitoso'}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => complete('failed')}
            disabled={actionLoading || !canAct}
          >
            Simular pago fallido
          </button>
        </div>

        <p className="checkout-mock-footer">
          <Link to={user ? '/app/billing' : '/login'}>
            {user ? '← Volver a facturación y suscripción' : '← Ir al inicio de sesión'}
          </Link>
          {' · '}
          <Link to="/">Inicio</Link>
        </p>
      </div>
    </div>
  );
}
