/**
 * Axios instance pre-configured for the Task Manager API.
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

// ── Tasks ─────────────────────────────────────────────────────────────────────
export const getTasks = (status) =>
  api.get('/tasks', { params: status ? { status } : {} });

export const getTask = (id) => api.get(`/tasks/${id}`);

export const createTask = (data) => api.post('/tasks', data);

export const updateTask = (id, data) => api.put(`/tasks/${id}`, data);

export const deleteTask = (id) => api.delete(`/tasks/${id}`);

// ── Users ─────────────────────────────────────────────────────────────────────
export const getMe = () => api.get('/users/me');

export const getUsers = () => api.get('/users');
