import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { listOrganizations, getPlatformDashboard, getPlatformTopOrganizations } from '../api';
import './DashboardPage.css';
import './PlatformInsights.css';

function fmtMoney(n) {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(Number(n));
}

export default function PlatformDashboardPage() {
  const [orgs, setOrgs] = useState([]);
  const [orgId, setOrgId] = useState('');
  const [stats, setStats] = useState(null);
  const [top, setTop] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingStats, setLoadingStats] = useState(false);
  const [error, setError] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await listOrganizations();
        if (!cancelled) setOrgs(r.data || []);
      } catch {
        if (!cancelled) setError('No se pudieron cargar las organizaciones.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const loadTop = useCallback(async () => {
    const params = {};
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    const r = await getPlatformTopOrganizations({ limit: 15, ...params });
    setTop(r.data || []);
  }, [dateFrom, dateTo]);

  const loadDashboard = useCallback(async () => {
    if (!orgId) {
      setStats(null);
      return;
    }
    setLoadingStats(true);
    setError('');
    try {
      const params = {};
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      const r = await getPlatformDashboard(Number(orgId), params);
      setStats(r.data);
    } catch {
      setError('No se pudo cargar el dashboard de la organización.');
      setStats(null);
    } finally {
      setLoadingStats(false);
    }
  }, [orgId, dateFrom, dateTo]);

  useEffect(() => {
    loadTop();
  }, [loadTop]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const monthly = stats?.monthly ?? [];
  const maxAmt = Math.max(...monthly.map((m) => Number(m.total_amount) || 0), 1);

  return (
    <div className="App">
      <Navbar />
      <main className="dashboard-main platform-insights">
        <div className="dashboard-header">
          <h1>Dashboard de plataforma</h1>
          <p className="dashboard-sub">
            Seleccione una organización para ver sus indicadores. El ranking muestra facturación por cliente.
          </p>
          <Link to="/app/plataforma/reportes" className="link-reportes">
            Ir a reportes (PDF / Excel) →
          </Link>
        </div>

        <div className="platform-org-row">
          <label className="platform-org-label">
            Organización
            <select
              value={orgId}
              onChange={(e) => setOrgId(e.target.value)}
              disabled={loading}
            >
              <option value="">— Seleccione —</option>
              {orgs.map((o) => (
                <option key={o.id} value={String(o.id)}>{o.name} ({o.slug})</option>
              ))}
            </select>
          </label>
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
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => { loadTop(); loadDashboard(); }} disabled={loadingStats}>
            Actualizar
          </button>
        </div>

        {error && <div className="form-error dashboard-error">{error}</div>}

        <section className="platform-rank-section">
          <h2>Organizaciones con mayor facturación</h2>
          <p className="muted small">Suma de montos de facturas en el rango de fechas (organización de plataforma excluida).</p>
          <div className="rank-table-wrap">
            <table className="rank-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Organización</th>
                  <th>Facturas</th>
                  <th>Total facturado</th>
                </tr>
              </thead>
              <tbody>
                {top.length === 0 ? (
                  <tr><td colSpan={4} className="muted">Sin datos en el rango.</td></tr>
                ) : (
                  top.map((row, i) => (
                    <tr key={row.organization_id}>
                      <td>{i + 1}</td>
                      <td>{row.name} <span className="slug">({row.slug})</span></td>
                      <td>{row.invoice_count}</td>
                      <td>{fmtMoney(row.total_amount)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        {!orgId && (
          <p className="muted platform-pick-hint">Elija una organización arriba para ver el detalle de KPIs.</p>
        )}

        {orgId && loadingStats && !stats && <p className="muted">Cargando…</p>}

        {stats && (
          <>
            <h2 className="platform-detail-title">Detalle: {stats.organization_name}</h2>
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
                <span className="kpi-label">Pendientes (vencen en 7 días)</span>
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
