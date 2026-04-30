import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { getInvoiceTrace, getInvoiceAuditPack } from '../api';
import { localeFromLanguage } from '../utils/locale';
import './InvoiceTraceModal.css';

const EVENT_LABELS = {
  created: 'Documento creado',
  updated: 'Actualización',
  status_changed: 'Cambio de estado DIAN',
  document_locked: 'Documento bloqueado',
  export_generated: 'Exportación / paquete generado',
  external_note: 'Nota externa',
};

function formatApiError(err, t) {
  const d = err.response?.data?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join('; ');
  return t('traceability:genericError');
}

export default function InvoiceTraceModal({ invoiceId, invoiceNumber, onClose }) {
  const { t, i18n } = useTranslation(['traceability', 'modals']);
  const locale = localeFromLanguage(i18n.resolvedLanguage);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [trace, setTrace] = useState(null);
  const [auditLoading, setAuditLoading] = useState(false);

  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError('');
      try {
        const resp = await getInvoiceTrace(invoiceId);
        if (!cancelled) setTrace(resp.data);
      } catch (err) {
        if (!cancelled) setError(formatApiError(err, t));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [invoiceId]);

  const downloadAuditPackJson = async () => {
    setAuditLoading(true);
    try {
      const { data } = await getInvoiceAuditPack(invoiceId, { format: 'json' });
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-pack-${invoiceNumber || invoiceId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(formatApiError(err, t));
    } finally {
      setAuditLoading(false);
    }
  };

  const downloadAuditPackExcel = async () => {
    setAuditLoading(true);
    try {
      const resp = await getInvoiceAuditPack(invoiceId, { format: 'xlsx' });
      const blob = resp.data;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-pack-${invoiceNumber || invoiceId}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(formatApiError(err, t));
    } finally {
      setAuditLoading(false);
    }
  };

  const events = trace?.events ?? [];

  return (
    <div className="trace-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="trace-box">
        <div className="trace-header">
          <div>
            <h2>{t('traceability:title')}</h2>
            <p className="trace-sub">
              {invoiceNumber ? t('traceability:invoice', { number: invoiceNumber }) : t('traceability:id', { id: invoiceId })}
            </p>
          </div>
          <div className="trace-header-actions">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={downloadAuditPackJson}
              disabled={auditLoading || loading}
            >
              {auditLoading ? t('traceability:generating') : t('traceability:downloadJson')}
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={downloadAuditPackExcel}
              disabled={auditLoading || loading}
            >
              {auditLoading ? t('traceability:generating') : t('traceability:downloadExcel')}
            </button>
            <button type="button" className="trace-close" onClick={onClose} aria-label={t('modals:close')}>
              ✕
            </button>
          </div>
        </div>

        <div className="trace-body">
          {loading && <div className="trace-loading">{t('traceability:loading')}</div>}
          {error && <div className="alert alert-error">{error}</div>}
          {!loading && !error && events.length === 0 && (
            <p className="trace-empty">{t('traceability:empty')}</p>
          )}
          {!loading && !error && events.length > 0 && (
            <ul className="trace-timeline">
              {events.map((ev) => (
                <li key={ev.id} className="trace-item">
                  <div className="trace-dot" />
                  <div className="trace-card">
                    <div className="trace-card-head">
                      <strong>{EVENT_LABELS[ev.event_type] || ev.event_type}</strong>
                      <time dateTime={ev.created_at}>
                        {new Date(ev.created_at).toLocaleString(locale)}
                      </time>
                    </div>
                    {ev.actor_user_id != null && (
                      <span className="trace-actor">{t('traceability:userActor', { id: ev.actor_user_id })}</span>
                    )}
                    {ev.payload && Object.keys(ev.payload).length > 0 && (
                      <pre className="trace-payload">{JSON.stringify(ev.payload, null, 2)}</pre>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
