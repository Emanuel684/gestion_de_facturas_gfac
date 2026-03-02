import { useState, useEffect, useCallback } from 'react';
import { getTasks, deleteTask, getUsers } from '../api';
import { useAuth } from '../context/AuthContext';
import TaskModal from '../components/TaskModal';
import Navbar from '../components/Navbar';
import './TasksPage.css';

const STATUS_LABELS = {
  todo: 'To Do',
  in_progress: 'In Progress',
  done: 'Done',
};

const STATUS_COLORS = {
  todo: 'badge-todo',
  in_progress: 'badge-progress',
  done: 'badge-done',
};

export default function TasksPage() {
  const { user } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [users, setUsers] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const resp = await getTasks(statusFilter || undefined);
      setTasks(resp.data);
    } catch {
      setError('Failed to load tasks. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { fetchTasks(); }, [fetchTasks]);

  useEffect(() => {
    getUsers().then((r) => setUsers(r.data)).catch(() => {});
  }, []);

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this task?')) return;
    setDeletingId(id);
    try {
      await deleteTask(id);
      setTasks((prev) => prev.filter((t) => t.id !== id));
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete task.');
    } finally {
      setDeletingId(null);
    }
  };

  const openCreate = () => { setEditingTask(null); setModalOpen(true); };
  const openEdit = (task) => { setEditingTask(task); setModalOpen(true); };

  const handleModalSuccess = (savedTask) => {
    setTasks((prev) => {
      const idx = prev.findIndex((t) => t.id === savedTask.id);
      if (idx >= 0) {
        const updated = [...prev];
        updated[idx] = savedTask;
        return updated;
      }
      return [savedTask, ...prev];
    });
    setModalOpen(false);
  };

  const getUserName = (id) => users.find((u) => u.id === id)?.username ?? `#${id}`;

  return (
    <>
      <Navbar />
      <main className="tasks-main">
        {/* Header row */}
        <div className="tasks-header">
          <div>
            <h2 className="tasks-title">Tasks</h2>
            <p className="tasks-sub">
              {user?.role === 'owner' ? 'Showing all tasks' : 'Showing your tasks'}
            </p>
          </div>
          <button className="btn btn-primary" onClick={openCreate}>＋ New Task</button>
        </div>

        {/* Filter bar */}
        <div className="filter-bar">
          <span className="filter-label">Filter by status:</span>
          {['', 'todo', 'in_progress', 'done'].map((s) => (
            <button
              key={s}
              className={`filter-btn ${statusFilter === s ? 'active' : ''}`}
              onClick={() => setStatusFilter(s)}
            >
              {s === '' ? 'All' : STATUS_LABELS[s]}
            </button>
          ))}
        </div>

        {/* Content */}
        {error && <div className="alert alert-error">{error}</div>}

        {loading ? (
          <div className="spinner-center"><div className="spinner" /></div>
        ) : tasks.length === 0 ? (
          <div className="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" strokeWidth="1.5">
              <rect x="3" y="3" width="18" height="18" rx="3"/>
              <path d="M9 12l2 2 4-4"/>
            </svg>
            <p>No tasks found. Create one!</p>
          </div>
        ) : (
          <div className="tasks-grid">
            {tasks.map((task) => (
              <div key={task.id} className="task-card">
                <div className="task-card-header">
                  <span className={`badge ${STATUS_COLORS[task.status]}`}>
                    {STATUS_LABELS[task.status]}
                  </span>
                  <div className="task-actions">
                    <button
                      className="icon-btn edit"
                      title="Edit"
                      onClick={() => openEdit(task)}
                    >✎</button>
                    <button
                      className="icon-btn delete"
                      title="Delete"
                      disabled={deletingId === task.id}
                      onClick={() => handleDelete(task.id)}
                    >✕</button>
                  </div>
                </div>

                <h3 className="task-title">{task.title}</h3>
                {task.description && (
                  <p className="task-desc">{task.description}</p>
                )}

                <div className="task-meta">
                  <span title="Creator">👤 {getUserName(task.creator_id)}</span>
                  {task.due_date && (
                    <span title="Due date">
                      📅 {new Date(task.due_date).toLocaleDateString()}
                    </span>
                  )}
                </div>

                {task.assigned_users?.length > 0 && (
                  <div className="task-assignees">
                    {task.assigned_users.map((u) => (
                      <span key={u.id} className="assignee-chip">{u.username}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>

      {modalOpen && (
        <TaskModal
          task={editingTask}
          users={users}
          onSuccess={handleModalSuccess}
          onClose={() => setModalOpen(false)}
        />
      )}
    </>
  );
}
