import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  deleteOrganizationUser,
  getOrganization,
  getOrganizationInvoices,
  getOrganizationUsers,
  updateOrganization,
  updateOrganizationUser,
} from '../api';
import Navbar from '../components/Navbar';
import './OrganizationDetailPage.css';

const PLAN_OPTIONS = [
  { value: 'basico', label: 'Basico' },
  { value: 'profesional', label: 'Profesional' },
  { value: 'empresarial', label: 'Empresarial' },
];

const ROLE_OPTIONS = [
  { value: 'administrador', label: 'Administrador' },
  { value: 'contador', label: 'Contador' },
  { value: 'asistente', label: 'Asistente' },
];

const STATUS_OPTIONS = [
  { value: '', label: 'Todos' },
  { value: 'pendiente', label: 'Pendiente' },
  { value: 'pagada', label: 'Pagada' },
  { value: 'vencida', label: 'Vencida' },
];

function fmtMoney(amount) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP' }).format(amount);
}

export default function OrganizationDetailPage() {
  const { organizationId } = useParams();
  const orgId = Number(organizationId);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [org, setOrg] = useState(null);
  const [orgForm, setOrgForm] = useState({ name: '', slug: '', plan_tier: 'basico' });
  const [savingOrg, setSavingOrg] = useState(false);

  const [users, setUsers] = useState([]);
  const [editingUser, setEditingUser] = useState(null);
  const [savingUser, setSavingUser] = useState(false);
  const [deletingUserId, setDeletingUserId] = useState(null);
  const [showInactiveUsers, setShowInactiveUsers] = useState(false);

  const [invoices, setInvoices] = useState([]);
  const [invoiceStatus, setInvoiceStatus] = useState('');
  const [invoiceSupplier, setInvoiceSupplier] = useState('');

  const fetchUsers = useCallback(async () => {
    const r = await getOrganizationUsers(orgId, showInactiveUsers);
    setUsers(r.data || []);
  }, [orgId, showInactiveUsers]);

  const fetchInvoices = useCallback(async () => {
    const params = { limit: 300 };
    if (invoiceStatus) params.status = invoiceStatus;
    if (invoiceSupplier.trim()) params.supplier = invoiceSupplier.trim();
    const r = await getOrganizationInvoices(orgId, params);
    setInvoices(r.data || []);
  }, [orgId, invoiceStatus, invoiceSupplier]);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [orgResp] = await Promise.all([getOrganization(orgId), fetchUsers(), fetchInvoices()]);
      setOrg(orgResp.data);
      setOrgForm({
        name: orgResp.data.name ?? '',
        slug: orgResp.data.slug ?? '',
        plan_tier: orgResp.data.plan_tier ?? 'basico',
      });
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === 'string' ? d : 'No se pudo cargar la organización.');
    } finally {
      setLoading(false);
    }
  }, [orgId, fetchUsers, fetchInvoices]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  useEffect(() => {
    if (!loading) fetchUsers().catch(() => {});
  }, [showInactiveUsers, loading, fetchUsers]);

  useEffect(() => {
    if (!loading) fetchInvoices().catch(() => {});
  }, [invoiceStatus, invoiceSupplier, loading, fetchInvoices]);

  const activeUsers = useMemo(() => users.filter((u) => u.is_active).length, [users]);

  const handleSaveOrg = async (e) => {
    e.preventDefault();
    setSavingOrg(true);
    setError('');
    try {
      const payload = {
        name: orgForm.name.trim(),
        slug: orgForm.slug.trim().toLowerCase(),
        plan_tier: orgForm.plan_tier,
      };
      const r = await updateOrganization(orgId, payload);
      setOrg(r.data);
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === 'string' ? d : 'No se pudo actualizar la organización.');
    } finally {
      setSavingOrg(false);
    }
  };

  const handleSaveUser = async (e) => {
    e.preventDefault();
    if (!editingUser) return;
    setSavingUser(true);
    setError('');
    try {
      const payload = {
        username: editingUser.username.trim(),
        email: editingUser.email.trim(),
        role: editingUser.role,
        is_active: editingUser.is_active,
      };
      if (editingUser.password?.trim()) payload.password = editingUser.password.trim();
      await updateOrganizationUser(orgId, editingUser.id, payload);
      setEditingUser(null);
      await fetchUsers();
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === 'string' ? d : 'No se pudo actualizar el usuario.');
    } finally {
      setSavingUser(false);
    }
  };

  const handleDeleteUser = async (u) => {
    if (!window.confirm(`Deshabilitar usuario ${u.username}?`)) return;
    setDeletingUserId(u.id);
    setError('');
    try {
      await deleteOrganizationUser(orgId, u.id);
      await fetchUsers();
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === 'string' ? d : 'No se pudo eliminar el usuario.');
    } finally {
      setDeletingUserId(null);
    }
  };

  return (
    <>
      <Navbar />
      <main className="org-detail-main">
        <div className="org-detail-header">
          <div>
            <h1>Gestion de organizacion</h1>
            <p>{org ? `${org.name} (${org.slug})` : 'Cargando...'}</p>
          </div>
          <Link className="btn btn-secondary" to="/app/organizaciones">
            Volver
          </Link>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {loading ? (
          <div className="spinner-center"><div className="spinner" /></div>
        ) : (
          <>
            <section className="org-detail-card">
              <h2>Editar organizacion</h2>
              <form className="org-detail-form" onSubmit={handleSaveOrg}>
                <div className="org-detail-grid">
                  <div className="form-group">
                    <label>Nombre</label>
                    <input
                      value={orgForm.name}
                      onChange={(e) => setOrgForm((f) => ({ ...f, name: e.target.value }))}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Slug</label>
                    <input
                      value={orgForm.slug}
                      onChange={(e) => setOrgForm((f) => ({ ...f, slug: e.target.value }))}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Plan</label>
                    <select
                      value={orgForm.plan_tier}
                      onChange={(e) => setOrgForm((f) => ({ ...f, plan_tier: e.target.value }))}
                    >
                      {PLAN_OPTIONS.map((p) => (
                        <option key={p.value} value={p.value}>{p.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <button className="btn btn-primary" type="submit" disabled={savingOrg}>
                  {savingOrg ? 'Guardando...' : 'Guardar cambios'}
                </button>
              </form>
            </section>

            <section className="org-detail-card">
              <div className="org-detail-section-head">
                <h2>Usuarios</h2>
                <label className="org-detail-check">
                  <input
                    type="checkbox"
                    checked={showInactiveUsers}
                    onChange={(e) => setShowInactiveUsers(e.target.checked)}
                  />
                  Incluir inactivos
                </label>
              </div>
              <p className="org-detail-muted">{activeUsers} activos / {users.length} visibles</p>
              <div className="org-users-list">
                {users.map((u) => (
                  <article className="org-user-item" key={u.id}>
                    <div>
                      <strong>{u.username}</strong> <span>{u.email}</span>
                    </div>
                    <div className="org-user-actions">
                      <span className={`org-user-status ${u.is_active ? 'active' : 'inactive'}`}>
                        {u.is_active ? 'Activo' : 'Inactivo'}
                      </span>
                      <span className="org-user-role">{u.role}</span>
                      <button
                        className="btn btn-secondary btn-sm"
                        type="button"
                        onClick={() => setEditingUser({ ...u, password: '' })}
                      >
                        Editar
                      </button>
                      {u.is_active && (
                        <button
                          className="btn btn-secondary btn-sm"
                          type="button"
                          disabled={deletingUserId === u.id}
                          onClick={() => handleDeleteUser(u)}
                        >
                          {deletingUserId === u.id ? 'Eliminando...' : 'Eliminar'}
                        </button>
                      )}
                    </div>
                  </article>
                ))}
                {users.length === 0 && <p className="org-detail-muted">Sin usuarios para esta organización.</p>}
              </div>
            </section>

            <section className="org-detail-card">
              <div className="org-detail-section-head">
                <h2>Facturas y estado</h2>
              </div>
              <div className="org-detail-grid">
                <div className="form-group">
                  <label>Estado</label>
                  <select value={invoiceStatus} onChange={(e) => setInvoiceStatus(e.target.value)}>
                    {STATUS_OPTIONS.map((s) => (
                      <option key={s.value || 'all'} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Proveedor</label>
                  <input
                    value={invoiceSupplier}
                    onChange={(e) => setInvoiceSupplier(e.target.value)}
                    placeholder="Buscar proveedor"
                  />
                </div>
              </div>
              <div className="org-invoices-table-wrap">
                <table className="org-invoices-table">
                  <thead>
                    <tr>
                      <th>Nro</th>
                      <th>Proveedor</th>
                      <th>Estado</th>
                      <th>Monto</th>
                      <th>Vence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoices.map((inv) => (
                      <tr key={inv.id}>
                        <td>{inv.invoice_number}</td>
                        <td>{inv.supplier}</td>
                        <td>{inv.status}</td>
                        <td>{fmtMoney(inv.amount)}</td>
                        <td>{inv.due_date ? new Date(inv.due_date).toLocaleDateString('es-CO') : '—'}</td>
                      </tr>
                    ))}
                    {invoices.length === 0 && (
                      <tr>
                        <td colSpan={5} className="org-detail-muted">Sin facturas con esos filtros.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </main>

      {editingUser && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setEditingUser(null)}>
          <div className="modal-box">
            <div className="modal-header">
              <h2>Editar usuario</h2>
              <button className="modal-close" onClick={() => setEditingUser(null)} aria-label="Cerrar">✕</button>
            </div>
            <form className="modal-form" onSubmit={handleSaveUser}>
              <div className="form-group">
                <label>Usuario</label>
                <input
                  value={editingUser.username}
                  onChange={(e) => setEditingUser((u) => ({ ...u, username: e.target.value }))}
                  required
                />
              </div>
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  value={editingUser.email}
                  onChange={(e) => setEditingUser((u) => ({ ...u, email: e.target.value }))}
                  required
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Rol</label>
                  <select
                    value={editingUser.role}
                    onChange={(e) => setEditingUser((u) => ({ ...u, role: e.target.value }))}
                  >
                    {ROLE_OPTIONS.map((r) => (
                      <option key={r.value} value={r.value}>{r.label}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Activo</label>
                  <select
                    value={editingUser.is_active ? 'yes' : 'no'}
                    onChange={(e) => setEditingUser((u) => ({ ...u, is_active: e.target.value === 'yes' }))}
                  >
                    <option value="yes">Si</option>
                    <option value="no">No</option>
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label>Nueva contraseña (opcional)</label>
                <input
                  type="password"
                  minLength={6}
                  value={editingUser.password}
                  onChange={(e) => setEditingUser((u) => ({ ...u, password: e.target.value }))}
                />
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setEditingUser(null)}>
                  Cancelar
                </button>
                <button type="submit" className="btn btn-primary" disabled={savingUser}>
                  {savingUser ? 'Guardando...' : 'Guardar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
