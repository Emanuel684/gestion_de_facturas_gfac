import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Navbar from '../components/Navbar';
import { getTenantDashboard, exportTenantReport } from '../api';
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

export default function ReportsPage() {
  const { t } = useTranslation(['reports', 'common']);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [status, setStatus] = useState('');
  const [presetActive, setPresetActive] = useState(null);
  const [loading, setLoading] = useState(null);
  const [loadingCharts, setLoadingCharts] = useState(true);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');
  const [chartError, setChartError] = useState('');

  const buildParams = () => {
    const params = {};
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    if (status) params.status = status;
    return params;
  };

  const loadCharts = useCallback(async () => {
    setLoadingCharts(true);
    setChartError('');
    try {
      const params = {};
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      if (status) params.status = status;
      const r = await getTenantDashboard(params);
      setStats(r.data);
    } catch {
      setChartError(t('reports:chartError'));
      setStats(null);
    } finally {
      setLoadingCharts(false);
    }
  }, [dateFrom, dateTo, status]);

  useEffect(() => {
    loadCharts();
  }, [loadCharts]);

  const applyPreset = (key) => {
    const { dateFrom: f, dateTo: t } = getDateRangePreset(key);
    setDateFrom(f);
    setDateTo(t);
    setPresetActive(key);
  };

  const download = async (format) => {
    setError('');
    setLoading(format);
    try {
      const res = await exportTenantReport(format, buildParams());
      const blob = res.data;
      const cd = res.headers['content-disposition'] || '';
      const m = /filename="?([^";]+)"?/i.exec(cd);
      const name = m ? m[1].trim() : `facturas.${format === 'xlsx' ? 'xlsx' : 'pdf'}`;
      triggerDownload(blob, name);
    } catch {
      setError(t('reports:downloadError'));
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="App">
      <Navbar />
      <main className="sgf-page">
        <header className="sgf-page-header">
          <h1 className="sgf-page-title">{t('reports:title')}</h1>
          <p className="sgf-page-sub">
            {t('reports:subtitle')}
          </p>
          <Link to="/app/dashboard" className="sgf-page-link">
            {t('reports:backDashboard')}
          </Link>
        </header>

        <div className="sgf-panel sgf-panel--flush">
          <h2 className="sgf-panel-title">{t('reports:filtersTitle')}</h2>
          <DateRangePresetBar activeKey={presetActive} onSelect={applyPreset} />
          <div className="sgf-toolbar sgf-toolbar--spaced">
            <div className="sgf-field">
              <span className="sgf-field-label">{t('common:from')}</span>
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
              <span className="sgf-field-label">{t('common:to')}</span>
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
              <span className="sgf-field-label">{t('reports:status')}</span>
              <select
                className="sgf-select"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
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
                disabled={loading}
                onClick={() => download('xlsx')}
              >
                {loading === 'xlsx' ? t('reports:generating') : t('reports:downloadExcel')}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={loading}
                onClick={() => download('pdf')}
              >
                {loading === 'pdf' ? t('reports:generating') : t('reports:downloadPdf')}
              </button>
            </div>
          </div>
          {error && <div className="alert alert-error">{error}</div>}
          <p className="sgf-report-hint">
            {t('reports:hint')}
          </p>
        </div>

        <div className="sgf-panel">
          <div className="sgf-section-head sgf-section-head--tight">
            <h2 className="sgf-section-title">{t('reports:previewTitle')}</h2>
            <p className="sgf-section-sub">{t('reports:previewSub')}</p>
          </div>
          {chartError && <div className="alert alert-error">{chartError}</div>}
          {loadingCharts && (
            <div className="sgf-skeleton-chart" aria-hidden />
          )}
          {!loadingCharts && stats && (
            <>
              <DashboardChartsGrid stats={stats} />
              {stats.total_invoices === 0 && (
                <p className="sgf-empty-hint">{t('reports:noGraphData')}</p>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
