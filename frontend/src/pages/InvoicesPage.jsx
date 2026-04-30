import { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  getInvoicesPage,
  getInvoicesAll,
  deleteInvoice,
  getUsers,
  getOverdueInvoices,
  getDueSoonInvoices,
  updateInvoice,
} from '../api';
import { useAuth } from '../context/AuthContext';
import InvoiceModal from '../components/InvoiceModal';
import InvoiceTraceModal from '../components/InvoiceTraceModal';
import UploadModal from '../components/UploadModal';
import Navbar from '../components/Navbar';
import { localeFromLanguage } from '../utils/locale';
import './InvoicesPage.css';

const STATUS_LABELS = { pendiente: 'pending', pagada: 'paid', vencida: 'overdue' };

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

function formatCurrency(amount, locale) {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount);
}

function formatDate(value, locale, t) {
  if (!value) return t('invoices:noDate');
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return t('invoices:noDate');
  return new Intl.DateTimeFormat(locale, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(d);
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
  const { t, i18n } = useTranslation(['invoices']);
  const locale = localeFromLanguage(i18n.resolvedLanguage);
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
  const [dueSoonInvoices, setDueSoonInvoices] = useState([]);
  const [dueSoonDismissed, setDueSoonDismissed] = useState(false);
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
      setError(t('invoices:loadingError'));
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
      setError(t('invoices:loadingError'));
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

  const fetchDueSoon = useCallback(async () => {
    try {
      const resp = await getDueSoonInvoices(7);
      setDueSoonInvoices(resp.data);
      if (resp.data.length > 0) setDueSoonDismissed(false);
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
    fetchDueSoon();
  }, [fetchOverdue, fetchDueSoon, invoices, allInvoices]);

  useEffect(() => {
    setPage(0);
  }, [statusFilter, supplierSearch]);

  useEffect(() => {
    getUsers().then((r) => setUsers(r.data)).catch(() => {});
  }, []);

  const canDelete = user?.role === 'administrador';
  const canEdit = user?.role !== 'asistente';

  const handleDelete = async (id) => {
    if (!window.confirm(t('invoices:deleteConfirm'))) return;
    setDeletingId(id);
    try {
      await deleteInvoice(id);
      if (isGridView) await fetchInvoices();
      else await fetchAllForBoard();
      await fetchOverdue();
      await fetchDueSoon();
    } catch (err) {
      alert(err.response?.data?.detail || t('invoices:deleteError'));
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
      await fetchDueSoon();
    } catch {
      setError(t('invoices:loadingError'));
    } finally {
      setLoading(false);
    }
  }, [isGridView, statusFilter, supplierSearch, fetchOverdue, fetchDueSoon]);

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
      alert(t('invoices:updateStatusDenied'));
      setDragInvoiceId(null);
      return;
    }
    setStatusUpdatingId(id);
    try {
      await updateInvoice(id, { status: targetStatus });
      setAllInvoices((prev) => prev.map((i) => (i.id === id ? { ...i, status: targetStatus } : i)));
      await fetchOverdue();
      await fetchDueSoon();
    } catch (err) {
      alert(err.response?.data?.detail || t('invoices:updateStatusError'));
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
        title={t('invoices:traceTitle')}
        onClick={() => setTraceInvoice({ id: inv.id, invoice_number: inv.invoice_number })}
      >
        📜
      </button>
      {canEdit && (
        <button type="button" className="icon-btn edit" title={t('invoices:edit')} onClick={() => openEdit(inv)}>
          ✎
        </button>
      )}
      {canDelete && (
        <button
          type="button"
          className="icon-btn delete"
          title={t('invoices:delete')}
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
            <h2 className="invoices-title">📋 {t('invoices:title')}</h2>
            <p className="invoices-sub">
              {user?.organization?.name && <span className="invoices-org">{user.organization.name} · </span>}
              {user?.role === 'asistente' ? t('invoices:showingMine') : t('invoices:showingAllOrg')}
            </p>
          </div>
          <div className="header-actions">
            <button type="button" className="btn btn-secondary" onClick={() => setUploadOpen(true)}>
              📤 {t('invoices:uploadDocument')}
            </button>
            <button type="button" className="btn btn-primary" onClick={openCreate}>
              ＋ {t('invoices:newInvoice')}
            </button>
          </div>
        </div>

        {overdueInvoices.length > 0 && !overdueDismissed && (
          <div className="overdue-banner">
            <span className="overdue-banner-icon">⚠️</span>
            <div className="overdue-banner-body">
              <strong>
                {overdueInvoices.length === 1
                  ? t('invoices:overdueBannerOne')
                  : t('invoices:overdueBannerMany', { count: overdueInvoices.length })}
              </strong>
              <span className="overdue-banner-list">
                {overdueInvoices.slice(0, 5).map((inv) => (
                  <span key={inv.id} className="overdue-chip">
                    {inv.invoice_number} — {inv.supplier}
                  </span>
                ))}
                {overdueInvoices.length > 5 && (
                  <span className="overdue-chip overdue-chip-more">{t('invoices:moreCount', { count: overdueInvoices.length - 5 })}</span>
                )}
              </span>
            </div>
            <button type="button" className="overdue-banner-dismiss" title={t('invoices:discard')} onClick={() => setOverdueDismissed(true)}>
              ✕
            </button>
          </div>
        )}

        {dueSoonInvoices.length > 0 && !dueSoonDismissed && (
          <div className="due-soon-banner">
            <span className="due-soon-banner-icon">🗓️</span>
            <div className="due-soon-banner-body">
              <strong>
                {dueSoonInvoices.length === 1
                  ? t('invoices:dueSoonBannerOne')
                  : t('invoices:dueSoonBannerMany', { count: dueSoonInvoices.length })}
              </strong>
              <span className="due-soon-banner-list">
                {dueSoonInvoices.slice(0, 5).map((inv) => (
                  <span key={inv.id} className="due-soon-chip">
                    {inv.invoice_number} — {inv.supplier} ({formatDate(inv.due_date, locale, t)})
                  </span>
                ))}
                {dueSoonInvoices.length > 5 && (
                  <span className="due-soon-chip due-soon-chip-more">{t('invoices:moreCount', { count: dueSoonInvoices.length - 5 })}</span>
                )}
              </span>
            </div>
            <button type="button" className="due-soon-banner-dismiss" title={t('invoices:discard')} onClick={() => setDueSoonDismissed(true)}>
              ✕
            </button>
          </div>
        )}

        <div className="summary-row">
          <div className="summary-card summary-pendiente">
            <span className="summary-label">{t('invoices:pending')}</span>
            <span className="summary-value">{formatCurrency(totalPendiente, locale)}</span>
          </div>
          <div className="summary-card summary-vencida">
            <span className="summary-label">{t('invoices:overdue')}</span>
            <span className="summary-value">{formatCurrency(totalVencida, locale)}</span>
          </div>
          <div className="summary-card summary-pagada">
            <span className="summary-label">{t('invoices:paid')}</span>
            <span className="summary-value">{formatCurrency(totalPagada, locale)}</span>
          </div>
        </div>

        <div className="filter-bar filter-bar-with-view">
          <div className="filter-bar-left">
            <span className="filter-label">{t('invoices:filter')}</span>
            {['', 'pendiente', 'pagada', 'vencida'].map((s) => (
              <button
                key={s}
                type="button"
                className={`filter-btn ${statusFilter === s ? 'active' : ''}`}
                onClick={() => setStatusFilter(s)}
              >
                {s === '' ? t('invoices:all') : t(`invoices:${STATUS_LABELS[s]}`)}
              </button>
            ))}
            <input
              type="text"
              className="supplier-search"
              placeholder={`🔍 ${t('invoices:searchSupplier')}`}
              value={supplierSearch}
              onChange={(e) => setSupplierSearch(e.target.value)}
            />
          </div>
          <div className="view-mode-toggle" role="group" aria-label={t('invoices:view')}>
            <span className="view-mode-label">{t('invoices:view')}</span>
            <button
              type="button"
              className={`view-mode-btn ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => persistView('grid')}
              title={t('invoices:cards')}
            >
              {t('invoices:cards')}
            </button>
            <button
              type="button"
              className={`view-mode-btn ${viewMode === 'kanban' ? 'active' : ''}`}
              onClick={() => persistView('kanban')}
              title={t('invoices:kanban')}
            >
              {t('invoices:kanban')}
            </button>
            <button
              type="button"
              className={`view-mode-btn ${viewMode === 'compact' ? 'active' : ''}`}
              onClick={() => persistView('compact')}
              title={t('invoices:list')}
            >
              {t('invoices:list')}
            </button>
          </div>
        </div>

        {viewMode === 'kanban' && (
          <p className="view-hint">
            {t('invoices:kanbanHint')}
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
            <p>{t('invoices:empty')}</p>
          </div>
        ) : viewMode === 'grid' ? (
          <div className="invoices-grid">
            {invoices.map((inv) => (
              <div
                key={inv.id}
                className={`invoice-card${inv.status === 'vencida' ? ' invoice-card-overdue' : ''}`}
              >
                <div className="invoice-card-header">
                <span className={`badge ${STATUS_COLORS[inv.status]}`}>{t(`invoices:${STATUS_LABELS[inv.status]}`)}</span>
                  {renderInvoiceActions(inv)}
                </div>

                <h3 className="invoice-number">{inv.invoice_number}</h3>
                {inv.dian_lifecycle_status && (
                  <p className="invoice-dian-line">
                    <span className="badge badge-dian">{DIAN_LABELS[inv.dian_lifecycle_status] || inv.dian_lifecycle_status}</span>
                  </p>
                )}
                <p className="invoice-supplier">🏢 {inv.supplier}</p>
                <p className="invoice-amount">{formatCurrency(inv.amount, locale)}</p>

                {inv.description && <p className="invoice-desc">{inv.description}</p>}

                <div className="invoice-meta">
                  <span title={t('invoices:registeredBy')}>👤 {getUserName(inv.creator_id)}</span>
                  {inv.due_date && (
                    <span title={t('invoices:dueDateLabel')}>📅 {new Date(inv.due_date).toLocaleDateString(locale)}</span>
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
                  <span className={`badge ${STATUS_COLORS[st]}`}>{t(`invoices:${STATUS_LABELS[st]}`)}</span>
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
                        <p className="kanban-card-amount">{formatCurrency(inv.amount, locale)}</p>
                        {inv.due_date && (
                          <p className="kanban-card-due">📅 {new Date(inv.due_date).toLocaleDateString(locale)}</p>
                        )}
                      </div>
                    ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <ul className="invoice-compact-list" aria-label={t('invoices:list')}>
            {sortedCompact.map((inv) => (
              <li
                key={inv.id}
                className={`invoice-compact-row${inv.status === 'vencida' ? ' invoice-compact-row-overdue' : ''}`}
              >
                <span className={`invoice-compact-dot invoice-compact-dot-${inv.status}`} title={t(`invoices:${STATUS_LABELS[inv.status]}`)} />
                <div className="invoice-compact-main">
                  <span className="invoice-compact-num">{inv.invoice_number}</span>
                  <span className="invoice-compact-sep">·</span>
                  <span className="invoice-compact-supplier">{inv.supplier}</span>
                </div>
                <span className="invoice-compact-amount">{formatCurrency(inv.amount, locale)}</span>
                {inv.due_date && (
                  <span className="invoice-compact-date">{new Date(inv.due_date).toLocaleDateString(locale)}</span>
                )}
                {renderInvoiceActions(inv, { compact: true })}
              </li>
            ))}
          </ul>
        )}

        {!loading && isGridView && (invoices.length > 0 || page > 0) && (
          <div className="pagination-bar">
            <button type="button" className="pagination-btn" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
              ← {t('invoices:previous')}
            </button>
            <span className="pagination-info">{t('invoices:page')} {page + 1}</span>
            <button type="button" className="pagination-btn" disabled={!hasNext} onClick={() => setPage((p) => p + 1)}>
              {t('invoices:next')} →
            </button>
          </div>
        )}

        {!loading && !isGridView && allInvoices.length > 0 && (
          <p className="list-footnote">
            {t('invoices:listSummary', { count: allInvoices.length })}
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
