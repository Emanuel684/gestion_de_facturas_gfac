import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  getOrganizationInvoiceStatuses,
  createOrganizationInvoiceStatus,
  patchOrganizationInvoiceStatus,
  deleteOrganizationInvoiceStatus,
} from '../api';
import '../pages/InvoiceStatusesPage.css';

/**
 * Gestión de estados de cobranza para una organización tenant (vista plataforma super-usuario).
 */
export default function PlatformOrgInvoiceStatusesPanel({ organizationId, onChanged }) {
  const { t } = useTranslation(['invoiceStatuses', 'organizations']);
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
      const r = await getOrganizationInvoiceStatuses(organizationId);
      setRows(r.data || []);
    } catch (e) {
      setError(e.response?.data?.detail || t('invoiceStatuses:loadError'));
    } finally {
      setLoading(false);
    }
  }, [organizationId, t]);

  useEffect(() => {
    load();
  }, [load]);

  const notifyParent = async () => {
    if (onChanged) await onChanged();
  };

  const saveRow = async (row, patch) => {
    setSavingId(row.id);
    setError('');
    try {
      await patchOrganizationInvoiceStatus(organizationId, row.id, patch);
      await load();
      await notifyParent();
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
      await deleteOrganizationInvoiceStatus(organizationId, row.id);
      await load();
      await notifyParent();
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
      await createOrganizationInvoiceStatus(organizationId, {
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
      await notifyParent();
    } catch (e) {
      setError(e.response?.data?.detail || t('invoiceStatuses:createError'));
    } finally {
      setCreating(false);
    }
  };

  return (
    <section className="org-detail-card org-detail-statuses-card">
      <div className="org-detail-section-head">
        <h2>{t('organizations:detail.platformStatusesTitle')}</h2>
      </div>
      <p className="org-detail-muted">{t('organizations:detail.platformStatusesHint')}</p>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="spinner-center">
          <div className="spinner" />
        </div>
      ) : (
        <>
          <section className="statuses-section">
            <h3 className="org-detail-subh3">{t('invoiceStatuses:addCustom')}</h3>
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
            <h3 className="org-detail-subh3">{t('invoiceStatuses:tableTitle')}</h3>
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
                      <td>
                        <code>{row.key}</code>
                      </td>
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
    </section>
  );
}
