import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { listOrganizations, exportPlatformReport } from '../api';
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

export default function PlatformReportsPage() {
  const [orgs, setOrgs] = useState([]);
  const [orgId, setOrgId] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    listOrganizations()
      .then((r) => setOrgs(r.data || []))
      .catch(() => setError('No se pudieron cargar las organizaciones.'));
  }, []);

  const buildParams = () => {
    const params = {};
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    if (status) params.status = status;
    return params;
  };

  const download = async (format) => {
    if (!orgId) {
      setError('Seleccione una organización.');
      return;
    }
    setError('');
    setLoading(format);
    try {
      const res = await exportPlatformReport(Number(orgId), format, buildParams());
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
      <main className="reports-main platform-reports">
        <div className="reports-header">
          <h1>Reportes (plataforma)</h1>
          <p className="reports-sub">Exporte facturas de la organización seleccionada en Excel o PDF.</p>
          <Link to="/app/plataforma/dashboard" className="link-reportes">← Volver al dashboard</Link>
        </div>

        <div className="reports-card">
          <div className="reports-filters">
            <label>
              Organización
              <select value={orgId} onChange={(e) => setOrgId(e.target.value)}>
                <option value="">— Seleccione —</option>
                {orgs.map((o) => (
                  <option key={o.id} value={String(o.id)}>{o.name} ({o.slug})</option>
                ))}
              </select>
            </label>
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
            Vista de auditoría: incluye todas las facturas de la organización seleccionada.
          </p>
        </div>
      </main>
    </div>
  );
}
