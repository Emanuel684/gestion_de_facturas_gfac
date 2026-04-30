import { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { createInvoice, updateInvoice, getFiscalProfile } from '../api';
import './InvoiceModal.css';

const STATUSES = ['pendiente', 'pagada', 'vencida'];

const DOC_TYPES = ['factura_venta', 'nota_credito', 'nota_debito'];

const PREFILL_DOC_TYPES = new Set(['factura_venta', 'nota_credito', 'nota_debito']);

const DIAN_STATUSES = [
  'borrador',
  'lista_para_envio',
  'enviada_proveedor',
  'aceptada_dian',
  'rechazada_dian',
  'contingencia',
];

function defaultIssueLocal() {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

function numOrEmpty(v) {
  if (v === '' || v === null || v === undefined) return '';
  const n = parseFloat(v);
  return Number.isFinite(n) ? String(n) : '';
}

export default function InvoiceModal({
  invoice,
  users,
  onSuccess,
  onClose,
  prefill,
  createHandler = createInvoice,
  updateHandler = updateInvoice,
}) {
  const { t } = useTranslation(['modals']);
  const isEdit = Boolean(invoice);
  const docLocked = isEdit && invoice?.document_locked;
  const formatApiError = (err) => {
    const d = err.response?.data?.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join('; ');
    return t('modals:errorGeneric');
  };

  const initial = useMemo(
    () => ({
      invoice_number: invoice?.invoice_number ?? prefill?.invoice_number ?? '',
      supplier: invoice?.supplier ?? prefill?.supplier ?? '',
      description: invoice?.description ?? prefill?.description ?? '',
      amount: invoice?.amount != null ? String(invoice.amount) : prefill?.amount != null ? String(prefill.amount) : '',
      status: invoice?.status ?? 'pendiente',
      due_date:
        invoice?.due_date
          ? invoice.due_date.slice(0, 16)
          : prefill?.due_date
            ? prefill.due_date.slice(0, 16)
            : '',
      assigned_user_ids: invoice?.assigned_users?.map((u) => u.id) ?? [],
      document_type:
        invoice?.document_type ??
        (prefill?.document_type && PREFILL_DOC_TYPES.has(prefill.document_type)
          ? prefill.document_type
          : 'factura_venta'),
      issue_date: invoice?.issue_date
        ? invoice.issue_date.slice(0, 16)
        : prefill?.issue_date
          ? prefill.issue_date.slice(0, 16)
          : defaultIssueLocal(),
      currency: invoice?.currency ?? prefill?.currency ?? 'COP',
      buyer_id_type: invoice?.buyer_id_type ?? prefill?.buyer_id_type ?? '',
      buyer_id_number: invoice?.buyer_id_number ?? prefill?.buyer_id_number ?? '',
      buyer_name: invoice?.buyer_name ?? prefill?.buyer_name ?? '',
      subtotal:
        invoice?.subtotal != null
          ? String(invoice.subtotal)
          : prefill?.subtotal != null
            ? String(prefill.subtotal)
            : '',
      taxable_base:
        invoice?.taxable_base != null
          ? String(invoice.taxable_base)
          : prefill?.taxable_base != null
            ? String(prefill.taxable_base)
            : '',
      iva_rate:
        invoice?.iva_rate != null
          ? String(invoice.iva_rate)
          : prefill?.iva_rate != null
            ? String(prefill.iva_rate)
            : '0.19',
      iva_amount:
        invoice?.iva_amount != null
          ? String(invoice.iva_amount)
          : prefill?.iva_amount != null
            ? String(prefill.iva_amount)
            : '',
      withholding_amount:
        invoice?.withholding_amount != null
          ? String(invoice.withholding_amount)
          : prefill?.withholding_amount != null
            ? String(prefill.withholding_amount)
            : '',
      total_document:
        invoice?.total_document != null
          ? String(invoice.total_document)
          : prefill?.total_document != null
            ? String(prefill.total_document)
            : '',
      dian_lifecycle_status: invoice?.dian_lifecycle_status ?? 'borrador',
    }),
    [invoice, prefill]
  );

  const [form, setForm] = useState(initial);
  const [fiscalProfile, setFiscalProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setForm(initial);
  }, [initial]);

  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  useEffect(() => {
    getFiscalProfile()
      .then((r) => setFiscalProfile(r.data))
      .catch(() => setFiscalProfile(null));
  }, []);

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const toggleUser = (id) => {
    setForm((f) => ({
      ...f,
      assigned_user_ids: f.assigned_user_ids.includes(id)
        ? f.assigned_user_ids.filter((x) => x !== id)
        : [...f.assigned_user_ids, id],
    }));
  };

  const sellerDisplay = () => {
    if (isEdit && (invoice?.seller_snapshot_nit || invoice?.seller_snapshot_business_name)) {
      return {
        nit: invoice.seller_snapshot_nit,
        dv: invoice.seller_snapshot_dv,
        name: invoice.seller_snapshot_business_name,
      };
    }
    if (fiscalProfile?.nit || fiscalProfile?.business_name) {
      return {
        nit: fiscalProfile.nit,
        dv: fiscalProfile.dv,
        name: fiscalProfile.business_name,
      };
    }
    return null;
  };

  const seller = sellerDisplay();

  const buildPayload = () => {
    const due = form.due_date ? new Date(form.due_date).toISOString() : null;

    if (isEdit && docLocked) {
      return {
        status: form.status,
        due_date: due,
        assigned_user_ids: form.assigned_user_ids,
        dian_lifecycle_status: form.dian_lifecycle_status,
      };
    }

    const payload = {
      invoice_number: form.invoice_number.trim(),
      supplier: form.supplier.trim(),
      description: form.description.trim() || null,
      amount: parseFloat(form.amount),
      status: form.status,
      due_date: due,
      assigned_user_ids: form.assigned_user_ids,
      document_type: form.document_type,
      issue_date: form.issue_date ? new Date(form.issue_date).toISOString() : null,
      currency: form.currency.trim() || 'COP',
      buyer_id_type: form.buyer_id_type.trim() || null,
      buyer_id_number: form.buyer_id_number.trim() || null,
      buyer_name: form.buyer_name.trim() || null,
      dian_lifecycle_status: form.dian_lifecycle_status,
    };

    const sub = numOrEmpty(form.subtotal);
    const tb = numOrEmpty(form.taxable_base);
    const ir = numOrEmpty(form.iva_rate);
    const ia = numOrEmpty(form.iva_amount);
    const wh = numOrEmpty(form.withholding_amount);
    const td = numOrEmpty(form.total_document);

    if (sub !== '') payload.subtotal = parseFloat(sub);
    if (tb !== '') payload.taxable_base = parseFloat(tb);
    if (ir !== '') payload.iva_rate = parseFloat(ir);
    if (ia !== '') payload.iva_amount = parseFloat(ia);
    if (wh !== '') payload.withholding_amount = parseFloat(wh);
    if (td !== '') payload.total_document = parseFloat(td);

    return payload;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    const payload = buildPayload();
    try {
      const resp = isEdit
        ? await updateHandler(invoice.id, payload)
        : await createHandler(payload);
      await Promise.resolve(onSuccess?.(resp.data));
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const fiscalDisabled = Boolean(docLocked);

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box modal-box-wide">
        <div className="modal-header">
          <h2>{isEdit ? t('modals:invoice.titleEdit') : t('modals:invoice.titleNew')}</h2>
          <button className="modal-close" onClick={onClose} aria-label={t('modals:close')}>
            ✕
          </button>
        </div>

        {docLocked && (
          <div className="modal-banner">
            {t('modals:invoice.lockedBanner')}
          </div>
        )}

        <form onSubmit={handleSubmit} className="modal-form">
          <section className="form-section">
            <h3 className="form-section-title">{t('modals:invoice.generalData')}</h3>
            <div className="form-row">
              <div className="form-group">
                <label>{t('modals:invoice.invoiceNumber')}</label>
                <input
                  type="text"
                  value={form.invoice_number}
                  onChange={set('invoice_number')}
                  placeholder="FAC-001"
                  required
                  autoFocus
                  disabled={isEdit}
                />
              </div>
              <div className="form-group">
                <label>{t('modals:invoice.supplier')}</label>
                <input
                  type="text"
                  value={form.supplier}
                  onChange={set('supplier')}
                  placeholder={t('modals:invoice.supplierPlaceholder')}
                  required
                  disabled={fiscalDisabled}
                />
              </div>
            </div>

            <div className="form-group">
              <label>{t('modals:invoice.description')}</label>
              <textarea
                value={form.description}
                onChange={set('description')}
                placeholder={t('modals:invoice.descriptionPlaceholder')}
                rows={2}
                disabled={fiscalDisabled}
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>{t('modals:invoice.operationalAmount')}</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={form.amount}
                  onChange={set('amount')}
                  placeholder="0.00"
                  required
                  disabled={fiscalDisabled}
                />
              </div>
              <div className="form-group">
                <label>{t('modals:invoice.collectionStatus')}</label>
                <select value={form.status} onChange={set('status')}>
                  {STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {t(`modals:invoice.statuses.${status === 'pendiente' ? 'pending' : status === 'pagada' ? 'paid' : 'overdue'}`)}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label>{t('modals:invoice.dueDate')}</label>
              <input type="datetime-local" value={form.due_date} onChange={set('due_date')} />
            </div>
          </section>

          <section className="form-section">
            <h3 className="form-section-title">{t('modals:invoice.issuerSection')}</h3>
            {seller ? (
              <div className="readonly-block">
                <p>
                  <strong>{t('modals:invoice.nit')}:</strong> {seller.nit}
                  {seller.dv ? `-${seller.dv}` : ''}
                </p>
                {seller.name && (
                  <p>
                    <strong>{t('modals:invoice.businessName')}:</strong> {seller.name}
                  </p>
                )}
              </div>
            ) : (
              <p className="hint-text">
                {t('modals:invoice.missingFiscalProfile')} <code>/api/fiscal/profile</code>.
              </p>
            )}
          </section>

          <section className="form-section">
            <h3 className="form-section-title">{t('modals:invoice.electronicSection')}</h3>
            <div className="form-row">
              <div className="form-group">
                <label>{t('modals:invoice.documentType')}</label>
                <select
                  value={form.document_type}
                  onChange={set('document_type')}
                  disabled={fiscalDisabled}
                >
                  {DOC_TYPES.map((docType) => (
                    <option key={docType} value={docType}>
                      {t(`modals:invoice.documentTypes.${docType === 'factura_venta' ? 'invoiceSale' : docType === 'nota_credito' ? 'creditNote' : 'debitNote'}`)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>{t('modals:invoice.dianStatus')}</label>
                <select value={form.dian_lifecycle_status} onChange={set('dian_lifecycle_status')}>
                  {DIAN_STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {t(`modals:invoice.dianStatuses.${status === 'borrador'
                        ? 'draft'
                        : status === 'lista_para_envio'
                          ? 'readyToSend'
                          : status === 'enviada_proveedor'
                            ? 'sentToProvider'
                            : status === 'aceptada_dian'
                              ? 'accepted'
                              : status === 'rechazada_dian'
                                ? 'rejected'
                                : 'contingency'}`)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>{t('modals:invoice.issueDate')}</label>
                <input
                  type="datetime-local"
                  value={form.issue_date}
                  onChange={set('issue_date')}
                  disabled={fiscalDisabled}
                />
              </div>
              <div className="form-group">
                <label>{t('modals:invoice.currency')}</label>
                <input
                  type="text"
                  value={form.currency}
                  onChange={set('currency')}
                  placeholder="COP"
                  disabled={fiscalDisabled}
                />
              </div>
            </div>
          </section>

          <section className="form-section">
            <h3 className="form-section-title">{t('modals:invoice.buyerSection')}</h3>
            <div className="form-row">
              <div className="form-group">
                <label>{t('modals:invoice.buyerIdType')}</label>
                <input
                  type="text"
                  value={form.buyer_id_type}
                  onChange={set('buyer_id_type')}
                  placeholder={t('modals:invoice.buyerIdTypePlaceholder')}
                  disabled={fiscalDisabled}
                />
              </div>
              <div className="form-group">
                <label>{t('modals:invoice.buyerIdNumber')}</label>
                <input
                  type="text"
                  value={form.buyer_id_number}
                  onChange={set('buyer_id_number')}
                  disabled={fiscalDisabled}
                />
              </div>
            </div>
            <div className="form-group">
              <label>{t('modals:invoice.buyerName')}</label>
              <input
                type="text"
                value={form.buyer_name}
                onChange={set('buyer_name')}
                disabled={fiscalDisabled}
              />
            </div>
          </section>

          <section className="form-section">
            <h3 className="form-section-title">{t('modals:invoice.totalsSection')}</h3>
            <p className="hint-text">
              {t('modals:invoice.totalsHint')}
            </p>
            <div className="form-row">
              <div className="form-group">
                <label>{t('modals:invoice.subtotal')}</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.subtotal}
                  onChange={set('subtotal')}
                  disabled={fiscalDisabled}
                />
              </div>
              <div className="form-group">
                <label>{t('modals:invoice.taxableBase')}</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.taxable_base}
                  onChange={set('taxable_base')}
                  disabled={fiscalDisabled}
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>{t('modals:invoice.vatRate')}</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.iva_rate}
                  onChange={set('iva_rate')}
                  disabled={fiscalDisabled}
                />
              </div>
              <div className="form-group">
                <label>{t('modals:invoice.vatValue')}</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.iva_amount}
                  onChange={set('iva_amount')}
                  disabled={fiscalDisabled}
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>{t('modals:invoice.withholdings')}</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.withholding_amount}
                  onChange={set('withholding_amount')}
                  disabled={fiscalDisabled}
                />
              </div>
              <div className="form-group">
                <label>{t('modals:invoice.documentTotal')}</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.total_document}
                  onChange={set('total_document')}
                  disabled={fiscalDisabled}
                />
              </div>
            </div>
          </section>

          {users.length > 0 && (
            <div className="form-group">
              <label>{t('modals:invoice.assignTo')}</label>
              <div className="user-chips">
                {users.map((u) => (
                  <button
                    key={u.id}
                    type="button"
                    className={`chip-btn ${form.assigned_user_ids.includes(u.id) ? 'selected' : ''}`}
                    onClick={() => toggleUser(u.id)}
                  >
                    {u.username}
                    {form.assigned_user_ids.includes(u.id) && ' ✓'}
                  </button>
                )}
              </div>
            </div>
          )}

          {error && <div className="alert alert-error">{error}</div>}

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              {t('modals:cancel')}
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? t('modals:saving') : isEdit ? t('modals:invoice.save') : t('modals:invoice.create')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
