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

// On 401, clear token so the app redirects to login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ── Auth ─────────────────────────────────────────────────────────────────────
export const login = (username, password) => {
  const form = new URLSearchParams();
  form.append('username', username);
  form.append('password', password);
  return api.post('/auth/login', form);
};

// ── Invoices ─────────────────────────────────────────────────────────────────
export const getInvoices = (params = {}) =>
  api.get('/invoices', { params });

export const getInvoicesPage = ({ page = 0, pageSize = 10, status, supplier } = {}) => {
  const params = { page, page_size: pageSize };
  if (status) params.status = status;
  if (supplier) params.supplier = supplier;
  return api.get('/invoices', { params });
};

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
