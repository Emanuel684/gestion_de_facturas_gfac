import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  getInvoicesPage,
  getInvoicesAll,
  deleteInvoice,
  getUsers,
  getOverdueInvoices,
  updateInvoice,
} from '../api';
import { useAuth } from '../context/AuthContext';
import InvoiceModal from '../components/InvoiceModal';
import InvoiceTraceModal from '../components/InvoiceTraceModal';
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

/** Columnas del tablero Kanban (orden visual izquierda → derecha) */
const KANBAN_STATUSES = ['pendiente', 'vencida', 'pagada'];

const DIAN_LABELS = {
  borrador: 'Borrador',
  lista_para_envio: 'Lista envío',
  enviada_proveedor: 'Enviada',
  aceptada_dian: 'Aceptada DIAN',
  rechazada_dian: 'Rechazada',
  contingencia: 'Contingencia',
};

const VIEW_STORAGE_KEY = 'sgf-invoices-view';

function formatCurrency(amount) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount);
}

function readStoredView() {
  try {
    const v = localStorage.getItem(VIEW_STORAGE_KEY);
    if (v === 'grid' || v === 'kanban' || v === 'compact') return v;
  } catch {
    /* ignore */
  }
  return 'grid';
}

/** Alineado con reglas del backend: contador solo si creó o está asignado. */
function canModifyInvoice(user, inv) {
  if (!user) return false;
  if (user.role === 'administrador') return true;
  if (user.role === 'asistente') return false;
  if (user.role === 'contador') {
    const assigned = inv.assigned_users?.some((u) => u.id === user.id);
    return inv.creator_id === user.id || assigned;
  }
  return true;
}

export default function InvoicesPage() {
  const { user } = useAuth();
  const [viewMode, setViewMode] = useState(readStoredView);

  const [invoices, setInvoices] = useState([]);
  const [allInvoices, setAllInvoices] = useState([]);
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
  const [overdueInvoices, setOverdueInvoices] = useState([]);
  const [overdueDismissed, setOverdueDismissed] = useState(false);
  const [traceInvoice, setTraceInvoice] = useState(null);
  const [dragInvoiceId, setDragInvoiceId] = useState(null);
  const [statusUpdatingId, setStatusUpdatingId] = useState(null);

  const isGridView = viewMode === 'grid';
  const displayInvoices = isGridView ? invoices : allInvoices;

  const persistView = (mode) => {
    setViewMode(mode);
    try {
      localStorage.setItem(VIEW_STORAGE_KEY, mode);
    } catch {
      /* ignore */
    }
  };

  // ── Data fetching: vista tarjetas (paginada) ───────────────────────────────

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

  // ── Data fetching: Kanban y lista compacta (todas las páginas) ─────────────

  const fetchAllForBoard = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const items = await getInvoicesAll({
        status: statusFilter || undefined,
        supplier: supplierSearch.trim() || undefined,
      });
      setAllInvoices(items);
    } catch {
      setError('Error al cargar facturas. Intente de nuevo.');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, supplierSearch]);

  const fetchOverdue = useCallback(async () => {
    try {
      const resp = await getOverdueInvoices();
      setOverdueInvoices(resp.data);
      if (resp.data.length > 0) setOverdueDismissed(false);
    } catch {
      /* non-critical */
    }
  }, []);

  useEffect(() => {
    if (isGridView) fetchInvoices();
  }, [isGridView, fetchInvoices]);

  useEffect(() => {
    if (!isGridView) fetchAllForBoard();
  }, [isGridView, fetchAllForBoard]);

  useEffect(() => {
    fetchOverdue();
  }, [fetchOverdue, invoices, allInvoices]);

  useEffect(() => {
    setPage(0);
  }, [statusFilter, supplierSearch]);

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
      if (isGridView) await fetchInvoices();
      else await fetchAllForBoard();
      await fetchOverdue();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al eliminar factura.');
    } finally {
      setDeletingId(null);
    }
  };

  const openCreate = () => {
    setEditingInvoice(null);
    setPrefillData(null);
    setModalOpen(true);
  };
  const openEdit = (inv) => {
    setEditingInvoice(inv);
    setPrefillData(null);
    setModalOpen(true);
  };

  const handleUploadExtracted = (data) => {
    setUploadOpen(false);
    setPrefillData(data.extracted || {});
    setEditingInvoice(null);
    setModalOpen(true);
  };

  const handleModalSuccess = useCallback(async () => {
    setEditingInvoice(null);
    setPrefillData(null);
    setModalOpen(false);
    setPage(0);
    setLoading(true);
    setError('');
    try {
      if (isGridView) {
        const resp = await getInvoicesPage({
          page: 0,
          pageSize: PAGE_SIZE,
          status: statusFilter || undefined,
          supplier: supplierSearch.trim() || undefined,
        });
        setInvoices(resp.data.items);
        setHasNext(resp.data.has_next);
      } else {
        const items = await getInvoicesAll({
          status: statusFilter || undefined,
          supplier: supplierSearch.trim() || undefined,
        });
        setAllInvoices(items);
      }
      await fetchOverdue();
    } catch {
      setError('Error al cargar facturas. Intente de nuevo.');
    } finally {
      setLoading(false);
    }
  }, [isGridView, statusFilter, supplierSearch, fetchOverdue]);

  const getUserName = (id) => users.find((u) => u.id === id)?.username ?? `#${id}`;

  const handleDropOnColumn = async (targetStatus, e) => {
    e.preventDefault();
    e.stopPropagation();
    const raw = e.dataTransfer?.getData('application/x-sgf-invoice') || e.dataTransfer?.getData('text/plain');
    const id = raw ? parseInt(raw, 10) : NaN;
    if (!id || Number.isNaN(id)) return;
    const inv = allInvoices.find((i) => i.id === id);
    if (!inv || inv.status === targetStatus) {
      setDragInvoiceId(null);
      return;
    }
    if (!canModifyInvoice(user, inv)) {
      alert('No tiene permiso para cambiar el estado de esta factura.');
      setDragInvoiceId(null);
      return;
    }
    setStatusUpdatingId(id);
    try {
      await updateInvoice(id, { status: targetStatus });
      setAllInvoices((prev) => prev.map((i) => (i.id === id ? { ...i, status: targetStatus } : i)));
      await fetchOverdue();
    } catch (err) {
      alert(err.response?.data?.detail || 'No se pudo actualizar el estado.');
    } finally {
      setStatusUpdatingId(null);
      setDragInvoiceId(null);
    }
  };

  const onDragStartInvoice = (e, inv) => {
    if (!canModifyInvoice(user, inv)) {
      e.preventDefault();
      return;
    }
    setDragInvoiceId(inv.id);
    e.dataTransfer.setData('application/x-sgf-invoice', String(inv.id));
    e.dataTransfer.setData('text/plain', String(inv.id));
    e.dataTransfer.effectAllowed = 'move';
  };

  const totalPendiente = useMemo(
    () =>
      displayInvoices.filter((inv) => inv.status === 'pendiente').reduce((sum, inv) => sum + parseFloat(inv.amount), 0),
    [displayInvoices]
  );
  const totalVencida = useMemo(
    () =>
      displayInvoices.filter((inv) => inv.status === 'vencida').reduce((sum, inv) => sum + parseFloat(inv.amount), 0),
    [displayInvoices]
  );
  const totalPagada = useMemo(
    () =>
      displayInvoices.filter((inv) => inv.status === 'pagada').reduce((sum, inv) => sum + parseFloat(inv.amount), 0),
    [displayInvoices]
  );

  const sortedCompact = useMemo(() => {
    const order = { vencida: 0, pendiente: 1, pagada: 2 };
    return [...allInvoices].sort((a, b) => {
      const oa = order[a.status] ?? 3;
      const ob = order[b.status] ?? 3;
      if (oa !== ob) return oa - ob;
      return (a.invoice_number || '').localeCompare(b.invoice_number || '');
    });
  }, [allInvoices]);

  const renderInvoiceActions = (inv, { compact = false } = {}) => (
    <div className={compact ? 'invoice-actions invoice-actions-compact' : 'invoice-actions'}>
      <button
        type="button"
        className="icon-btn trace"
        title="Trazabilidad y auditoría"
        onClick={() => setTraceInvoice({ id: inv.id, invoice_number: inv.invoice_number })}
      >
        📜
      </button>
      {canEdit && (
        <button type="button" className="icon-btn edit" title="Editar" onClick={() => openEdit(inv)}>
          ✎
        </button>
      )}
      {canDelete && (
        <button
          type="button"
          className="icon-btn delete"
          title="Eliminar"
          disabled={deletingId === inv.id}
          onClick={() => handleDelete(inv.id)}
        >
          ✕
        </button>
      )}
    </div>
  );

  return (
    <>
      <Navbar />
      <main className="invoices-main">
        <div className="invoices-header">
          <div>
            <h2 className="invoices-title">📋 Facturas</h2>
            <p className="invoices-sub">
              {user?.organization?.name && <span className="invoices-org">{user.organization.name} · </span>}
              {user?.role === 'asistente' ? 'Mostrando sus facturas' : 'Mostrando todas las facturas de la organización'}
            </p>
          </div>
          <div className="header-actions">
            <button type="button" className="btn btn-secondary" onClick={() => setUploadOpen(true)}>
              📤 Cargar Documento
            </button>
            <button type="button" className="btn btn-primary" onClick={openCreate}>
              ＋ Nueva Factura
            </button>
          </div>
        </div>

        {overdueInvoices.length > 0 && !overdueDismissed && (
          <div className="overdue-banner">
            <span className="overdue-banner-icon">⚠️</span>
            <div className="overdue-banner-body">
              <strong>
                {overdueInvoices.length === 1
                  ? '1 factura vencida sin pagar'
                  : `${overdueInvoices.length} facturas vencidas sin pagar`}
              </strong>
              <span className="overdue-banner-list">
                {overdueInvoices.slice(0, 5).map((inv) => (
                  <span key={inv.id} className="overdue-chip">
                    {inv.invoice_number} — {inv.supplier}
                  </span>
                ))}
                {overdueInvoices.length > 5 && (
                  <span className="overdue-chip overdue-chip-more">+{overdueInvoices.length - 5} más</span>
                )}
              </span>
            </div>
            <button type="button" className="overdue-banner-dismiss" title="Descartar" onClick={() => setOverdueDismissed(true)}>
              ✕
            </button>
          </div>
        )}

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

        <div className="filter-bar filter-bar-with-view">
          <div className="filter-bar-left">
            <span className="filter-label">Filtrar:</span>
            {['', 'pendiente', 'pagada', 'vencida'].map((s) => (
              <button
                key={s}
                type="button"
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
          <div className="view-mode-toggle" role="group" aria-label="Forma de ver facturas">
            <span className="view-mode-label">Vista:</span>
            <button
              type="button"
              className={`view-mode-btn ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => persistView('grid')}
              title="Tarjetas (actual)"
            >
              Tarjetas
            </button>
            <button
              type="button"
              className={`view-mode-btn ${viewMode === 'kanban' ? 'active' : ''}`}
              onClick={() => persistView('kanban')}
              title="Tablero Kanban"
            >
              Kanban
            </button>
            <button
              type="button"
              className={`view-mode-btn ${viewMode === 'compact' ? 'active' : ''}`}
              onClick={() => persistView('compact')}
              title="Lista compacta"
            >
              Lista
            </button>
          </div>
        </div>

        {viewMode === 'kanban' && (
          <p className="view-hint">
            Arrastre las facturas entre columnas para cambiar el estado de cobro. Los asistentes no pueden modificar
            facturas.
          </p>
        )}

        {error && <div className="alert alert-error">{error}</div>}

        {loading ? (
          <div className="spinner-center">
            <div className="spinner" />
          </div>
        ) : displayInvoices.length === 0 ? (
          <div className="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" strokeWidth="1.5">
              <rect x="3" y="3" width="18" height="18" rx="3" />
              <path d="M7 8h10M7 12h10M7 16h6" />
            </svg>
            <p>No se encontraron facturas. ¡Cree una!</p>
          </div>
        ) : viewMode === 'grid' ? (
          <div className="invoices-grid">
            {invoices.map((inv) => (
              <div
                key={inv.id}
                className={`invoice-card${inv.status === 'vencida' ? ' invoice-card-overdue' : ''}`}
              >
                <div className="invoice-card-header">
                  <span className={`badge ${STATUS_COLORS[inv.status]}`}>{STATUS_LABELS[inv.status]}</span>
                  {renderInvoiceActions(inv)}
                </div>

                <h3 className="invoice-number">{inv.invoice_number}</h3>
                {inv.dian_lifecycle_status && (
                  <p className="invoice-dian-line">
                    <span className="badge badge-dian">{DIAN_LABELS[inv.dian_lifecycle_status] || inv.dian_lifecycle_status}</span>
                  </p>
                )}
                <p className="invoice-supplier">🏢 {inv.supplier}</p>
                <p className="invoice-amount">{formatCurrency(inv.amount)}</p>

                {inv.description && <p className="invoice-desc">{inv.description}</p>}

                <div className="invoice-meta">
                  <span title="Registrado por">👤 {getUserName(inv.creator_id)}</span>
                  {inv.due_date && (
                    <span title="Fecha de vencimiento">📅 {new Date(inv.due_date).toLocaleDateString('es-CO')}</span>
                  )}
                </div>

                {inv.assigned_users?.length > 0 && (
                  <div className="invoice-assignees">
                    {inv.assigned_users.map((u) => (
                      <span key={u.id} className="assignee-chip">
                        {u.username}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : viewMode === 'kanban' ? (
          <div className="kanban-board">
            {KANBAN_STATUSES.map((st) => (
              <div
                key={st}
                className={`kanban-column kanban-column-${st}`}
                onDragOver={(e) => {
                  e.preventDefault();
                  e.dataTransfer.dropEffect = 'move';
                }}
                onDrop={(e) => handleDropOnColumn(st, e)}
              >
                <div className="kanban-column-header">
                  <span className={`badge ${STATUS_COLORS[st]}`}>{STATUS_LABELS[st]}</span>
                  <span className="kanban-count">{allInvoices.filter((i) => i.status === st).length}</span>
                </div>
                <div className="kanban-column-body">
                  {allInvoices
                    .filter((i) => i.status === st)
                    .map((inv) => (
                      <div
                        key={inv.id}
                        draggable={canModifyInvoice(user, inv)}
                        onDragStart={(e) => onDragStartInvoice(e, inv)}
                        onDragEnd={() => setDragInvoiceId(null)}
                        className={`kanban-card${dragInvoiceId === inv.id ? ' kanban-card-dragging' : ''}${
                          !canModifyInvoice(user, inv) ? ' kanban-card-no-drag' : ''
                        }${statusUpdatingId === inv.id ? ' kanban-card-updating' : ''}`}
                      >
                        <div className="kanban-card-top">
                          <span className="kanban-card-number">{inv.invoice_number}</span>
                          {renderInvoiceActions(inv, { compact: true })}
                        </div>
                        <p className="kanban-card-supplier">{inv.supplier}</p>
                        <p className="kanban-card-amount">{formatCurrency(inv.amount)}</p>
                        {inv.due_date && (
                          <p className="kanban-card-due">📅 {new Date(inv.due_date).toLocaleDateString('es-CO')}</p>
                        )}
                      </div>
                    ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <ul className="invoice-compact-list" aria-label="Lista compacta de facturas">
            {sortedCompact.map((inv) => (
              <li
                key={inv.id}
                className={`invoice-compact-row${inv.status === 'vencida' ? ' invoice-compact-row-overdue' : ''}`}
              >
                <span className={`invoice-compact-dot invoice-compact-dot-${inv.status}`} title={STATUS_LABELS[inv.status]} />
                <div className="invoice-compact-main">
                  <span className="invoice-compact-num">{inv.invoice_number}</span>
                  <span className="invoice-compact-sep">·</span>
                  <span className="invoice-compact-supplier">{inv.supplier}</span>
                </div>
                <span className="invoice-compact-amount">{formatCurrency(inv.amount)}</span>
                {inv.due_date && (
                  <span className="invoice-compact-date">{new Date(inv.due_date).toLocaleDateString('es-CO')}</span>
                )}
                {renderInvoiceActions(inv, { compact: true })}
              </li>
            ))}
          </ul>
        )}

        {!loading && isGridView && (invoices.length > 0 || page > 0) && (
          <div className="pagination-bar">
            <button type="button" className="pagination-btn" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
              ← Anterior
            </button>
            <span className="pagination-info">Página {page + 1}</span>
            <button type="button" className="pagination-btn" disabled={!hasNext} onClick={() => setPage((p) => p + 1)}>
              Siguiente →
            </button>
          </div>
        )}

        {!loading && !isGridView && allInvoices.length > 0 && (
          <p className="list-footnote">
            Mostrando {allInvoices.length} factura{allInvoices.length !== 1 ? 's' : ''} (filtros actuales).
          </p>
        )}
      </main>

      {modalOpen && (
        <InvoiceModal
          key={`${editingInvoice?.id ?? 'new'}-${prefillData ? 'p' : 'n'}`}
          invoice={editingInvoice}
          users={users}
          prefill={prefillData}
          onSuccess={handleModalSuccess}
          onClose={() => setModalOpen(false)}
        />
      )}

      {traceInvoice && (
        <InvoiceTraceModal
          invoiceId={traceInvoice.id}
          invoiceNumber={traceInvoice.invoice_number}
          onClose={() => setTraceInvoice(null)}
        />
      )}

      {uploadOpen && <UploadModal onExtracted={handleUploadExtracted} onClose={() => setUploadOpen(false)} />}
    </>
  );
}
