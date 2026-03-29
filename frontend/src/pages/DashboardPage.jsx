import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { getTenantDashboard } from '../api';
import './DashboardPage.css';

function fmtMoney(n) {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(Number(n));
}

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = {};
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      const r = await getTenantDashboard(params);
      setStats(r.data);
    } catch {
      setError('No se pudo cargar el dashboard.');
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo]);

  useEffect(() => {
    load();
  }, [load]);

  const monthly = stats?.monthly ?? [];
  const maxAmt = Math.max(...monthly.map((m) => Number(m.total_amount) || 0), 1);

  return (
    <div className="App">
      <Navbar />
      <main className="dashboard-main">
        <div className="dashboard-header">
          <h1>Dashboard</h1>
          <p className="dashboard-sub">Resumen de facturas de su organización</p>
          <Link to="/app/reportes" className="link-reportes">
            Ir a reportes (PDF / Excel) →
          </Link>
        </div>

        <div className="dashboard-filters">
          <label>
            Desde
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </label>
          <label>
            Hasta
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </label>
          <button type="button" className="btn btn-secondary btn-sm" onClick={load} disabled={loading}>
            Actualizar
          </button>
        </div>

        {error && <div className="form-error dashboard-error">{error}</div>}
        {loading && !stats && <p className="muted">Cargando…</p>}

        {stats && (
          <>
            <div className="kpi-grid">
              <div className="kpi-card">
                <span className="kpi-label">Total facturas</span>
                <span className="kpi-value">{stats.total_invoices}</span>
              </div>
              <div className="kpi-card kpi-accent">
                <span className="kpi-label">Monto total</span>
                <span className="kpi-value">{fmtMoney(stats.total_amount)}</span>
              </div>
              <div className="kpi-card">
                <span className="kpi-label">Pendientes de pago (próx. 7 días)</span>
                <span className="kpi-value">{stats.pending_due_within_7_days}</span>
              </div>
            </div>

            <div className="status-grid">
              <h2>Por estado</h2>
              <div className="status-cards">
                {['pendiente', 'pagada', 'vencida'].map((k) => (
                  <div key={k} className={`status-card status-${k}`}>
                    <div className="status-name">{k}</div>
                    <div className="status-count">{stats.count_by_status?.[k] ?? 0}</div>
                    <div className="status-amt">{fmtMoney(stats.amount_by_status?.[k])}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="chart-block">
              <h2>Facturación por mes</h2>
              {monthly.length === 0 ? (
                <p className="muted">Sin datos en el rango seleccionado.</p>
              ) : (
                <div className="bar-chart">
                  {monthly.map((m) => (
                    <div key={m.month} className="bar-row">
                      <span className="bar-label">{m.month}</span>
                      <div className="bar-track">
                        <div
                          className="bar-fill"
                          style={{ width: `${(Number(m.total_amount) / maxAmt) * 100}%` }}
                        />
                      </div>
                      <span className="bar-meta">
                        {m.invoice_count} doc. · {fmtMoney(m.total_amount)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
