import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
  getCollectionStatuses,
  createCollectionStatus,
  patchCollectionStatus,
  deleteCollectionStatus,
} from '../api';
import Navbar from '../components/Navbar';
import './InvoiceStatusesPage.css';

export default function InvoiceStatusesPage() {
  const { t } = useTranslation(['invoiceStatuses', 'common']);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [savingId, setSavingId] = useState(null);
  const [newKey, setNewKey] = useState('');
  const [newLabel, setNewLabel] = useState('');
  const [newSort, setNewSort] = useState(10);
  const [newAuto, setNewAuto] = useState(false);
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const r = await getCollectionStatuses();
      setRows(r.data);
    } catch (e) {
      setError(e.response?.data?.detail || t('invoiceStatuses:loadError'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    load();
  }, [load]);

  const saveRow = async (row, patch) => {
    setSavingId(row.id);
    setError('');
    try {
      await patchCollectionStatus(row.id, patch);
      await load();
    } catch (e) {
      setError(e.response?.data?.detail || t('invoiceStatuses:saveError'));
    } finally {
      setSavingId(null);
    }
  };

  const handleDelete = async (row) => {
    if (!window.confirm(t('invoiceStatuses:deleteConfirm', { label: row.label }))) return;
    setSavingId(row.id);
    setError('');
    try {
      await deleteCollectionStatus(row.id);
      await load();
    } catch (e) {
      setError(e.response?.data?.detail || t('invoiceStatuses:deleteError'));
    } finally {
      setSavingId(null);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setCreating(true);
    setError('');
    try {
      await createCollectionStatus({
        key: newKey.trim().toLowerCase(),
        label: newLabel.trim(),
        sort_order: Number(newSort) || 0,
        auto_overdue_eligible: newAuto,
      });
      setNewKey('');
      setNewLabel('');
      setNewSort(10);
      setNewAuto(false);
      await load();
    } catch (e) {
      setError(e.response?.data?.detail || t('invoiceStatuses:createError'));
    } finally {
      setCreating(false);
    }
  };

  return (
    <>
      <Navbar />
      <main className="statuses-main">
        <div className="statuses-header">
          <div>
            <Link to="/app" className="statuses-back">
              ← {t('invoiceStatuses:backInvoices')}
            </Link>
            <h1>{t('invoiceStatuses:title')}</h1>
            <p className="statuses-intro">{t('invoiceStatuses:intro')}</p>
          </div>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {loading ? (
          <div className="spinner-center">
            <div className="spinner" />
          </div>
        ) : (
          <>
            <section className="statuses-section">
              <h2>{t('invoiceStatuses:addCustom')}</h2>
              <form className="statuses-new-form" onSubmit={handleCreate}>
                <input
                  type="text"
                  placeholder={t('invoiceStatuses:keyPlaceholder')}
                  value={newKey}
                  onChange={(e) => setNewKey(e.target.value)}
                  required
                  pattern="[a-z][a-z0-9_]*"
                  title={t('invoiceStatuses:keyPattern')}
                />
                <input
                  type="text"
                  placeholder={t('invoiceStatuses:labelPlaceholder')}
                  value={newLabel}
                  onChange={(e) => setNewLabel(e.target.value)}
                  required
                />
                <input
                  type="number"
                  className="statuses-sort-input"
                  value={newSort}
                  onChange={(e) => setNewSort(e.target.value)}
                  min={0}
                  max={999}
                />
                <label className="statuses-check">
                  <input type="checkbox" checked={newAuto} onChange={(e) => setNewAuto(e.target.checked)} />
                  {t('invoiceStatuses:autoOverdue')}
                </label>
                <button type="submit" className="btn btn-primary" disabled={creating}>
                  {creating ? t('invoiceStatuses:creating') : t('invoiceStatuses:create')}
                </button>
              </form>
            </section>

            <section className="statuses-section">
              <h2>{t('invoiceStatuses:tableTitle')}</h2>
              <div className="statuses-table-wrap">
                <table className="statuses-table">
                  <thead>
                    <tr>
                      <th>{t('invoiceStatuses:colKey')}</th>
                      <th>{t('invoiceStatuses:colLabel')}</th>
                      <th>{t('invoiceStatuses:colSort')}</th>
                      <th>{t('invoiceStatuses:colAuto')}</th>
                      <th>{t('invoiceStatuses:colReserved')}</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr key={row.id}>
                        <td><code>{row.key}</code></td>
                        <td>
                          <input
                            type="text"
                            className="statuses-inline-input"
                            defaultValue={row.label}
                            disabled={savingId === row.id}
                            onBlur={(e) => {
                              const v = e.target.value.trim();
                              if (v && v !== row.label) saveRow(row, { label: v });
                            }}
                          />
                        </td>
                        <td>
                          <input
                            type="number"
                            className="statuses-sort-input"
                            defaultValue={row.sort_order}
                            disabled={savingId === row.id}
                            onBlur={(e) => {
                              const v = parseInt(e.target.value, 10);
                              if (!Number.isNaN(v) && v !== row.sort_order) saveRow(row, { sort_order: v });
                            }}
                          />
                        </td>
                        <td>
                          <input
                            type="checkbox"
                            defaultChecked={row.auto_overdue_eligible}
                            disabled={savingId === row.id}
                            onChange={(e) => saveRow(row, { auto_overdue_eligible: e.target.checked })}
                          />
                        </td>
                        <td>{row.is_reserved ? t('invoiceStatuses:yes') : t('invoiceStatuses:no')}</td>
                        <td>
                          {!row.is_reserved && (
                            <button
                              type="button"
                              className="btn btn-secondary btn-sm"
                              disabled={savingId === row.id}
                              onClick={() => handleDelete(row)}
                            >
                              {t('invoiceStatuses:delete')}
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </main>
    </>
  );
}
