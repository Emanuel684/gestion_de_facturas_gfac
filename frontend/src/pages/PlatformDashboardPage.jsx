import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { listOrganizations, getPlatformDashboard, getPlatformTopOrganizations } from '../api';
import {
  DashboardChartsGrid,
  moneyFmt,
  TopOrganizationsBarChart,
  ChartCard,
} from '../components/charts/DashboardCharts';
import DateRangePresetBar from '../components/charts/DateRangePresetBar';
import { getDateRangePreset } from '../utils/dateRangePresets';
import './DashboardPage.css';
import './PlatformInsights.css';
import '../components/charts/Charts.css';

const STATUSES = [
  { value: '', label: 'Todos' },
  { value: 'pendiente', label: 'Pendiente' },
  { value: 'pagada', label: 'Pagada' },
  { value: 'vencida', label: 'Vencida' },
];

export default function PlatformDashboardPage() {
  const [orgs, setOrgs] = useState([]);
  const [orgId, setOrgId] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [stats, setStats] = useState(null);
  const [top, setTop] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingStats, setLoadingStats] = useState(false);
  const [error, setError] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [presetActive, setPresetActive] = useState(null);

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
    return () => {
      cancelled = true;
    };
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
      if (statusFilter) params.status = statusFilter;
      const r = await getPlatformDashboard(Number(orgId), params);
      setStats(r.data);
    } catch {
      setError('No se pudo cargar el dashboard de la organización.');
      setStats(null);
    } finally {
      setLoadingStats(false);
    }
  }, [orgId, dateFrom, dateTo, statusFilter]);

  useEffect(() => {
    loadTop();
  }, [loadTop]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const applyPreset = (key) => {
    const { dateFrom: f, dateTo: t } = getDateRangePreset(key);
    setDateFrom(f);
    setDateTo(t);
    setPresetActive(key);
  };

  return (
    <div className="App">
      <Navbar />
      <main className="dashboard-main platform-insights">
        <div className="dashboard-header">
          <h1>Dashboard de plataforma</h1>
          <p className="dashboard-sub">
            Elija organización para KPIs detallados. El ranking compara facturación entre clientes.
          </p>
          <Link to="/app/plataforma/reportes" className="link-reportes">
            Ir a reportes (PDF / Excel) →
          </Link>
        </div>

        <div className="platform-org-row">
          <label className="platform-org-label">
            Organización
            <select value={orgId} onChange={(e) => setOrgId(e.target.value)} disabled={loading}>
              <option value="">— Seleccione —</option>
              {orgs.map((o) => (
                <option key={o.id} value={String(o.id)}>
                  {o.name} ({o.slug})
                </option>
              ))}
            </select>
          </label>
          <label className="platform-org-label platform-status-filter">
            Estado (KPIs)
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              {STATUSES.map((s) => (
                <option key={s.value || 'all'} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <DateRangePresetBar activeKey={presetActive} onSelect={applyPreset} />

        <div className="dashboard-filters">
          <label>
            Desde
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => {
                setDateFrom(e.target.value);
                setPresetActive(null);
              }}
            />
          </label>
          <label>
            Hasta
            <input
              type="date"
              value={dateTo}
              onChange={(e) => {
                setDateTo(e.target.value);
                setPresetActive(null);
              }}
            />
          </label>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => {
              loadTop();
              loadDashboard();
            }}
            disabled={loadingStats}
          >
            {loadingStats ? 'Actualizando…' : 'Actualizar'}
          </button>
        </div>

        {error && <div className="form-error dashboard-error">{error}</div>}

        <section className="platform-rank-section">
          <h2>Organizaciones con mayor facturación</h2>
          <p className="muted small">Suma de montos en el rango (org. plataforma excluida).</p>
          <ChartCard title="Ranking visual" subtitle="Top por monto total facturado" className="platform-rank-chart">
            <TopOrganizationsBarChart rows={top} maxBars={12} />
          </ChartCard>
          <div className="rank-table-wrap platform-rank-table">
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
                  <tr>
                    <td colSpan={4} className="muted">
                      Sin datos en el rango.
                    </td>
                  </tr>
                ) : (
                  top.map((row, i) => (
                    <tr key={row.organization_id}>
                      <td>{i + 1}</td>
                      <td>
                        {row.name} <span className="slug">({row.slug})</span>
                      </td>
                      <td>{row.invoice_count}</td>
                      <td>{moneyFmt(row.total_amount)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        {!orgId && <p className="muted platform-pick-hint">Seleccione una organización para ver KPIs y gráficos detallados.</p>}

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
                <span className="kpi-value">{moneyFmt(stats.total_amount)}</span>
              </div>
              <div className="kpi-card">
                <span className="kpi-label">Pendientes (vencen en 7 días)</span>
                <span className="kpi-value">{stats.pending_due_within_7_days}</span>
              </div>
            </div>

            <div className="dashboard-charts-section">
              <h2 className="dashboard-section-title">Visualización</h2>
              <DashboardChartsGrid stats={stats} />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
