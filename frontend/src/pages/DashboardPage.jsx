import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { getTenantDashboard } from '../api';
import { DashboardChartsGrid, moneyFmt } from '../components/charts/DashboardCharts';
import DateRangePresetBar from '../components/charts/DateRangePresetBar';
import { getDateRangePreset } from '../utils/dateRangePresets';
import './DashboardPage.css';
import '../components/charts/Charts.css';

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [presetActive, setPresetActive] = useState(null);

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

  const applyPreset = (key) => {
    const { dateFrom: f, dateTo: t } = getDateRangePreset(key);
    setDateFrom(f);
    setDateTo(t);
    setPresetActive(key);
  };

  const onDateFromChange = (e) => {
    setDateFrom(e.target.value);
    setPresetActive(null);
  };

  const onDateToChange = (e) => {
    setDateTo(e.target.value);
    setPresetActive(null);
  };

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

        <DateRangePresetBar activeKey={presetActive} onSelect={applyPreset} />

        <div className="dashboard-filters">
          <label>
            Desde
            <input type="date" value={dateFrom} onChange={onDateFromChange} />
          </label>
          <label>
            Hasta
            <input type="date" value={dateTo} onChange={onDateToChange} />
          </label>
          <button type="button" className="btn btn-secondary btn-sm" onClick={load} disabled={loading}>
            {loading ? 'Actualizando…' : 'Actualizar'}
          </button>
        </div>

        {error && <div className="form-error dashboard-error">{error}</div>}

        {loading && !stats && (
          <div className="dashboard-skeleton" aria-hidden>
            <div className="skeleton-block" />
            <div className="skeleton-block" />
            <div className="skeleton-block" />
          </div>
        )}

        {stats && (
          <>
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
                <span className="kpi-label">Pendientes de pago (próx. 7 días)</span>
                <span className="kpi-value">{stats.pending_due_within_7_days}</span>
              </div>
            </div>

            <div className="dashboard-charts-section">
              <h2 className="dashboard-section-title">Visualización</h2>
              <DashboardChartsGrid stats={stats} />
            </div>

            {stats.total_invoices === 0 && (
              <p className="muted dashboard-zero-hint">
                No hay facturas en el periodo seleccionado. Ajuste las fechas o cree facturas desde el listado.
              </p>
            )}
          </>
        )}
      </main>
    </div>
  );
}
