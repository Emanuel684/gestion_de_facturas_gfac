import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
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
  { value: '', labelKey: 'common:allStatuses' },
  { value: 'pendiente', labelKey: 'common:pending' },
  { value: 'pagada', labelKey: 'common:paid' },
  { value: 'vencida', labelKey: 'common:overdue' },
];

export default function PlatformDashboardPage() {
  const { t } = useTranslation(['platform', 'common']);
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
        if (!cancelled) setError(t('platform:loadOrgError'));
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
      setError(t('platform:loadDashboardError'));
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
          <h1 className="sgf-page-title">{t('platform:dashboardTitle')}</h1>
          <p className="sgf-page-sub">
            {t('platform:dashboardSub')}
          </p>
          <Link to="/app/plataforma/reportes" className="sgf-page-link">
            {t('platform:goReports')}
          </Link>
        </header>

        <div className="sgf-panel sgf-panel--flush">
          <h2 className="sgf-panel-title">{t('platform:globalFilters')}</h2>
          <div className="sgf-toolbar">
            <div className="sgf-field">
              <span className="sgf-field-label">{t('platform:orgLabel')}</span>
              <select
                className="sgf-select"
                value={orgId}
                onChange={(e) => setOrgId(e.target.value)}
                disabled={loading}
              >
                <option value="">{t('platform:selectOption')}</option>
                {orgs.map((o) => (
                  <option key={o.id} value={String(o.id)}>
                    {o.name} ({o.slug})
                  </option>
                ))}
              </select>
            </div>
            <div className="sgf-field">
              <span className="sgf-field-label">{t('platform:kpiStatusLabel')}</span>
              <select
                className="sgf-select"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                {STATUSES.map((s) => (
                  <option key={s.value || 'all'} value={s.value}>
                    {t(s.labelKey)}
                  </option>
                ))}
              </select>
            </div>
          </div>
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
                {loadingStats ? t('common:loading') : t('common:update')}
              </button>
            </div>
          </div>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <section className="sgf-rank-panel">
          <div className="sgf-section-head sgf-section-head--tight">
            <h2 className="sgf-section-title">{t('platform:topOrganizationsTitle')}</h2>
            <p className="sgf-section-sub">{t('platform:topOrganizationsSub')}</p>
          </div>
          <ChartCard title={t('platform:visualRankingTitle')} subtitle={t('platform:visualRankingSub')} className="platform-rank-chart">
            <TopOrganizationsBarChart rows={top} maxBars={12} />
          </ChartCard>
          <div className="sgf-rank-table-wrap">
            <table className="sgf-rank-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>{t('platform:tableOrg')}</th>
                  <th>{t('platform:tableInvoices')}</th>
                  <th>{t('platform:tableTotalBilled')}</th>
                </tr>
              </thead>
              <tbody>
                {top.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="sgf-muted">
                      {t('platform:emptyRange')}
                    </td>
                  </tr>
                ) : (
                  top.map((row, i) => (
                    <tr key={row.organization_id}>
                      <td data-label={t('platform:tablePosition')}>{i + 1}</td>
                      <td data-label={t('platform:tableOrg')}>
                        {row.name} <span className="sgf-rank-slug">({row.slug})</span>
                      </td>
                      <td data-label={t('platform:tableInvoices')}>{row.invoice_count}</td>
                      <td data-label={t('platform:tableTotalBilled')}>{moneyFmt(row.total_amount, 'es-CO')}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        {!orgId && (
          <p className="sgf-empty-hint">{t('platform:selectOrg')}</p>
        )}

        {orgId && loadingStats && !stats && <p className="sgf-muted">{t('common:loading')}</p>}

        {stats && (
          <>
            <h2 className="sgf-title-accent">{t('platform:detailPrefix', { name: stats.organization_name })}</h2>
            <div className="sgf-kpi-row">
              <div className="sgf-kpi">
                <span className="sgf-kpi-label">{t('platform:kpiTotalInvoices')}</span>
                <span className="sgf-kpi-value">{stats.total_invoices}</span>
              </div>
              <div className="sgf-kpi sgf-kpi--teal">
                <span className="sgf-kpi-label">{t('platform:kpiTotalAmount')}</span>
                <span className="sgf-kpi-value">{moneyFmt(stats.total_amount)}</span>
              </div>
              <div className="sgf-kpi sgf-kpi--amber">
                <span className="sgf-kpi-label">{t('platform:kpiPending7Days')}</span>
                <span className="sgf-kpi-value">{stats.pending_due_within_7_days}</span>
              </div>
            </div>

            <div className="sgf-section-head">
              <h2 className="sgf-section-title">{t('platform:visualizationTitle')}</h2>
              <p className="sgf-section-sub">{t('platform:visualizationSub')}</p>
            </div>
            <DashboardChartsGrid stats={stats} />
          </>
        )}
      </main>
    </div>
  );
}
