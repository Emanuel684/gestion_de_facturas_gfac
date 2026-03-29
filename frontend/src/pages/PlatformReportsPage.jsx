import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { listOrganizations, exportPlatformReport, getPlatformDashboard } from '../api';
import { DashboardChartsGrid } from '../components/charts/DashboardCharts';
import DateRangePresetBar from '../components/charts/DateRangePresetBar';
import { getDateRangePreset } from '../utils/dateRangePresets';
import '../components/charts/Charts.css';

const STATUSES = [
  { value: '', label: 'Todos los estados' },
  { value: 'pendiente', label: 'Pendiente' },
  { value: 'pagada', label: 'Pagada' },
  { value: 'vencida', label: 'Vencida' },
];

function triggerDownload(blob, fallbackName) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fallbackName;
  a.click();
  window.URL.revokeObjectURL(url);
}

export default function PlatformReportsPage() {
  const [orgs, setOrgs] = useState([]);
  const [orgId, setOrgId] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [status, setStatus] = useState('');
  const [presetActive, setPresetActive] = useState(null);
  const [loading, setLoading] = useState(null);
  const [loadingCharts, setLoadingCharts] = useState(false);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');
  const [chartError, setChartError] = useState('');

  useEffect(() => {
    listOrganizations()
      .then((r) => setOrgs(r.data || []))
      .catch(() => setError('No se pudieron cargar las organizaciones.'));
  }, []);

  const loadCharts = useCallback(async () => {
    if (!orgId) {
      setStats(null);
      return;
    }
    setLoadingCharts(true);
    setChartError('');
    try {
      const params = {};
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      if (status) params.status = status;
      const r = await getPlatformDashboard(Number(orgId), params);
      setStats(r.data);
    } catch {
      setChartError('No se pudieron cargar los gráficos.');
      setStats(null);
    } finally {
      setLoadingCharts(false);
    }
  }, [orgId, dateFrom, dateTo, status]);

  useEffect(() => {
    loadCharts();
  }, [loadCharts]);

  const buildExportParams = () => {
    const params = {};
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    if (status) params.status = status;
    return params;
  };

  const applyPreset = (key) => {
    const { dateFrom: f, dateTo: t } = getDateRangePreset(key);
    setDateFrom(f);
    setDateTo(t);
    setPresetActive(key);
  };

  const download = async (format) => {
    if (!orgId) {
      setError('Seleccione una organización.');
      return;
    }
    setError('');
    setLoading(format);
    try {
      const res = await exportPlatformReport(Number(orgId), format, buildExportParams());
      const blob = res.data;
      const cd = res.headers['content-disposition'] || '';
      const m = /filename="?([^";]+)"?/i.exec(cd);
      const name = m ? m[1].trim() : `facturas.${format === 'xlsx' ? 'xlsx' : 'pdf'}`;
      triggerDownload(blob, name);
    } catch {
      setError('No se pudo generar el archivo. Intente de nuevo.');
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="App">
      <Navbar />
      <main className="sgf-page">
        <header className="sgf-page-header">
          <h1 className="sgf-page-title">Reportes (plataforma)</h1>
          <p className="sgf-page-sub">Exporte y visualice todas las facturas de la organización elegida.</p>
          <Link to="/app/plataforma/dashboard" className="sgf-page-link">
            ← Volver al dashboard
          </Link>
        </header>

        <div className="sgf-panel sgf-panel--flush">
          <h2 className="sgf-panel-title">Filtros y descarga</h2>
          <DateRangePresetBar activeKey={presetActive} onSelect={applyPreset} />
          <div className="sgf-toolbar sgf-toolbar--spaced">
            <div className="sgf-field">
              <span className="sgf-field-label">Organización</span>
              <select className="sgf-select" value={orgId} onChange={(e) => setOrgId(e.target.value)}>
                <option value="">— Seleccione —</option>
                {orgs.map((o) => (
                  <option key={o.id} value={String(o.id)}>
                    {o.name} ({o.slug})
                  </option>
                ))}
              </select>
            </div>
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
            <div className="sgf-field">
              <span className="sgf-field-label">Estado</span>
              <select className="sgf-select" value={status} onChange={(e) => setStatus(e.target.value)}>
                {STATUSES.map((s) => (
                  <option key={s.value || 'all'} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="sgf-toolbar-actions">
              <button
                type="button"
                className="btn btn-primary"
                disabled={loading || !orgId}
                onClick={() => download('xlsx')}
              >
                {loading === 'xlsx' ? 'Generando…' : 'Descargar Excel'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={loading || !orgId}
                onClick={() => download('pdf')}
              >
                {loading === 'pdf' ? 'Generando…' : 'Descargar PDF'}
              </button>
            </div>
          </div>
          {error && <div className="alert alert-error">{error}</div>}
          <p className="sgf-report-hint">Vista de auditoría: incluye todas las facturas de la organización.</p>
        </div>

        {orgId && (
          <div className="sgf-panel">
            <div className="sgf-section-head sgf-section-head--tight">
              <h2 className="sgf-section-title">Vista previa (gráficos)</h2>
              <p className="sgf-section-sub">Mismos criterios que los archivos exportados</p>
            </div>
            {chartError && <div className="alert alert-error">{chartError}</div>}
            {loadingCharts && <div className="sgf-skeleton-chart" aria-hidden />}
            {!loadingCharts && stats && (
              <>
                <DashboardChartsGrid stats={stats} />
                {stats.total_invoices === 0 && (
                  <p className="sgf-empty-hint">Sin datos para graficar con los filtros actuales.</p>
                )}
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
