import { useState, useEffect, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { listOrganizations, createOrganization, deleteOrganization } from '../api';
import Navbar from '../components/Navbar';
import './OrganizationsPage.css';

const PLAN_OPTIONS = [
  { value: 'basico', label: 'Básico' },
  { value: 'profesional', label: 'Profesional' },
  { value: 'empresarial', label: 'Empresarial' },
];

export default function OrganizationsPage() {
  const { t } = useTranslation(['organizations']);
  const PAGE_SIZE = 6;
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchName, setSearchName] = useState('');
  const [page, setPage] = useState(0);
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
      setError(t('organizations:loadError'));
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
      setError(typeof d === 'string' ? d : t('organizations:createError'));
    } finally {
      setCreating(false);
    }
  };

  const planLabel = (k) => PLAN_OPTIONS.find((p) => p.value === k)?.label ?? k;

  const filteredOrgs = useMemo(() => {
    const term = searchName.trim().toLowerCase();
    return orgs
      .filter((o) => o.is_active)
      .filter((o) => (term ? o.name.toLowerCase().includes(term) : true));
  }, [orgs, searchName]);

  const totalPages = Math.max(1, Math.ceil(filteredOrgs.length / PAGE_SIZE));
  const paginatedOrgs = useMemo(
    () => filteredOrgs.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE),
    [filteredOrgs, page]
  );

  useEffect(() => {
    setPage(0);
  }, [searchName, orgs.length]);

  useEffect(() => {
    if (page > totalPages - 1) setPage(Math.max(0, totalPages - 1));
  }, [page, totalPages]);

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
      setError(typeof d === 'string' ? d : t('organizations:deleteError'));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <>
      <Navbar />
      <main className="orgs-main">
        <div className="orgs-header">
          <h1>{t('organizations:title')}</h1>
          <p className="orgs-sub">{t('organizations:subtitle')}</p>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <section className="orgs-form-section">
          <h2>{t('organizations:newOrg')}</h2>
          <form className="orgs-form" onSubmit={handleCreate}>
            <div className="orgs-form-row">
              <div className="form-group">
                <label>{t('organizations:orgName')}</label>
                <input value={form.name} onChange={set('name')} required placeholder="Acme SAS" />
              </div>
              <div className="form-group">
                <label>{t('organizations:slug')}</label>
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
                <label>{t('organizations:plan')}</label>
                <select value={form.plan_tier} onChange={set('plan_tier')}>
                  {PLAN_OPTIONS.map((p) => (
                    <option key={p.value} value={p.value}>{p.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <p className="orgs-admin-hint">{t('organizations:adminHint')}</p>
            <div className="orgs-form-row">
              <div className="form-group">
                <label>{t('organizations:adminUser')}</label>
                <input value={form.admin_username} onChange={set('admin_username')} required minLength={3} />
              </div>
              <div className="form-group">
                <label>{t('organizations:email')}</label>
                <input type="email" value={form.admin_email} onChange={set('admin_email')} required />
              </div>
              <div className="form-group">
                <label>{t('organizations:password')}</label>
                <input type="password" value={form.admin_password} onChange={set('admin_password')} required minLength={6} />
              </div>
            </div>
            <button type="submit" className="btn btn-primary" disabled={creating}>
              {creating ? t('organizations:creating') : t('organizations:create')}
            </button>
          </form>
        </section>

        <section className="orgs-list-section">
          <h2>{t('organizations:registered')}</h2>
          <div className="orgs-list-toolbar">
            <input
              className="orgs-search"
              type="text"
              placeholder={t('organizations:search')}
              value={searchName}
              onChange={(e) => setSearchName(e.target.value)}
            />
            <span className="orgs-count">
              {t('organizations:resultCount', { count: filteredOrgs.length })}
            </span>
          </div>
          {loading ? (
            <div className="spinner-center"><div className="spinner" /></div>
          ) : filteredOrgs.length === 0 ? (
            <p className="orgs-empty">
              {searchName.trim() ? 'No se encontraron organizaciones con ese nombre.' : 'Aún no hay organizaciones activas.'}
            </p>
          ) : (
            <>
              <ul className="orgs-list">
                {paginatedOrgs.map((o) => (
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
                      {t('organizations:manage')}
                    </Link>
                    <button
                      type="button"
                      className="btn btn-org-delete"
                      disabled={deletingId === o.id}
                      title="Eliminar organización y todos sus datos"
                      onClick={() => handleDelete(o)}
                    >
                      {deletingId === o.id ? t('organizations:deleting') : t('organizations:delete')}
                    </button>
                  </div>
                </li>
                ))}
              </ul>
              <div className="orgs-pagination">
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  disabled={page === 0}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                >
                  {t('organizations:previous')}
                </button>
                <span className="orgs-page-info">
                  {t('organizations:pageOf', { page: page + 1, total: totalPages })}
                </span>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  disabled={page >= totalPages - 1}
                  onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                >
                  {t('organizations:next')}
                </button>
              </div>
            </>
          )}
        </section>
      </main>
    </>
  );
}
