import { useState, useEffect } from 'react';
import { createInvoice, updateInvoice } from '../api';
import './InvoiceModal.css';

const STATUSES = [
  { value: 'pendiente', label: 'Pendiente' },
  { value: 'pagada',    label: 'Pagada' },
  { value: 'vencida',   label: 'Vencida' },
];

export default function InvoiceModal({ invoice, users, onSuccess, onClose, prefill }) {
  const isEdit = Boolean(invoice);

  const [form, setForm] = useState({
    invoice_number:    invoice?.invoice_number ?? prefill?.invoice_number ?? '',
    supplier:          invoice?.supplier ?? prefill?.supplier ?? '',
    description:       invoice?.description ?? prefill?.description ?? '',
    amount:            invoice?.amount ?? prefill?.amount ?? '',
    status:            invoice?.status ?? 'pendiente',
    due_date:          invoice?.due_date ? invoice.due_date.slice(0, 16) : prefill?.due_date ? prefill.due_date.slice(0, 16) : '',
    assigned_user_ids: invoice?.assigned_users?.map((u) => u.id) ?? [],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');

  // Close on Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const toggleUser = (id) => {
    setForm((f) => ({
      ...f,
      assigned_user_ids: f.assigned_user_ids.includes(id)
        ? f.assigned_user_ids.filter((x) => x !== id)
        : [...f.assigned_user_ids, id],
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    const payload = {
      invoice_number:    form.invoice_number.trim(),
      supplier:          form.supplier.trim(),
      description:       form.description.trim() || null,
      amount:            parseFloat(form.amount),
      status:            form.status,
      due_date:          form.due_date ? new Date(form.due_date).toISOString() : null,
      assigned_user_ids: form.assigned_user_ids,
    };
    try {
      const resp = isEdit
        ? await updateInvoice(invoice.id, payload)
        : await createInvoice(payload);
      await Promise.resolve(onSuccess?.(resp.data));
    } catch (err) {
      setError(err.response?.data?.detail || 'Ocurrió un error.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box">
        <div className="modal-header">
          <h2>{isEdit ? 'Editar Factura' : 'Nueva Factura'}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
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
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Monto (COP) *</label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={form.amount}
                onChange={set('amount')}
                placeholder="0.00"
                required
              />
            </div>
            <div className="form-group">
              <label>Estado</label>
              <select value={form.status} onChange={set('status')}>
                {STATUSES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label>Fecha de Vencimiento</label>
            <input
              type="datetime-local"
              value={form.due_date}
              onChange={set('due_date')}
            />
          </div>

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
