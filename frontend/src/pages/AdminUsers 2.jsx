import { useState, useEffect, useCallback } from 'react';
import Sidebar from '../components/Sidebar';
import { apiGetUsers, apiCreateUser, apiDeleteUser } from '../api';

// ── Icons ──────────────────────────────────────────────────────────────────────

function IconPlus() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function IconX() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 14, height: 14 }}>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function IconTrash() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 14, height: 14 }}>
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14H6L5 6" />
      <path d="M10 11v6M14 11v6" />
      <path d="M9 6V4h6v2" />
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

function IconCheck() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 14, height: 14 }}>
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function IconUsers() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 24, height: 24 }}>
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

// ── Role Badge ─────────────────────────────────────────────────────────────────

function RoleBadge({ role }) {
  const cls =
    role === 'Admin'
      ? 'badge badge-admin'
      : role === 'Management'
      ? 'badge badge-management'
      : 'badge badge-staff';
  return <span className={cls}>{role}</span>;
}

// ── Create User Modal ──────────────────────────────────────────────────────────

const EMPTY_FORM = {
  user_id: '',
  full_name: '',
  password: '',
  confirm_password: '',
  role: '',
};

function CreateUserModal({ onClose, onCreated }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState('');

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
    setErrors((e) => ({ ...e, [field]: '' }));
    setServerError('');
  }

  function validate() {
    const errs = {};
    if (!form.user_id.trim()) errs.user_id = 'User ID is required.';
    if (!form.full_name.trim()) errs.full_name = 'Full Name is required.';
    if (!form.password) errs.password = 'Password is required.';
    if (!form.confirm_password) {
      errs.confirm_password = 'Please confirm the password.';
    } else if (form.password !== form.confirm_password) {
      errs.confirm_password = 'Passwords do not match.';
    }
    if (!form.role) errs.role = 'Please select a role.';
    return errs;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length > 0) {
      setErrors(errs);
      return;
    }

    setSubmitting(true);
    try {
      const created = await apiCreateUser({
        user_id: form.user_id.trim(),
        full_name: form.full_name.trim(),
        password: form.password,
        role: form.role,
      });
      onCreated(created);
    } catch (err) {
      setServerError(err.message || 'Failed to create user.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className="modal">
        <div className="modal-header">
          <h2 className="modal-title" id="modal-title">Create New User</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close modal">
            <IconX />
          </button>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          <div className="modal-body">
            {serverError && (
              <div className="alert alert-error" role="alert">
                <IconAlertCircle />
                <span>{serverError}</span>
              </div>
            )}

            {/* User ID */}
            <div className="form-group">
              <label className="form-label" htmlFor="create-userid">
                User ID <span className="required">*</span>
              </label>
              <input
                id="create-userid"
                type="text"
                className={`form-input${errors.user_id ? ' error' : ''}`}
                placeholder="e.g. john.doe"
                value={form.user_id}
                onChange={(e) => set('user_id', e.target.value)}
                autoFocus
              />
              {errors.user_id && (
                <div className="form-error"><IconAlertCircle />{errors.user_id}</div>
              )}
            </div>

            {/* Full Name */}
            <div className="form-group">
              <label className="form-label" htmlFor="create-fullname">
                Full Name <span className="required">*</span>
              </label>
              <input
                id="create-fullname"
                type="text"
                className={`form-input${errors.full_name ? ' error' : ''}`}
                placeholder="e.g. John Doe"
                value={form.full_name}
                onChange={(e) => set('full_name', e.target.value)}
              />
              {errors.full_name && (
                <div className="form-error"><IconAlertCircle />{errors.full_name}</div>
              )}
            </div>

            {/* Password */}
            <div className="form-group">
              <label className="form-label" htmlFor="create-password">
                Password <span className="required">*</span>
              </label>
              <input
                id="create-password"
                type="password"
                className={`form-input${errors.password ? ' error' : ''}`}
                placeholder="Create a password"
                value={form.password}
                onChange={(e) => set('password', e.target.value)}
                autoComplete="new-password"
              />
              {errors.password && (
                <div className="form-error"><IconAlertCircle />{errors.password}</div>
              )}
            </div>

            {/* Confirm Password */}
            <div className="form-group">
              <label className="form-label" htmlFor="create-confirm-password">
                Confirm Password <span className="required">*</span>
              </label>
              <input
                id="create-confirm-password"
                type="password"
                className={`form-input${errors.confirm_password ? ' error' : ''}`}
                placeholder="Re-enter password"
                value={form.confirm_password}
                onChange={(e) => set('confirm_password', e.target.value)}
                autoComplete="new-password"
              />
              {errors.confirm_password && (
                <div className="form-error"><IconAlertCircle />{errors.confirm_password}</div>
              )}
            </div>

            {/* Role */}
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label" htmlFor="create-role">
                Role <span className="required">*</span>
              </label>
              <select
                id="create-role"
                className={`form-select${errors.role ? ' error' : ''}`}
                value={form.role}
                onChange={(e) => set('role', e.target.value)}
              >
                <option value="">-- Select a role --</option>
                <option value="Staff">Staff</option>
                <option value="Management">Management</option>
                <option value="Admin">Admin</option>
              </select>
              {errors.role && (
                <div className="form-error"><IconAlertCircle />{errors.role}</div>
              )}
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button
              id="create-user-submit"
              type="submit"
              className="btn btn-primary"
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <span className="spinner" />
                  Creating…
                </>
              ) : (
                <>
                  <IconPlus />
                  Create User
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Users Table ────────────────────────────────────────────────────────────────

function UsersTable({ users, onDelete }) {
  const [deletingId, setDeletingId] = useState(null);

  async function handleDelete(userId) {
    if (!window.confirm(`Delete user "${userId}"? This cannot be undone.`)) return;
    setDeletingId(userId);
    try {
      await onDelete(userId);
    } finally {
      setDeletingId(null);
    }
  }

  if (users.length === 0) {
    return (
      <div className="table-empty">
        <div style={{ marginBottom: 8, color: '#cbd5e0' }}>
          <IconUsers />
        </div>
        <div style={{ fontWeight: 600, color: '#718096', marginBottom: 4 }}>No users created yet</div>
        <div style={{ fontSize: 12, color: '#a0aec0' }}>
          Click "+ Create User" above to add the first user.
        </div>
      </div>
    );
  }

  return (
    <div className="table-wrapper">
      <table aria-label="Users list">
        <thead>
          <tr>
            <th>User ID</th>
            <th>Full Name</th>
            <th>Role</th>
            <th>Created</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.user_id}>
              <td>
                <span className="user-id-cell">{user.user_id}</span>
              </td>
              <td style={{ fontWeight: 500 }}>{user.full_name}</td>
              <td>
                <RoleBadge role={user.role} />
              </td>
              <td style={{ color: '#718096', fontSize: 12 }}>
                {user.created_at
                  ? new Date(user.created_at).toLocaleDateString('en-IN', {
                      day: '2-digit',
                      month: 'short',
                      year: 'numeric',
                    })
                  : '—'}
              </td>
              <td>
                <button
                  id={`delete-user-${user.user_id}`}
                  className="btn btn-danger"
                  onClick={() => handleDelete(user.user_id)}
                  disabled={deletingId === user.user_id}
                  aria-label={`Delete user ${user.user_id}`}
                >
                  {deletingId === user.user_id ? (
                    <span className="spinner" style={{ borderTopColor: 'var(--color-error)' }} />
                  ) : (
                    <IconTrash />
                  )}
                  {deletingId === user.user_id ? 'Deleting…' : 'Delete'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Users() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [fetchError, setFetchError] = useState('');

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setFetchError('');
    try {
      const data = await apiGetUsers();
      setUsers(data);
    } catch (err) {
      setFetchError(err.message || 'Failed to load users.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  function handleCreated(newUser) {
    setUsers((prev) => [...prev, newUser]);
    setShowModal(false);
    setSuccessMsg(`User "${newUser.user_id}" was created successfully.`);
    setTimeout(() => setSuccessMsg(''), 5000);
  }

  async function handleDelete(userId) {
    await apiDeleteUser(userId);
    setUsers((prev) => prev.filter((u) => u.user_id !== userId));
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
              <span className="header-breadcrumb-item">User Management</span>
            </div>
            <h1 className="header-page-title">Create Users</h1>
          </div>
          <div className="header-right">
            <span className="header-badge">
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#0891b2', display: 'inline-block' }} />
              Phase 1 Prototype
            </span>
          </div>
        </header>

        {/* Body */}
        <main className="page-body">
          {/* Page title + CTA */}
          <div className="page-header">
            <div className="page-header-text">
              <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4 }}>
                User Management
              </h2>
              <p>Create and manage admin portal user accounts.</p>
            </div>
            <button
              id="open-create-user-modal"
              className="btn btn-primary"
              onClick={() => { setShowModal(true); setSuccessMsg(''); }}
            >
              <IconPlus />
              Create User
            </button>
          </div>

          {/* Success alert */}
          {successMsg && (
            <div className="alert alert-success" role="status">
              <IconCheck />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Fetch error */}
          {fetchError && (
            <div className="alert alert-error" role="alert">
              <IconAlertCircle />
              <span>{fetchError}</span>
            </div>
          )}

          {/* Users Table Card */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">
                <div className="card-icon" style={{ background: '#e0f2fe', color: '#0891b2' }}>
                  <IconUsers />
                </div>
                Registered Users
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
                {users.length} {users.length === 1 ? 'user' : 'users'}
              </span>
            </div>

            <div style={{ minHeight: 200 }}>
              {loading ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 60, gap: 12, color: 'var(--color-text-muted)' }}>
                  <span className="spinner" style={{ borderTopColor: 'var(--color-accent)', borderColor: 'rgba(8,145,178,0.2)' }} />
                  Loading users…
                </div>
              ) : (
                <UsersTable users={users} onDelete={handleDelete} />
              )}
            </div>
          </div>
        </main>
      </div>

      {/* Modal */}
      {showModal && (
        <CreateUserModal
          onClose={() => setShowModal(false)}
          onCreated={handleCreated}
        />
      )}
    </div>
  );
}
