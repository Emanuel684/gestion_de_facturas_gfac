import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { localeFromLanguage } from '../utils/locale';
import { completePublicCheckout, getPublicCheckout } from '../api';
import { useAuth } from '../context/AuthContext';
import './MockCheckoutPage.css';

function formatCurrency(amount, locale, currency = 'COP') {
  const n = typeof amount === 'string' ? parseFloat(amount, 10) : amount;
  if (Number.isNaN(n)) return String(amount);
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currency || 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(n);
}

export default function MockCheckoutPage() {
  const { t, i18n } = useTranslation(['auth', 'common']);
  const locale = localeFromLanguage(i18n.resolvedLanguage);
  const { sessionToken } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('info');
  const [error, setError] = useState('');

  useEffect(() => {
    setError('');
    getPublicCheckout(sessionToken)
      .then((r) => setSession(r.data))
      .catch(() => setError(t('auth:mockLoadError')))
      .finally(() => setLoading(false));
  }, [sessionToken]);

  const complete = async (outcome) => {
    setActionLoading(true);
    setMessage('');
    setMessageType('info');
    try {
      await completePublicCheckout(sessionToken, outcome);
      if (outcome === 'paid') {
        setMessage(
          user
            ? t('auth:mockProcessingSuccessUser')
            : t('auth:mockProcessingSuccessGuest')
        );
        setMessageType('success');
        setTimeout(() => {
          navigate(user ? '/app/billing' : '/login', { replace: true });
        }, 1400);
      } else {
        setMessage(t('auth:mockProcessingFailed'));
        setMessageType('error');
      }
    } catch (err) {
      const d = err.response?.data?.detail;
      setMessage(typeof d === 'string' ? d : t('auth:mockProcessingError'));
      setMessageType('error');
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
          <p className="checkout-mock-sub">{error || t('auth:mockSessionNotFound')}</p>
          <p className="checkout-mock-footer">
            <Link to={user ? '/app/billing' : '/'}>{user ? t('auth:mockBackBilling') : t('auth:mockBackHome')}</Link>
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
          <strong>{t('auth:mockPlan')}:</strong> {session.plan_tier}
        </p>
        <p className="checkout-mock-detail">
          <strong>{t('auth:mockAmount')}:</strong> {formatCurrency(session.amount, locale, session.currency)}
        </p>
        <p className="checkout-mock-detail">
          <strong>{t('auth:mockStatus')}:</strong> {t(`auth:checkoutStatuses.${session.status}`)}
        </p>
        {isExpired && (
          <div className="alert alert-error">{t('auth:mockExpired')}</div>
        )}
        {isDone && (
          <div className="checkout-mock-msg-info">{t('auth:mockAlreadyProcessed')}</div>
        )}

        {message && (
          <div
            className={
              messageType === 'success'
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
            {actionLoading ? t('common:loading') : t('auth:mockSimulateSuccess')}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => complete('failed')}
            disabled={actionLoading || !canAct}
          >
            {t('auth:mockSimulateFailure')}
          </button>
        </div>

        <p className="checkout-mock-footer">
          <Link to={user ? '/app/billing' : '/login'}>
            {user ? t('auth:mockBackBillingSubscription') : t('auth:mockGoLogin')}
          </Link>
          {' · '}
          <Link to="/">{t('auth:home')}</Link>
        </p>
      </div>
    </div>
  );
}
