import { useState, useEffect, useMemo } from 'react';
import { createInvoice, updateInvoice, getFiscalProfile } from '../api';
import './InvoiceModal.css';

const STATUSES = [
  { value: 'pendiente', label: 'Pendiente' },
  { value: 'pagada', label: 'Pagada' },
  { value: 'vencida', label: 'Vencida' },
];

const DOC_TYPES = [
  { value: 'factura_venta', label: 'Factura de venta' },
  { value: 'nota_credito', label: 'Nota crédito' },
  { value: 'nota_debito', label: 'Nota débito' },
];

const DIAN_STATUSES = [
  { value: 'borrador', label: 'Borrador' },
  { value: 'lista_para_envio', label: 'Lista para envío' },
  { value: 'enviada_proveedor', label: 'Enviada a proveedor/OSE' },
  { value: 'aceptada_dian', label: 'Aceptada DIAN' },
  { value: 'rechazada_dian', label: 'Rechazada DIAN' },
  { value: 'contingencia', label: 'Contingencia' },
];

function defaultIssueLocal() {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

function formatApiError(err) {
  const d = err.response?.data?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join('; ');
  return 'Ocurrió un error.';
}

function numOrEmpty(v) {
  if (v === '' || v === null || v === undefined) return '';
  const n = parseFloat(v);
  return Number.isFinite(n) ? String(n) : '';
}

export default function InvoiceModal({ invoice, users, onSuccess, onClose, prefill }) {
  const isEdit = Boolean(invoice);
  const docLocked = isEdit && invoice?.document_locked;

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
      document_type: invoice?.document_type ?? 'factura_venta',
      issue_date: invoice?.issue_date ? invoice.issue_date.slice(0, 16) : defaultIssueLocal(),
      currency: invoice?.currency ?? 'COP',
      buyer_id_type: invoice?.buyer_id_type ?? '',
      buyer_id_number: invoice?.buyer_id_number ?? '',
      buyer_name: invoice?.buyer_name ?? '',
      subtotal: invoice?.subtotal != null ? String(invoice.subtotal) : '',
      taxable_base: invoice?.taxable_base != null ? String(invoice.taxable_base) : '',
      iva_rate: invoice?.iva_rate != null ? String(invoice.iva_rate) : '0.19',
      iva_amount: invoice?.iva_amount != null ? String(invoice.iva_amount) : '',
      withholding_amount: invoice?.withholding_amount != null ? String(invoice.withholding_amount) : '',
      total_document: invoice?.total_document != null ? String(invoice.total_document) : '',
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
        ? await updateInvoice(invoice.id, payload)
        : await createInvoice(payload);
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
          <h2>{isEdit ? 'Editar Factura' : 'Nueva Factura'}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">
            ✕
          </button>
        </div>

        {docLocked && (
          <div className="modal-banner">
            Documento fiscal bloqueado: solo puede ajustar cobranza (estado interno, vencimiento,
            asignaciones) y el estado DIAN.
          </div>
        )}

        <form onSubmit={handleSubmit} className="modal-form">
          <section className="form-section">
            <h3 className="form-section-title">Datos generales</h3>
            <div className="form-row">
              <div className="form-group">
                <label>N° Factura *</label>
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
                <label>Proveedor *</label>
                <input
                  type="text"
                  value={form.supplier}
                  onChange={set('supplier')}
                  placeholder="Nombre del proveedor"
                  required
                  disabled={fiscalDisabled}
                />
              </div>
            </div>

            <div className="form-group">
              <label>Descripción</label>
              <textarea
                value={form.description}
                onChange={set('description')}
                placeholder="Descripción opcional…"
                rows={2}
                disabled={fiscalDisabled}
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Monto operativo (COP) *</label>
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
                <label>Estado cobranza</label>
                <select value={form.status} onChange={set('status')}>
                  {STATUSES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label>Fecha de Vencimiento</label>
              <input type="datetime-local" value={form.due_date} onChange={set('due_date')} />
            </div>
          </section>

          <section className="form-section">
            <h3 className="form-section-title">Emisor (perfil fiscal)</h3>
            {seller ? (
              <div className="readonly-block">
                <p>
                  <strong>NIT:</strong> {seller.nit}
                  {seller.dv ? `-${seller.dv}` : ''}
                </p>
                {seller.name && (
                  <p>
                    <strong>Razón social:</strong> {seller.name}
                  </p>
                )}
              </div>
            ) : (
              <p className="hint-text">
                Sin perfil fiscal configurado. Un administrador puede completarlo en la sección de
                facturación o vía API <code>/api/fiscal/profile</code>.
              </p>
            )}
          </section>

          <section className="form-section">
            <h3 className="form-section-title">Documento electrónico (preparación DIAN)</h3>
            <div className="form-row">
              <div className="form-group">
                <label>Tipo de documento</label>
                <select
                  value={form.document_type}
                  onChange={set('document_type')}
                  disabled={fiscalDisabled}
                >
                  {DOC_TYPES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Estado ciclo DIAN</label>
                <select value={form.dian_lifecycle_status} onChange={set('dian_lifecycle_status')}>
                  {DIAN_STATUSES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Fecha de emisión</label>
                <input
                  type="datetime-local"
                  value={form.issue_date}
                  onChange={set('issue_date')}
                  disabled={fiscalDisabled}
                />
              </div>
              <div className="form-group">
                <label>Moneda</label>
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
            <h3 className="form-section-title">Adquirente</h3>
            <div className="form-row">
              <div className="form-group">
                <label>Tipo ID</label>
                <input
                  type="text"
                  value={form.buyer_id_type}
                  onChange={set('buyer_id_type')}
                  placeholder="NIT, CC, CE…"
                  disabled={fiscalDisabled}
                />
              </div>
              <div className="form-group">
                <label>Número ID</label>
                <input
                  type="text"
                  value={form.buyer_id_number}
                  onChange={set('buyer_id_number')}
                  disabled={fiscalDisabled}
                />
              </div>
            </div>
            <div className="form-group">
              <label>Nombre adquirente</label>
              <input
                type="text"
                value={form.buyer_name}
                onChange={set('buyer_name')}
                disabled={fiscalDisabled}
              />
            </div>
          </section>

          <section className="form-section">
            <h3 className="form-section-title">Totales e IVA</h3>
            <p className="hint-text">
              Opcional: si no completa, el servidor deriva montos a partir del monto operativo. Use
              IVA 0,19 para el estándar Colombia.
            </p>
            <div className="form-row">
              <div className="form-group">
                <label>Subtotal</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.subtotal}
                  onChange={set('subtotal')}
                  disabled={fiscalDisabled}
                />
              </div>
              <div className="form-group">
                <label>Base gravable</label>
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
                <label>Alícuota IVA</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.iva_rate}
                  onChange={set('iva_rate')}
                  disabled={fiscalDisabled}
                />
              </div>
              <div className="form-group">
                <label>Valor IVA</label>
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
                <label>Retenciones</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.withholding_amount}
                  onChange={set('withholding_amount')}
                  disabled={fiscalDisabled}
                />
              </div>
              <div className="form-group">
                <label>Total documento</label>
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
              <label>Asignar a</label>
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
                ))}
              </div>
            </div>
          )}

          {error && <div className="alert alert-error">{error}</div>}

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Guardando…' : isEdit ? 'Guardar Cambios' : 'Crear Factura'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
