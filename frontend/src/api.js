/**
 * Axios instance pre-configured for the SGF (Sistema de Gestión de Facturas) API.
 * The Vite dev proxy forwards /api/* → http://localhost:8000,
 * so we use a relative base URL (works in both dev and production builds).
 */
import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

// Attach JWT token from localStorage to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// On 401, clear session and go to login — except failed /auth/login (wrong credentials),
// where a full redirect would reload the page and wipe the form before the user reads the error.
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      const url = err.config?.url ?? '';
      const isLoginFailure = url.includes('/auth/login');
      if (!isLoginFailure) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(err);
  }
);

// ── Auth ─────────────────────────────────────────────────────────────────────
export const login = (organizationSlug, username, password) =>
  api.post('/auth/login', {
    organization_slug: organizationSlug,
    username,
    password,
  });

// ── Invoices ─────────────────────────────────────────────────────────────────
export const getInvoices = (params = {}) =>
  api.get('/invoices', { params });

export const getInvoicesPage = ({ page = 0, pageSize = 10, status, supplier } = {}) => {
  const params = { page, page_size: pageSize };
  if (status) params.status = status;
  if (supplier) params.supplier = supplier;
  return api.get('/invoices', { params });
};

/** Carga todas las facturas que coincidan con filtros (paginación interna, máx. 100 por página en API). */
export async function getInvoicesAll({ status, supplier } = {}) {
  const pageSize = 100;
  const items = [];
  let page = 0;
  let hasNext = true;
  while (hasNext) {
    const resp = await getInvoicesPage({
      page,
      pageSize,
      status: status || undefined,
      supplier: supplier?.trim() || undefined,
    });
    items.push(...resp.data.items);
    hasNext = resp.data.has_next;
    page += 1;
    if (page > 500) break;
  }
  return items;
}

export const getInvoice = (id) => api.get(`/invoices/${id}`);

export const createInvoice = (data) => api.post('/invoices', data);

export const updateInvoice = (id, data) => api.put(`/invoices/${id}`, data);

export const deleteInvoice = (id) => api.delete(`/invoices/${id}`);

export const getOverdueInvoices = () => api.get('/invoices/overdue');

export const uploadInvoiceFile = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/invoices/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

// ── Users ─────────────────────────────────────────────────────────────────────
export const getMe = () => api.get('/users/me');

export const getUsers = () => api.get('/users');

export const createUser = (data) => api.post('/users', data);

export const updateUser = (id, data) => api.put(`/users/${id}`, data);

export const deleteUser = (id) => api.delete(`/users/${id}`);

// ── Organizations (plataforma_admin) ────────────────────────────────────────
export const listOrganizations = () => api.get('/organizations');

export const createOrganization = (data) => api.post('/organizations', data);

export const deleteOrganization = (organizationId) =>
  api.delete(`/organizations/${organizationId}`);

// ── Public signup / mock checkout ────────────────────────────────────────────
export const publicSignup = (data) => api.post('/public/signup', data);
export const getPublicCheckout = (token) => api.get(`/public/checkout/${token}`);
export const completePublicCheckout = (token, outcome) =>
  api.post(`/public/checkout/${token}/complete`, { outcome });

// ── Billing (tenant) ─────────────────────────────────────────────────────────
export const getSubscription = () => api.get('/billing/subscription/me');
export const getPayments = () => api.get('/billing/payments');
export const createCheckout = (planTier) => api.post('/billing/checkout', { plan_tier: planTier });
export const getCheckout = (token) => api.get(`/billing/checkout/${token}`);
export const completeCheckout = (token, outcome) =>
  api.post(`/billing/checkout/${token}/complete`, { outcome });

// ── Fiscal profile (tenant) ─────────────────────────────────────────────────
export const getFiscalProfile = () => api.get('/fiscal/profile');
export const putFiscalProfile = (data) => api.put('/fiscal/profile', data);

// ── Dashboard & reportes (tenant) ───────────────────────────────────────────
export const getTenantDashboard = (params = {}) => api.get('/reports/dashboard', { params });

export const exportTenantReport = (format, params = {}) =>
  api.get('/reports/export', {
    params: { format, ...params },
    responseType: 'blob',
  });

// ── Dashboard & reportes (plataforma) ───────────────────────────────────────
export const getPlatformDashboard = (organizationId, params = {}) =>
  api.get('/platform/dashboard', { params: { organization_id: organizationId, ...params } });

export const getPlatformTopOrganizations = (params = {}) =>
  api.get('/platform/analytics/top-organizations', { params });

export const exportPlatformReport = (organizationId, format, params = {}) =>
  api.get('/platform/reports/export', {
    params: { organization_id: organizationId, format, ...params },
    responseType: 'blob',
  });

// ── Invoice traceability / audit ────────────────────────────────────────────
export const getInvoiceTrace = (id) => api.get(`/invoices/${id}/trace`);

/** @param {string} [opts.format] 'json' (default) | 'xlsx' */
export const getInvoiceAuditPack = (id, opts = {}) => {
  const format = opts.format ?? 'json';
  return api.get(`/invoices/${id}/audit-pack`, {
    params: { format },
    responseType: format === 'xlsx' ? 'blob' : undefined,
  });
};
