import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { completePublicCheckout, getPublicCheckout } from '../api';

export default function MockCheckoutPage() {
  const { sessionToken } = useParams();
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    getPublicCheckout(sessionToken)
      .then((r) => setSession(r.data))
      .catch(() => setMessage('No se pudo cargar el checkout'))
      .finally(() => setLoading(false));
  }, [sessionToken]);

  const complete = async (outcome) => {
    setActionLoading(true);
    try {
      await completePublicCheckout(sessionToken, outcome);
      setMessage(outcome === 'paid' ? 'Pago aprobado. Ya puedes iniciar sesion.' : 'Pago rechazado.');
      if (outcome === 'paid') {
        setTimeout(() => navigate('/login', { replace: true }), 1400);
      }
    } catch (err) {
      setMessage(err.response?.data?.detail || 'No se pudo procesar el pago');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return <div className="spinner-center"><div className="spinner" /></div>;
  if (!session) return <main><h2>Checkout no disponible</h2></main>;

  return (
    <main style={{ maxWidth: 720 }}>
      <h1>Checkout Mock</h1>
      <p>Sesion: <code>{session.session_token}</code></p>
      <p>Plan: <strong>{session.plan_tier}</strong></p>
      <p>Monto: <strong>${session.amount} {session.currency}</strong></p>
      <p>Estado: <strong>{session.status}</strong></p>
      {message && <div className={message.includes('aprobado') ? 'alert' : 'alert alert-error'}>{message}</div>}
      <div style={{ display: 'flex', gap: 12, marginTop: 12 }}>
        <button className="btn btn-primary" onClick={() => complete('paid')} disabled={actionLoading || session.status !== 'created'}>
          Simular pago exitoso
        </button>
        <button className="btn btn-secondary" onClick={() => complete('failed')} disabled={actionLoading || session.status !== 'created'}>
          Simular pago fallido
        </button>
        <Link className="btn btn-secondary" to="/login">Ir al login</Link>
      </div>
    </main>
  );
}

