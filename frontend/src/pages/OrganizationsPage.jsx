import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { listOrganizations, createOrganization, deleteOrganization } from '../api';
import Navbar from '../components/Navbar';
import './OrganizationsPage.css';

const PLAN_OPTIONS = [
  { value: 'basico', label: 'Básico' },
  { value: 'profesional', label: 'Profesional' },
  { value: 'empresarial', label: 'Empresarial' },
];

export default function OrganizationsPage() {
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [form, setForm] = useState({
    name: '',
    slug: '',
    plan_tier: 'basico',
    admin_username: '',
    admin_email: '',
    admin_password: '',
  });

  const fetchOrgs = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const r = await listOrganizations();
      setOrgs(r.data);
    } catch {
      setError('No se pudieron cargar las organizaciones.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchOrgs(); }, [fetchOrgs]);

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const handleCreate = async (e) => {
    e.preventDefault();
    setError('');
    setCreating(true);
    try {
      await createOrganization({
        name: form.name.trim(),
        slug: form.slug.trim().toLowerCase(),
        plan_tier: form.plan_tier,
        admin_username: form.admin_username.trim(),
        admin_email: form.admin_email.trim(),
        admin_password: form.admin_password,
      });
      setForm({
        name: '',
        slug: '',
        plan_tier: 'basico',
        admin_username: '',
        admin_email: '',
        admin_password: '',
      });
      await fetchOrgs();
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === 'string' ? d : 'Error al crear la organización.');
    } finally {
      setCreating(false);
    }
  };

  const planLabel = (k) => PLAN_OPTIONS.find((p) => p.value === k)?.label ?? k;

  const handleDelete = async (o) => {
    const msg =
      `¿Eliminar permanentemente la organización «${o.name}» (${o.slug})?\n\n` +
      'Se borrarán todos los datos: usuarios (activos e inactivos), facturas, eventos, suscripciones, pagos y perfiles fiscales. Esta acción no se puede deshacer.';
    if (!window.confirm(msg)) return;
    setError('');
    setDeletingId(o.id);
    try {
      await deleteOrganization(o.id);
      await fetchOrgs();
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === 'string' ? d : 'No se pudo eliminar la organización.');
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <>
      <Navbar />
      <main className="orgs-main">
        <div className="orgs-header">
          <h1>Organizaciones</h1>
          <p className="orgs-sub">Cree espacios aislados para cada cliente. Cada uno tendrá sus usuarios y facturas.</p>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <section className="orgs-form-section">
          <h2>Nueva organización</h2>
          <form className="orgs-form" onSubmit={handleCreate}>
            <div className="orgs-form-row">
              <div className="form-group">
                <label>Nombre de la empresa</label>
                <input value={form.name} onChange={set('name')} required placeholder="Ej. Acme SAS" />
              </div>
              <div className="form-group">
                <label>Slug (URL / login)</label>
                <input
                  value={form.slug}
                  onChange={set('slug')}
                  required
                  placeholder="ej. acme-corp"
                  pattern="[a-z0-9]+(-[a-z0-9]+)*"
                  title="minúsculas, números y guiones"
                />
              </div>
              <div className="form-group">
                <label>Plan</label>
                <select value={form.plan_tier} onChange={set('plan_tier')}>
                  {PLAN_OPTIONS.map((p) => (
                    <option key={p.value} value={p.value}>{p.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <p className="orgs-admin-hint">Primer administrador de la organización (acceso a facturas y usuarios de ese cliente):</p>
            <div className="orgs-form-row">
              <div className="form-group">
                <label>Usuario admin</label>
                <input value={form.admin_username} onChange={set('admin_username')} required minLength={3} />
              </div>
              <div className="form-group">
                <label>Email</label>
                <input type="email" value={form.admin_email} onChange={set('admin_email')} required />
              </div>
              <div className="form-group">
                <label>Contraseña</label>
                <input type="password" value={form.admin_password} onChange={set('admin_password')} required minLength={6} />
              </div>
            </div>
            <button type="submit" className="btn btn-primary" disabled={creating}>
              {creating ? 'Creando…' : 'Crear organización'}
            </button>
          </form>
        </section>

        <section className="orgs-list-section">
          <h2>Organizaciones registradas</h2>
          {loading ? (
            <div className="spinner-center"><div className="spinner" /></div>
          ) : orgs.length === 0 ? (
            <p className="orgs-empty">Aún no hay organizaciones cliente.</p>
          ) : (
            <ul className="orgs-list">
              {orgs.map((o) => (
                <li key={o.id} className="orgs-card">
                  <div className="orgs-card-main">
                    <strong>{o.name}</strong>
                    <span className="orgs-slug">slug: <code>{o.slug}</code></span>
                  </div>
                  <div className="orgs-card-actions">
                    <span className="orgs-plan">{planLabel(o.plan_tier)}</span>
                    <Link
                      className="btn btn-secondary btn-sm"
                      to={`/app/organizaciones/${o.id}`}
                      title="Editar organización y administrar sus usuarios/facturas"
                    >
                      Gestionar
                    </Link>
                    <button
                      type="button"
                      className="btn btn-org-delete"
                      disabled={deletingId === o.id}
                      title="Eliminar organización y todos sus datos"
                      onClick={() => handleDelete(o)}
                    >
                      {deletingId === o.id ? 'Eliminando…' : 'Eliminar'}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </>
  );
}
