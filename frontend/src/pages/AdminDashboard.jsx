import Sidebar from '../components/Sidebar';

// ── Icons ──────────────────────────────────────────────────────────────────────

function IconPatients() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function IconCalendar() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  );
}

function IconQueue() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="8" y1="6" x2="21" y2="6" />
      <line x1="8" y1="12" x2="21" y2="12" />
      <line x1="8" y1="18" x2="21" y2="18" />
      <line x1="3" y1="6" x2="3.01" y2="6" />
      <line x1="3" y1="12" x2="3.01" y2="12" />
      <line x1="3" y1="18" x2="3.01" y2="18" />
    </svg>
  );
}

function IconDoctor() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
      <path d="M16 11l1 5h2" />
      <circle cx="19" cy="17" r="2" />
    </svg>
  );
}

function IconSystem() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14" />
      <path d="M15.54 8.46a5 5 0 0 1 0 7.07M8.46 8.46a5 5 0 0 0 0 7.07" />
    </svg>
  );
}

// ── Dashboard Card ─────────────────────────────────────────────────────────────

const SECTIONS = [
  {
    id: 'patient-overview',
    title: 'Patient Overview',
    icon: <IconPatients />,
    iconBg: '#e0f2fe',
    iconColor: '#0891b2',
    desc: 'Total patients, active cases, and registration stats will appear here.',
  },
  {
    id: 'appointment-overview',
    title: 'Appointment Overview',
    icon: <IconCalendar />,
    iconBg: '#f0fdf4',
    iconColor: '#16a34a',
    desc: "Today's appointments, upcoming schedules, and booking trends will appear here.",
  },
  {
    id: 'queue-overview',
    title: 'Queue Overview',
    icon: <IconQueue />,
    iconBg: '#fef9c3',
    iconColor: '#ca8a04',
    desc: 'Live queue status, token numbers, and average wait times will appear here.',
  },
  {
    id: 'doctor-overview',
    title: 'Doctor Overview',
    icon: <IconDoctor />,
    iconBg: '#fdf2f8',
    iconColor: '#9333ea',
    desc: 'Active doctors, specialisations, and availability slots will appear here.',
  },
  {
    id: 'system-overview',
    title: 'System Overview',
    icon: <IconSystem />,
    iconBg: '#fff1f2',
    iconColor: '#e11d48',
    desc: 'System health, active sessions, and user activity logs will appear here.',
  },
];

function PlaceholderCard({ section }) {
  return (
    <div className="card" id={section.id}>
      <div className="card-header">
        <div className="card-title">
          <div
            className="card-icon"
            style={{ background: section.iconBg, color: section.iconColor }}
            aria-hidden="true"
          >
            {section.icon}
          </div>
          {section.title}
        </div>
        <span
          style={{
            fontSize: 11,
            padding: '3px 10px',
            background: '#f0f4f8',
            color: '#94a3b8',
            borderRadius: 99,
            fontWeight: 600,
            border: '1px solid #e2e8f0',
          }}
        >
          Pending
        </span>
      </div>
      <div className="card-body">
        <div className="placeholder-state">
          <div
            className="placeholder-icon"
            style={{ background: section.iconBg, color: section.iconColor }}
            aria-hidden="true"
          >
            {section.icon}
          </div>
          <div className="placeholder-title">No data available yet</div>
          <div className="placeholder-desc">{section.desc}</div>
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const userInfo = (() => {
    try {
      return JSON.parse(localStorage.getItem('hqms_user') || '{}');
    } catch {
      return {};
    }
  })();

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
              <span className="header-breadcrumb-item">Dashboard</span>
            </div>
            <h1 className="header-page-title">Dashboard</h1>
          </div>
          <div className="header-right">
            <span className="header-badge">
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: '#0891b2',
                  display: 'inline-block',
                }}
              />
              Phase 1 Prototype
            </span>
          </div>
        </header>

        {/* Body */}
        <main className="page-body">
          <div className="prototype-notice" role="note">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 14, height: 14, flexShrink: 0 }}>
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>
              <strong>Prototype Mode:</strong> This dashboard shows the planned layout structure.
              No real data is connected yet — sections are placeholders for future integration.
            </span>
          </div>

          <div className="dashboard-section-title">Overview Sections</div>

          <div className="dashboard-grid">
            {SECTIONS.map((section) => (
              <PlaceholderCard key={section.id} section={section} />
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}
