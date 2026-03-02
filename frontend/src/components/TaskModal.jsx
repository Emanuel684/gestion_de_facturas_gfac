import { useState, useEffect } from 'react';
import { createTask, updateTask } from '../api';
import './TaskModal.css';

const STATUSES = [
  { value: 'todo',        label: 'To Do' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'done',        label: 'Done' },
];

export default function TaskModal({ task, users, onSuccess, onClose }) {
  const isEdit = Boolean(task);

  const [form, setForm] = useState({
    title:             task?.title ?? '',
    description:       task?.description ?? '',
    status:            task?.status ?? 'todo',
    due_date:          task?.due_date ? task.due_date.slice(0, 16) : '',
    assigned_user_ids: task?.assigned_users?.map((u) => u.id) ?? [],
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
      title:             form.title.trim(),
      description:       form.description.trim() || null,
      status:            form.status,
      due_date:          form.due_date ? new Date(form.due_date).toISOString() : null,
      assigned_user_ids: form.assigned_user_ids,
    };
    try {
      const resp = isEdit
        ? await updateTask(task.id, payload)
        : await createTask(payload);
      onSuccess(resp.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box">
        <div className="modal-header">
          <h2>{isEdit ? 'Edit Task' : 'New Task'}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-group">
            <label>Title *</label>
            <input
              type="text"
              value={form.title}
              onChange={set('title')}
              placeholder="Task title"
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label>Description</label>
            <textarea
              value={form.description}
              onChange={set('description')}
              placeholder="Optional description…"
              rows={3}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Status</label>
              <select value={form.status} onChange={set('status')}>
                {STATUSES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Due Date</label>
              <input
                type="datetime-local"
                value={form.due_date}
                onChange={set('due_date')}
              />
            </div>
          </div>

          {users.length > 0 && (
            <div className="form-group">
              <label>Assign to</label>
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
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Saving…' : isEdit ? 'Save Changes' : 'Create Task'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
