import { useEffect, useState } from 'react';
import { createCheckout, getPayments, getSubscription } from '../api';
import Navbar from '../components/Navbar';

export default function BillingPage() {
  const [subscription, setSubscription] = useState(null);
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [subRes, payRes] = await Promise.all([getSubscription(), getPayments()]);
      setSubscription(subRes.data);
      setPayments(payRes.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const onPay = async () => {
    if (!subscription) return;
    const { data } = await createCheckout(subscription.plan_tier);
    window.location.href = data.checkout_url;
  };

  return (
    <div className="App">
      <Navbar />
      <main>
        <h1>Facturacion y suscripcion</h1>
        {loading ? (
          <div className="spinner-center"><div className="spinner" /></div>
        ) : (
          <>
            {subscription && (
              <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: 16, marginBottom: 16 }}>
                <p><strong>Plan:</strong> {subscription.plan_tier}</p>
                <p><strong>Estado:</strong> {subscription.status}</p>
                <p><strong>Proximo cobro:</strong> {subscription.next_due_date || 'N/A'}</p>
                <p><strong>Gracia hasta:</strong> {subscription.grace_expires_at || 'N/A'}</p>
                <button className="btn btn-primary" onClick={onPay}>Pagar renovacion</button>
              </div>
            )}
            <h3>Historial de pagos</h3>
            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: 16 }}>
              {payments.length === 0 && <p>No hay pagos registrados.</p>}
              {payments.map((p) => (
                <div key={p.id} style={{ padding: '8px 0', borderBottom: '1px solid #f3f4f6' }}>
                  #{p.id} · {p.status} · ${p.amount} {p.currency} · {p.created_at}
                </div>
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}

