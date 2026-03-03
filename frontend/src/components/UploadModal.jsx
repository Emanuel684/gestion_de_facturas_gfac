import { useState, useEffect, useRef } from 'react';
import { uploadInvoiceFile } from '../api';
import './UploadModal.css';

const ACCEPTED_EXTENSIONS = '.jpg,.jpeg,.png,.webp,.bmp,.tiff,.tif,.pdf,.docx';
const MAX_SIZE_MB = 10;

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function UploadModal({ onExtracted, onClose }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef(null);

  // Close on Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  // Generate preview for images
  useEffect(() => {
    if (!file) { setPreview(null); return; }
    if (file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file);
      setPreview(url);
      return () => URL.revokeObjectURL(url);
    }
    setPreview(null);
  }, [file]);

  const validateFile = (f) => {
    if (f.size > MAX_SIZE_MB * 1024 * 1024) {
      setError(`El archivo excede el límite de ${MAX_SIZE_MB} MB.`);
      return false;
    }
    const ext = f.name.split('.').pop()?.toLowerCase();
    const validExts = ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'tiff', 'tif', 'pdf', 'docx'];
    if (!validExts.includes(ext)) {
      setError('Formato no soportado. Use: imágenes, PDF o DOCX.');
      return false;
    }
    return true;
  };

  const handleFileSelect = (e) => {
    setError('');
    const f = e.target.files?.[0];
    if (f && validateFile(f)) setFile(f);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    setError('');
    const f = e.dataTransfer.files?.[0];
    if (f && validateFile(f)) setFile(f);
  };

  const handleDragOver = (e) => { e.preventDefault(); setDragActive(true); };
  const handleDragLeave = () => setDragActive(false);

  const handleUpload = async () => {
    if (!file) return;
    setError('');
    setLoading(true);
    try {
      const resp = await uploadInvoiceFile(file);
      onExtracted(resp.data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Error al procesar el archivo.');
    } finally {
      setLoading(false);
    }
  };

  const removeFile = () => { setFile(null); setError(''); };

  const getFileIcon = () => {
    if (!file) return '📄';
    if (file.type.startsWith('image/')) return '🖼️';
    if (file.type === 'application/pdf') return '📕';
    return '📝';
  };

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box upload-modal-box">
        <div className="modal-header">
          <h2>📤 Cargar Documento de Factura</h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">✕</button>
        </div>

        <div className="upload-body">
          <p className="upload-hint">
            Suba una foto, PDF o documento Word (.docx) con los datos de la factura.
            El sistema extraerá automáticamente los campos para crear una nueva factura.
          </p>

          {/* Drop zone */}
          {!file ? (
            <div
              className={`drop-zone ${dragActive ? 'drag-active' : ''}`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => inputRef.current?.click()}
            >
              <input
                ref={inputRef}
                type="file"
                accept={ACCEPTED_EXTENSIONS}
                onChange={handleFileSelect}
                hidden
              />
              <div className="drop-zone-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#0e7490" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <p className="drop-zone-text">
                <strong>Haga clic o arrastre</strong> un archivo aquí
              </p>
              <p className="drop-zone-formats">
                JPEG, PNG, PDF, DOCX — máx. {MAX_SIZE_MB} MB
              </p>
            </div>
          ) : (
            <div className="file-preview">
              {preview ? (
                <img src={preview} alt="Vista previa" className="file-preview-img" />
              ) : (
                <div className="file-preview-icon">{getFileIcon()}</div>
              )}
              <div className="file-info">
                <span className="file-name">{file.name}</span>
                <span className="file-size">{formatFileSize(file.size)}</span>
              </div>
              <button
                className="file-remove"
                onClick={removeFile}
                title="Quitar archivo"
                disabled={loading}
              >
                ✕
              </button>
            </div>
          )}

          {error && <div className="alert alert-error">{error}</div>}

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button
              className="btn btn-primary"
              onClick={handleUpload}
              disabled={!file || loading}
            >
              {loading ? (
                <>
                  <span className="btn-spinner" />
                  Procesando…
                </>
              ) : (
                '📤 Extraer Datos'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
