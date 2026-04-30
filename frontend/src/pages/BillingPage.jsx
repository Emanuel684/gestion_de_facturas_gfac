import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { createCheckout, getPayments, getSubscription } from '../api';
import Navbar from '../components/Navbar';
import './BillingPage.css';

const PLAN_LABELS = {
  basico: 'Básico',
  profesional: 'Profesional',
  empresarial: 'Empresarial',
};

const SUB_LABELS = {
  active: 'Activa',
  past_due: 'Pago pendiente',
  suspended: 'Suspendida',
  canceled: 'Cancelada',
};

const PAYMENT_LABELS = {
  paid: 'Pagado',
  failed: 'Fallido',
  pending: 'Pendiente',
};

function formatCurrency(amount, currency = 'COP', locale = 'es-CO') {
  const n = typeof amount === 'string' ? parseFloat(amount, 10) : amount;
  if (Number.isNaN(n)) return amount;
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currency || 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(n);
}

function formatDate(iso, locale = 'es-CO') {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString(locale, {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  } catch {
    return iso;
  }
}

function formatApiError(err, t) {
  const d = err.response?.data?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join('; ');
  return t('billing:errorGeneric');
}

export default function BillingPage() {
  const { t, i18n } = useTranslation(['billing']);
  const locale = i18n.resolvedLanguage?.startsWith('en') ? 'en-US' : 'es-CO';
  const [subscription, setSubscription] = useState(null);
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [checkoutLoading, setCheckoutLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [subRes, payRes] = await Promise.all([getSubscription(), getPayments()]);
      setSubscription(subRes.data);
      setPayments(payRes.data);
    } catch (err) {
      setError(formatApiError(err, t));
      setSubscription(null);
      setPayments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onPay = async () => {
    if (!subscription) return;
    setCheckoutLoading(true);
    setError('');
    try {
      const { data } = await createCheckout(subscription.plan_tier);
      window.location.href = data.checkout_url;
    } catch (err) {
      setError(formatApiError(err, t));
    } finally {
      setCheckoutLoading(false);
    }
  };

  const planLabel = (k) => PLAN_LABELS[k] ?? k;
  const subLabel = (k) => SUB_LABELS[k] ?? k;
  const payLabel = (k) => PAYMENT_LABELS[k] ?? k;

  const subClass = subscription?.status ? `billing-sub-${subscription.status}` : '';

  return (
    <>
      <Navbar />
      <main className="billing-main">
        <div className="billing-header">
          <h1 className="billing-title">{t('billing:title')}</h1>
          <p className="billing-sub">
            {t('billing:subtitle')}
          </p>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {loading ? (
          <div className="spinner-center">
            <div className="spinner" />
          </div>
        ) : (
          <>
            {subscription && (
              <section className="billing-card" aria-labelledby="sub-heading">
                <h2 id="sub-heading">{t('billing:subStatusTitle')}</h2>
                <div className="billing-grid">
                  <div className="billing-field">
                    <label>{t('billing:plan')}</label>
                    <span>{planLabel(subscription.plan_tier)}</span>
                  </div>
                  <div className="billing-field">
                    <label>{t('billing:status')}</label>
                    <span className={subClass}>{subLabel(subscription.status)}</span>
                  </div>
                  <div className="billing-field">
                    <label>{t('billing:nextCharge')}</label>
                    <span>{formatDate(subscription.next_due_date, locale)}</span>
                  </div>
                  <div className="billing-field">
                    <label>{t('billing:graceUntil')}</label>
                    <span>{formatDate(subscription.grace_expires_at, locale)}</span>
                  </div>
                  <div className="billing-field">
                    <label>{t('billing:currentPeriod')}</label>
                    <span>
                      {subscription.current_period_start && subscription.current_period_end
                        ? `${formatDate(subscription.current_period_start, locale)} — ${formatDate(subscription.current_period_end, locale)}`
                        : '—'}
                    </span>
                  </div>
                </div>
                <div className="billing-actions">
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={onPay}
                    disabled={checkoutLoading}
                  >
                    {checkoutLoading ? t('billing:openingPayment') : t('billing:payRenew')}
                  </button>
                </div>
              </section>
            )}

            <section className="billing-card" aria-labelledby="pay-heading">
              <h2 id="pay-heading">{t('billing:historyTitle')}</h2>
              {payments.length === 0 ? (
                <p className="billing-empty-payments">{t('billing:noPayments')}</p>
              ) : (
                payments.map((p) => (
                  <div key={p.id} className="billing-payment-row">
                    <span className="billing-pay-id">#{p.id}</span>
                    <span className="billing-pay-meta">
                      {formatDate(p.created_at, locale)} · {p.provider}
                    </span>
                    <span className="billing-pay-amount">
                      {formatCurrency(p.amount, p.currency, locale)}
                    </span>
                    <span
                      className={`billing-pay-status billing-status-${p.status}`}
                    >
                      {payLabel(p.status)}
                    </span>
                  </div>
                ))
              )}
            </section>
          </>
        )}
      </main>
    </>
  );
}
