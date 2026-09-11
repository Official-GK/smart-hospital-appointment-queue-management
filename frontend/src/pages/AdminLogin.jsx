import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiLogin } from '../api';

// ── Icons ──────────────────────────────────────────────────────────────────────

function IconCross() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 14, height: 14 }}>
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  );
}

function IconHospital() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <path d="M12 2v8M8 13h8M12 13v6" />
    </svg>
  );
}

function IconShield() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 16, height: 16 }}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

// ── Component ──────────────────────────────────────────────────────────────────

export default function Login() {
  const navigate = useNavigate();

  const [userId, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');

    if (!userId.trim()) {
      setError('User ID is required.');
      return;
    }
    if (!password) {
      setError('Password is required.');
      return;
    }

    setLoading(true);
    try {
      const data = await apiLogin(userId.trim(), password);
      localStorage.setItem('hqms_token', data.token);
      localStorage.setItem('access_token', data.token);
      localStorage.setItem('user_role', data.role);
      localStorage.setItem(
        'hqms_user',
        JSON.stringify({ user_id: data.user_id, full_name: data.full_name, role: data.role }),
      );
      navigate('/admin/dashboard', { replace: true });
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      {/* Left — Branding */}
      <div className="login-left">
        <div className="login-branding">
          <div className="login-brand-logo">
            <IconHospital />
          </div>
          <h1 className="login-brand-name">
            Smart<span>Hospital</span>
            <br />QMS
          </h1>
          <p className="login-brand-desc">
            A unified platform for managing hospital appointments,
            patient queues, and clinical operations — all in one place.
          </p>

          <div className="login-features">
            {[
              'Streamlined patient appointment management',
              'Real-time queue tracking and optimisation',
              'Multi-role staff access control',
              'Comprehensive reporting &amp; analytics',
            ].map((text) => (
              <div key={text} className="login-feature-item">
                <div className="login-feature-dot" />
                <span dangerouslySetInnerHTML={{ __html: text }} />
              </div>
            ))}
          </div>

          <div style={{ marginTop: 48, fontSize: 11, color: 'rgba(168,192,216,0.5)', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 20 }}>
            Smart Hospital Queue Management System &bull; Phase 1 Prototype
          </div>
        </div>
      </div>

      {/* Right — Login Form */}
      <div className="login-right">
        <div className="login-card">
          <div className="login-card-header">
            <h2 className="login-card-title">Admin Sign In</h2>
            <p className="login-card-subtitle">
              Enter your credentials to access the admin portal.
            </p>
          </div>

          {error && (
            <div className="alert alert-error" role="alert">
              <IconCross />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="form-group">
              <label className="form-label" htmlFor="login-userid">
                User ID <span className="required">*</span>
              </label>
              <input
                id="login-userid"
                type="text"
                className={`form-input${error ? ' error' : ''}`}
                placeholder="Enter your User ID"
                value={userId}
                onChange={(e) => { setUserId(e.target.value); setError(''); }}
                autoComplete="username"
                autoFocus
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="login-password">
                Password <span className="required">*</span>
              </label>
              <input
                id="login-password"
                type="password"
                className={`form-input${error ? ' error' : ''}`}
                placeholder="Enter your password"
                value={password}
                onChange={(e) => { setPassword(e.target.value); setError(''); }}
                autoComplete="current-password"
              />
            </div>

            <div style={{ marginTop: 8 }}>
              <button
                id="login-submit"
                type="submit"
                className="btn btn-primary btn-full btn-lg"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="spinner" />
                    Signing In…
                  </>
                ) : (
                  'Sign In'
                )}
              </button>
            </div>
          </form>

          <div
            style={{
              marginTop: 32,
              padding: '14px 16px',
              background: '#f8fafc',
              borderRadius: 8,
              border: '1px solid #e2e8f0',
              display: 'flex',
              alignItems: 'flex-start',
              gap: 10,
            }}
          >
            <IconShield style={{ flexShrink: 0, marginTop: 1, color: '#718096' }} />
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#4a5568', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>
                Admin Credentials
              </div>
              <div style={{ fontSize: 12, color: '#718096', lineHeight: 1.8 }}>
                User ID: <code style={{ background: '#e2e8f0', padding: '1px 5px', borderRadius: 3, color: '#1a202c', fontFamily: 'Courier New, monospace' }}>ADMIN-001</code>
                <br />
                Password: <code style={{ background: '#e2e8f0', padding: '1px 5px', borderRadius: 3, color: '#1a202c', fontFamily: 'Courier New, monospace' }}>admin123</code>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
