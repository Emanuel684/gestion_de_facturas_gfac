import { useState, useEffect, useCallback } from 'react';
import { getInvoicesPage, deleteInvoice, getUsers } from '../api';
import { useAuth } from '../context/AuthContext';
import InvoiceModal from '../components/InvoiceModal';
import UploadModal from '../components/UploadModal';
import Navbar from '../components/Navbar';
import './InvoicesPage.css';

const STATUS_LABELS = {
  pendiente: 'Pendiente',
  pagada: 'Pagada',
  vencida: 'Vencida',
};

const STATUS_COLORS = {
  pendiente: 'badge-pendiente',
  pagada: 'badge-pagada',
  vencida: 'badge-vencida',
};

function formatCurrency(amount) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount);
}

export default function InvoicesPage() {  const { user } = useAuth();
  const [invoices, setInvoices] = useState([]);
  const [hasNext, setHasNext] = useState(false);
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 10;
  const [users, setUsers] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [supplierSearch, setSupplierSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingInvoice, setEditingInvoice] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [prefillData, setPrefillData] = useState(null);
  const fetchInvoices = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const resp = await getInvoicesPage({
        page,
        pageSize: PAGE_SIZE,
        status: statusFilter || undefined,
        supplier: supplierSearch.trim() || undefined,
      });
      setInvoices(resp.data.items);
      setHasNext(resp.data.has_next);
    } catch {
      setError('Error al cargar facturas. Intente de nuevo.');
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, supplierSearch]);

  useEffect(() => { fetchInvoices(); }, [fetchInvoices]);

  // Reset to page 0 whenever filters change
  useEffect(() => { setPage(0); }, [statusFilter, supplierSearch]);

  useEffect(() => {
    getUsers().then((r) => setUsers(r.data)).catch(() => {});
  }, []);

  const canDelete = user?.role === 'administrador';
  const canEdit = user?.role !== 'asistente';
  const handleDelete = async (id) => {
    if (!window.confirm('¿Eliminar esta factura?')) return;
    setDeletingId(id);
    try {
      await deleteInvoice(id);
      // Refresh current page so the grid stays consistent
      await fetchInvoices();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al eliminar factura.');
    } finally {
      setDeletingId(null);
    }
  };
  const openCreate = () => { setEditingInvoice(null); setPrefillData(null); setModalOpen(true); };
  const openEdit = (inv) => { setEditingInvoice(inv); setPrefillData(null); setModalOpen(true); };

  const handleUploadExtracted = (data) => {
    setUploadOpen(false);
    const extracted = data.extracted || {};
    setPrefillData(extracted);
    setEditingInvoice(null);
    setModalOpen(true);
  };
  const handleModalSuccess = () => {
    // After create/edit, go to page 0 so the user sees the freshest data
    setPage(0);
    setModalOpen(false);
  };

  const getUserName = (id) => users.find((u) => u.id === id)?.username ?? `#${id}`;

  // Summary stats
  const totalPendiente = invoices
    .filter((inv) => inv.status === 'pendiente')
    .reduce((sum, inv) => sum + parseFloat(inv.amount), 0);
  const totalVencida = invoices
    .filter((inv) => inv.status === 'vencida')
    .reduce((sum, inv) => sum + parseFloat(inv.amount), 0);
  const totalPagada = invoices
    .filter((inv) => inv.status === 'pagada')
    .reduce((sum, inv) => sum + parseFloat(inv.amount), 0);

  return (
    <>
      <Navbar />
      <main className="invoices-main">
        {/* Header row */}
        <div className="invoices-header">
          <div>
            <h2 className="invoices-title">📋 Facturas</h2>
            <p className="invoices-sub">
              {user?.role === 'administrador'
                ? 'Mostrando todas las facturas'
                : user?.role === 'contador'
                ? 'Mostrando todas las facturas'
                : 'Mostrando sus facturas'}
            </p>
          </div>
          <div className="header-actions">
            <button className="btn btn-secondary" onClick={() => setUploadOpen(true)}>📤 Cargar Documento</button>
            <button className="btn btn-primary" onClick={openCreate}>＋ Nueva Factura</button>
          </div>
        </div>

        {/* Summary cards */}
        <div className="summary-row">
          <div className="summary-card summary-pendiente">
            <span className="summary-label">Pendiente</span>
            <span className="summary-value">{formatCurrency(totalPendiente)}</span>
          </div>
          <div className="summary-card summary-vencida">
            <span className="summary-label">Vencida</span>
            <span className="summary-value">{formatCurrency(totalVencida)}</span>
          </div>
          <div className="summary-card summary-pagada">
            <span className="summary-label">Pagada</span>
            <span className="summary-value">{formatCurrency(totalPagada)}</span>
          </div>
        </div>

        {/* Filter bar */}
        <div className="filter-bar">
          <span className="filter-label">Filtrar:</span>
          {['', 'pendiente', 'pagada', 'vencida'].map((s) => (
            <button
              key={s}
              className={`filter-btn ${statusFilter === s ? 'active' : ''}`}
              onClick={() => setStatusFilter(s)}
            >
              {s === '' ? 'Todas' : STATUS_LABELS[s]}
            </button>
          ))}
          <input
            type="text"
            className="supplier-search"
            placeholder="🔍 Buscar proveedor…"
            value={supplierSearch}
            onChange={(e) => setSupplierSearch(e.target.value)}
          />
        </div>

        {/* Content */}
        {error && <div className="alert alert-error">{error}</div>}

        {loading ? (
          <div className="spinner-center"><div className="spinner" /></div>
        ) : invoices.length === 0 ? (
          <div className="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" strokeWidth="1.5">
              <rect x="3" y="3" width="18" height="18" rx="3"/>
              <path d="M7 8h10M7 12h10M7 16h6"/>
            </svg>
            <p>No se encontraron facturas. ¡Cree una!</p>
          </div>
        ) : (
          <div className="invoices-grid">
            {invoices.map((inv) => (
              <div key={inv.id} className="invoice-card">
                <div className="invoice-card-header">
                  <span className={`badge ${STATUS_COLORS[inv.status]}`}>
                    {STATUS_LABELS[inv.status]}
                  </span>
                  <div className="invoice-actions">
                    {canEdit && (
                      <button
                        className="icon-btn edit"
                        title="Editar"
                        onClick={() => openEdit(inv)}
                      >✎</button>
                    )}
                    {canDelete && (
                      <button
                        className="icon-btn delete"
                        title="Eliminar"
                        disabled={deletingId === inv.id}
                        onClick={() => handleDelete(inv.id)}
                      >✕</button>
                    )}
                  </div>
                </div>

                <h3 className="invoice-number">{inv.invoice_number}</h3>
                <p className="invoice-supplier">🏢 {inv.supplier}</p>
                <p className="invoice-amount">{formatCurrency(inv.amount)}</p>

                {inv.description && (
                  <p className="invoice-desc">{inv.description}</p>
                )}

                <div className="invoice-meta">
                  <span title="Registrado por">👤 {getUserName(inv.creator_id)}</span>
                  {inv.due_date && (
                    <span title="Fecha de vencimiento">
                      📅 {new Date(inv.due_date).toLocaleDateString('es-CO')}
                    </span>
                  )}
                </div>

                {inv.assigned_users?.length > 0 && (
                  <div className="invoice-assignees">
                    {inv.assigned_users.map((u) => (
                      <span key={u.id} className="assignee-chip">{u.username}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}          </div>
        )}

        {/* Pagination bar — only shown when there is more than one page or data exists */}
        {!loading && (invoices.length > 0 || page > 0) && (
          <div className="pagination-bar">
            <button
              className="pagination-btn"
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
            >
              ← Anterior
            </button>
            <span className="pagination-info">Página {page + 1}</span>
            <button
              className="pagination-btn"
              disabled={!hasNext}
              onClick={() => setPage((p) => p + 1)}
            >
              Siguiente →
            </button>
          </div>
        )}
      </main>{modalOpen && (
        <InvoiceModal
          invoice={editingInvoice}
          users={users}
          prefill={prefillData}
          onSuccess={handleModalSuccess}
          onClose={() => setModalOpen(false)}
        />
      )}

      {uploadOpen && (
        <UploadModal
          onExtracted={handleUploadExtracted}
          onClose={() => setUploadOpen(false)}
        />
      )}
    </>
  );
}
