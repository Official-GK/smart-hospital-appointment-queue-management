import { useNavigate, useLocation } from 'react-router-dom';
import { apiLogout } from '../api';

// ── SVG Icons ──────────────────────────────────────────────────────────────────

function IconDashboard() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
    </svg>
  );
}

function IconUsers() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function IconLogout() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
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

function IconActivity() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  );
}

const NAV_ITEMS = [
  { label: 'Dashboard', path: '/admin/dashboard', icon: <IconDashboard /> },
  { label: 'Create Users', path: '/admin/users', icon: <IconUsers /> },
  { label: 'Audit Logs', path: '/admin/audit-logs', icon: <IconActivity /> },
];

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();

  const userInfo = (() => {
    try {
      return JSON.parse(localStorage.getItem('hqms_user') || '{}');
    } catch {
      return {};
    }
  })();

  const initials = (userInfo.full_name || 'A')
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  async function handleLogout() {
    try {
      await apiLogout();
    } finally {
      localStorage.removeItem('hqms_token');
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_role');
      localStorage.removeItem('hqms_user');
      navigate('/admin/login', { replace: true });
    }
  }

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">
          <IconHospital />
        </div>
        <div className="sidebar-brand-text">
          <span className="sidebar-brand-name">SmartHospital</span>
          <span className="sidebar-brand-tagline">Queue Management</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav" aria-label="Main navigation">
        <span className="sidebar-nav-label">Main Menu</span>

        {NAV_ITEMS.map((item) => (
          <button
            key={item.path}
            id={`nav-${item.label.toLowerCase().replace(/\s/g, '-')}`}
            className={`nav-item${location.pathname === item.path ? ' active' : ''}`}
            onClick={() => navigate(item.path)}
            aria-current={location.pathname === item.path ? 'page' : undefined}
          >
            {item.icon}
            {item.label}
          </button>
        ))}

        <div className="nav-item-divider" />

        <button
          id="nav-logout"
          className="nav-item"
          onClick={handleLogout}
          aria-label="Logout"
        >
          <IconLogout />
          Logout
        </button>
      </nav>

      {/* Logged-in user */}
      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="sidebar-user-avatar" aria-hidden="true">
            {initials}
          </div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">{userInfo.full_name || 'Administrator'}</div>
            <div className="sidebar-user-role">{userInfo.role || 'Admin'}</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
