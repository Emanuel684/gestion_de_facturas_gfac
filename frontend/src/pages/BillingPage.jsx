import { useEffect, useState, useCallback } from 'react';
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

function formatCurrency(amount, currency = 'COP') {
  const n = typeof amount === 'string' ? parseFloat(amount, 10) : amount;
  if (Number.isNaN(n)) return amount;
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: currency || 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(n);
}

function formatDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('es-CO', {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  } catch {
    return iso;
  }
}

function formatApiError(err) {
  const d = err.response?.data?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join('; ');
  return 'Ocurrió un error.';
}

export default function BillingPage() {
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
      setError(formatApiError(err));
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
      setError(formatApiError(err));
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
          <h1 className="billing-title">Facturación y suscripción</h1>
          <p className="billing-sub">
            Consulte su plan, fechas de renovación y el historial de pagos simulados.
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
                <h2 id="sub-heading">Estado de la suscripción</h2>
                <div className="billing-grid">
                  <div className="billing-field">
                    <label>Plan</label>
                    <span>{planLabel(subscription.plan_tier)}</span>
                  </div>
                  <div className="billing-field">
                    <label>Estado</label>
                    <span className={subClass}>{subLabel(subscription.status)}</span>
                  </div>
                  <div className="billing-field">
                    <label>Próximo cobro</label>
                    <span>{formatDate(subscription.next_due_date)}</span>
                  </div>
                  <div className="billing-field">
                    <label>Gracia hasta</label>
                    <span>{formatDate(subscription.grace_expires_at)}</span>
                  </div>
                  <div className="billing-field">
                    <label>Periodo actual</label>
                    <span>
                      {subscription.current_period_start && subscription.current_period_end
                        ? `${formatDate(subscription.current_period_start)} — ${formatDate(subscription.current_period_end)}`
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
                    {checkoutLoading ? 'Abriendo pago…' : 'Pagar o renovar plan (simulado)'}
                  </button>
                </div>
              </section>
            )}

            <section className="billing-card" aria-labelledby="pay-heading">
              <h2 id="pay-heading">Historial de pagos</h2>
              {payments.length === 0 ? (
                <p className="billing-empty-payments">No hay pagos registrados aún.</p>
              ) : (
                payments.map((p) => (
                  <div key={p.id} className="billing-payment-row">
                    <span className="billing-pay-id">#{p.id}</span>
                    <span className="billing-pay-meta">
                      {formatDate(p.created_at)} · {p.provider}
                    </span>
                    <span className="billing-pay-amount">
                      {formatCurrency(p.amount, p.currency)}
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
