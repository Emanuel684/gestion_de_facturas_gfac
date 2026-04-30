import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Navbar from '../components/Navbar';
import { getTenantDashboard } from '../api';
import { DashboardChartsGrid, moneyFmt } from '../components/charts/DashboardCharts';
import DateRangePresetBar from '../components/charts/DateRangePresetBar';
import { getDateRangePreset } from '../utils/dateRangePresets';
import '../components/charts/Charts.css';

export default function DashboardPage() {
  const { t } = useTranslation(['dashboard', 'common']);
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
      setError(t('dashboard:loadError', { defaultValue: 'No se pudo cargar el dashboard.' }));
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
      <main className="sgf-page">
        <header className="sgf-page-header">
          <h1 className="sgf-page-title">{t('dashboard:title')}</h1>
          <p className="sgf-page-sub">{t('dashboard:subtitle')}</p>
          <Link to="/app/reportes" className="sgf-page-link">
            {t('dashboard:goReports')}
          </Link>
        </header>

        <div className="sgf-panel sgf-panel--flush">
          <DateRangePresetBar activeKey={presetActive} onSelect={applyPreset} />
          <div className="sgf-toolbar sgf-toolbar--spaced">
            <div className="sgf-field">
              <span className="sgf-field-label">{t('common:from')}</span>
              <input
                className="sgf-input"
                type="date"
                value={dateFrom}
                onChange={onDateFromChange}
              />
            </div>
            <div className="sgf-field">
              <span className="sgf-field-label">{t('common:to')}</span>
              <input className="sgf-input" type="date" value={dateTo} onChange={onDateToChange} />
            </div>
            <div className="sgf-toolbar-actions">
              <button type="button" className="btn btn-secondary btn-sm" onClick={load} disabled={loading}>
                {loading ? t('dashboard:updating', { defaultValue: 'Actualizando...' }) : t('common:update')}
              </button>
            </div>
          </div>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {loading && !stats && (
          <div className="sgf-skeleton-row" aria-hidden>
            <div className="sgf-skeleton-block" />
            <div className="sgf-skeleton-block" />
            <div className="sgf-skeleton-block" />
          </div>
        )}

        {stats && (
          <>
            <div className="sgf-kpi-row">
              <div className="sgf-kpi">
                <span className="sgf-kpi-label">{t('dashboard:totalInvoices')}</span>
                <span className="sgf-kpi-value">{stats.total_invoices}</span>
              </div>
              <div className="sgf-kpi sgf-kpi--teal">
                <span className="sgf-kpi-label">{t('dashboard:totalAmount')}</span>
                <span className="sgf-kpi-value">{moneyFmt(stats.total_amount)}</span>
              </div>
              <div className="sgf-kpi sgf-kpi--amber">
                <span className="sgf-kpi-label">{t('dashboard:pendingNext7')}</span>
                <span className="sgf-kpi-value">{stats.pending_due_within_7_days}</span>
              </div>
            </div>

            <div className="sgf-section-head">
              <h2 className="sgf-section-title">{t('dashboard:visualization')}</h2>
              <p className="sgf-section-sub">{t('dashboard:visualizationSub')}</p>
            </div>
            <DashboardChartsGrid stats={stats} />

            {stats.total_invoices === 0 && (
              <p className="sgf-empty-hint">
                {t('dashboard:emptyPeriod')}
              </p>
            )}
          </>
        )}
      </main>
    </div>
  );
}
