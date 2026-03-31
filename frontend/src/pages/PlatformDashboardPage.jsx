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
      <main className="sgf-page">
        <header className="sgf-page-header">
          <h1 className="sgf-page-title">Dashboard de plataforma</h1>
          <p className="sgf-page-sub">
            Elija organización para KPIs detallados. El ranking compara facturación entre clientes.
          </p>
          <Link to="/app/plataforma/reportes" className="sgf-page-link">
            Ir a reportes (PDF / Excel) →
          </Link>
        </header>

        <div className="sgf-panel sgf-panel--flush">
          <h2 className="sgf-panel-title">Filtros globales</h2>
          <div className="sgf-toolbar">
            <div className="sgf-field">
              <span className="sgf-field-label">Organización</span>
              <select
                className="sgf-select"
                value={orgId}
                onChange={(e) => setOrgId(e.target.value)}
                disabled={loading}
              >
                <option value="">— Seleccione —</option>
                {orgs.map((o) => (
                  <option key={o.id} value={String(o.id)}>
                    {o.name} ({o.slug})
                  </option>
                ))}
              </select>
            </div>
            <div className="sgf-field">
              <span className="sgf-field-label">Estado (KPIs)</span>
              <select
                className="sgf-select"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                {STATUSES.map((s) => (
                  <option key={s.value || 'all'} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <DateRangePresetBar activeKey={presetActive} onSelect={applyPreset} />
          <div className="sgf-toolbar sgf-toolbar--spaced">
            <div className="sgf-field">
              <span className="sgf-field-label">Desde</span>
              <input
                className="sgf-input"
                type="date"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value);
                  setPresetActive(null);
                }}
              />
            </div>
            <div className="sgf-field">
              <span className="sgf-field-label">Hasta</span>
              <input
                className="sgf-input"
                type="date"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value);
                  setPresetActive(null);
                }}
              />
            </div>
            <div className="sgf-toolbar-actions">
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
          </div>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <section className="sgf-rank-panel">
          <div className="sgf-section-head sgf-section-head--tight">
            <h2 className="sgf-section-title">Organizaciones con mayor facturación</h2>
            <p className="sgf-section-sub">Suma de montos en el rango (organización plataforma excluida)</p>
          </div>
          <ChartCard title="Ranking visual" subtitle="Top por monto total facturado" className="platform-rank-chart">
            <TopOrganizationsBarChart rows={top} maxBars={12} />
          </ChartCard>
          <div className="sgf-rank-table-wrap">
            <table className="sgf-rank-table">
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
                    <td colSpan={4} className="sgf-muted">
                      Sin datos en el rango.
                    </td>
                  </tr>
                ) : (
                  top.map((row, i) => (
                    <tr key={row.organization_id}>
                      <td data-label="Posición">{i + 1}</td>
                      <td data-label="Organización">
                        {row.name} <span className="sgf-rank-slug">({row.slug})</span>
                      </td>
                      <td data-label="Facturas">{row.invoice_count}</td>
                      <td data-label="Total facturado">{moneyFmt(row.total_amount)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        {!orgId && (
          <p className="sgf-empty-hint">
            Seleccione una organización para ver KPIs y gráficos detallados.
          </p>
        )}

        {orgId && loadingStats && !stats && <p className="sgf-muted">Cargando…</p>}

        {stats && (
          <>
            <h2 className="sgf-title-accent">Detalle: {stats.organization_name}</h2>
            <div className="sgf-kpi-row">
              <div className="sgf-kpi">
                <span className="sgf-kpi-label">Total facturas</span>
                <span className="sgf-kpi-value">{stats.total_invoices}</span>
              </div>
              <div className="sgf-kpi sgf-kpi--teal">
                <span className="sgf-kpi-label">Monto total</span>
                <span className="sgf-kpi-value">{moneyFmt(stats.total_amount)}</span>
              </div>
              <div className="sgf-kpi sgf-kpi--amber">
                <span className="sgf-kpi-label">Pendientes (vencen en 7 días)</span>
                <span className="sgf-kpi-value">{stats.pending_due_within_7_days}</span>
              </div>
            </div>

            <div className="sgf-section-head">
              <h2 className="sgf-section-title">Visualización</h2>
              <p className="sgf-section-sub">Mismos gráficos que en la vista web</p>
            </div>
            <DashboardChartsGrid stats={stats} />
          </>
        )}
      </main>
    </div>
  );
}
