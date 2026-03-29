import { useState } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { exportTenantReport } from '../api';
import './ReportsPage.css';

const STATUSES = [
  { value: '', label: 'Todos los estados' },
  { value: 'pendiente', label: 'Pendiente' },
  { value: 'pagada', label: 'Pagada' },
  { value: 'vencida', label: 'Vencida' },
];

function triggerDownload(blob, fallbackName) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fallbackName;
  a.click();
  window.URL.revokeObjectURL(url);
}

export default function ReportsPage() {
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(null);
  const [error, setError] = useState('');

  const buildParams = () => {
    const params = {};
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    if (status) params.status = status;
    return params;
  };

  const download = async (format) => {
    setError('');
    setLoading(format);
    try {
      const res = await exportTenantReport(format, buildParams());
      const blob = res.data;
      const cd = res.headers['content-disposition'] || '';
      const m = /filename="?([^";]+)"?/i.exec(cd);
      const name = m ? m[1].trim() : `facturas.${format === 'xlsx' ? 'xlsx' : 'pdf'}`;
      triggerDownload(blob, name);
    } catch {
      setError('No se pudo generar el archivo. Intente de nuevo.');
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="App">
      <Navbar />
      <main className="reports-main">
        <div className="reports-header">
          <h1>Reportes</h1>
          <p className="reports-sub">Descargue el listado de facturas en Excel o PDF según filtros.</p>
          <Link to="/app/dashboard" className="link-reportes">← Volver al dashboard</Link>
        </div>

        <div className="reports-card">
          <div className="reports-filters">
            <label>
              Desde
              <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            </label>
            <label>
              Hasta
              <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
            </label>
            <label>
              Estado
              <select value={status} onChange={(e) => setStatus(e.target.value)}>
                {STATUSES.map((s) => (
                  <option key={s.value || 'all'} value={s.value}>{s.label}</option>
                ))}
              </select>
            </label>
          </div>

          {error && <div className="form-error">{error}</div>}

          <div className="reports-actions">
            <button
              type="button"
              className="btn btn-primary"
              disabled={loading}
              onClick={() => download('xlsx')}
            >
              {loading === 'xlsx' ? 'Generando…' : 'Descargar Excel'}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={loading}
              onClick={() => download('pdf')}
            >
              {loading === 'pdf' ? 'Generando…' : 'Descargar PDF'}
            </button>
          </div>
          <p className="reports-hint">
            Los datos respetan su rol: los asistentes solo ven facturas creadas o asignadas a ellos.
          </p>
        </div>
      </main>
    </div>
  );
}
