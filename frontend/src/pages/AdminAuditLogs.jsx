import { useState, useEffect, useCallback } from 'react';
import Sidebar from '../components/Sidebar';
import { apiGetAuditLogs, apiExportAuditLogsUrl } from '../api';

// ── Icons ──────────────────────────────────────────────────────────────────────

function IconDownload() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 14, height: 14 }}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}

function IconActivity() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 24, height: 24 }}>
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  );
}

function IconAlertCircle() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 14, height: 14 }}>
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

// ── Audit Logs Table ───────────────────────────────────────────────────────────

function LogsTable({ logs }) {
  if (logs.length === 0) {
    return (
      <div className="table-empty">
        <div style={{ marginBottom: 8, color: '#cbd5e0' }}>
          <IconActivity />
        </div>
        <div style={{ fontWeight: 600, color: '#718096', marginBottom: 4 }}>No audit logs found</div>
        <div style={{ fontSize: 12, color: '#a0aec0' }}>
          Try adjusting your search or date filters.
        </div>
      </div>
    );
  }

  return (
    <div className="table-wrapper">
      <table aria-label="Audit Logs list">
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Action</th>
            <th>User ID</th>
            <th>IP Address</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.log_id}>
              <td style={{ color: '#718096', fontSize: 13 }}>
                {log.created_at
                  ? new Date(log.created_at).toLocaleString('en-IN', {
                      day: '2-digit', month: 'short', year: 'numeric',
                      hour: '2-digit', minute: '2-digit', second: '2-digit'
                    })
                  : '—'}
              </td>
              <td>
                <span className="badge badge-staff">{log.action}</span>
              </td>
              <td style={{ fontWeight: 500, fontSize: 13 }}>{log.employee_id}</td>
              <td style={{ color: '#718096', fontSize: 13 }}>{log.ip_address || '—'}</td>
              <td style={{ fontSize: 12, color: '#4a5568', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {JSON.stringify(log.details || {})}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminAuditLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [fetchError, setFetchError] = useState('');
  
  // Filters
  const [search, setSearch] = useState('');

  const loadLogs = useCallback(async () => {
    setLoading(true);
    setFetchError('');
    try {
      const data = await apiGetAuditLogs({ search: search.trim() });
      setLogs(data);
    } catch (err) {
      setFetchError(err.message || 'Failed to load audit logs.');
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  async function handleExport() {
    setExporting(true);
    setFetchError('');
    try {
      const objectUrl = await apiExportAuditLogsUrl({ search: search.trim() });
      const a = document.createElement('a');
      a.href = objectUrl;
      a.download = `audit_logs_${new Date().toISOString().replace(/[:.]/g, '-')}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(objectUrl);
    } catch (err) {
      setFetchError(err.message || 'Failed to export audit logs.');
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-content">
        {/* Header */}
        <header className="top-header">
          <div>
            <div className="header-breadcrumb">
              <span className="header-breadcrumb-item">Admin Portal</span>
              <span className="header-breadcrumb-separator">›</span>
              <span className="header-breadcrumb-item">System Logs</span>
            </div>
            <h1 className="header-page-title">Audit Logs</h1>
          </div>
          <div className="header-right">
            <span className="header-badge">
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#16a34a', display: 'inline-block' }} />
              Active Logger
            </span>
          </div>
        </header>

        {/* Body */}
        <main className="page-body">
          {/* Page title + CTA */}
          <div className="page-header" style={{ alignItems: 'flex-end' }}>
            <div className="page-header-text">
              <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4 }}>
                Security & Audit Trail
              </h2>
              <p>Monitor and export immutable system and user operations for compliance.</p>
            </div>
            <div style={{ display: 'flex', gap: 12 }}>
              <input 
                type="text" 
                className="form-input" 
                placeholder="Search action or user..." 
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ width: '250px' }}
              />
              <button
                className="btn btn-secondary"
                onClick={handleExport}
                disabled={exporting || logs.length === 0}
              >
                {exporting ? (
                  <><span className="spinner" /> Exporting…</>
                ) : (
                  <><IconDownload /> Download CSV</>
                )}
              </button>
            </div>
          </div>

          {/* Fetch error */}
          {fetchError && (
            <div className="alert alert-error" role="alert">
              <IconAlertCircle />
              <span>{fetchError}</span>
            </div>
          )}

          {/* Logs Table Card */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">
                <div className="card-icon" style={{ background: '#f0fdf4', color: '#16a34a' }}>
                  <IconActivity />
                </div>
                Recent Activity
              </div>
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  color: 'var(--color-accent)',
                  background: 'var(--color-accent-light)',
                  padding: '3px 12px',
                  borderRadius: 99,
                }}
              >
                {logs.length} {logs.length === 1 ? 'record' : 'records'}
              </span>
            </div>

            <div style={{ minHeight: 400 }}>
              {loading ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 60, gap: 12, color: 'var(--color-text-muted)' }}>
                  <span className="spinner" style={{ borderTopColor: 'var(--color-accent)', borderColor: 'rgba(8,145,178,0.2)' }} />
                  Loading logs…
                </div>
              ) : (
                <LogsTable logs={logs} />
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
