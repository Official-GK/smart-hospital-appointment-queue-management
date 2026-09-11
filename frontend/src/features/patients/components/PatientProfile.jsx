import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { patientService } from '../services/patientService';
import '../patients.css';

const PatientProfile = ({ initialPatientId = null }) => {
  const [selectedPatientId, setSelectedPatientId] = useState(initialPatientId);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [maskSensitive, setMaskSensitive] = useState(false);
  const [activeTab, setActiveTab] = useState('active'); // 'active' | 'history' | 'tokens' | 'audit'

  const [allPatients, setAllPatients] = useState([]);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const results = await patientService.searchPatients('');
        setAllPatients(results || []);
      } catch (err) {
        console.error(err);
      }
    };
    fetchAll();
  }, []);

  // Edit Demographics Modal State
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editFirstName, setEditFirstName] = useState('');
  const [editLastName, setEditLastName] = useState('');
  const [editPhone, setEditPhone] = useState('');
  const [editAddress, setEditAddress] = useState('');
  const [editGender, setEditGender] = useState('Other');
  const [editDob, setEditDob] = useState('');
  const [editReason, setEditReason] = useState('');
  const [editSubmitting, setEditSubmitting] = useState(false);

  const fetchProfile = async (patientId, masked = maskSensitive) => {
    if (!patientId) {
      setProfile(null);
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const data = await patientService.getPatientProfile(patientId, masked, 'Staff');
      setProfile(data);
    } catch (err) {
      console.error('Failed to load patient profile:', err);
      setError(err.message || 'Failed to load patient profile');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialPatientId && initialPatientId !== selectedPatientId) {
      setSelectedPatientId(initialPatientId);
    }
  }, [initialPatientId]);

  useEffect(() => {
    fetchProfile(selectedPatientId, maskSensitive);
  }, [selectedPatientId, maskSensitive]);

  // Handle Search Lookup
  const handleSearch = async (e) => {
    const q = e.target.value;
    setSearchQuery(q);
    if (!q.trim()) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }
    try {
      setIsSearching(true);
      const results = await patientService.searchPatients(q);
      setSearchResults(results);
    } catch (err) {
      console.error('Search error:', err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      if (searchResults.length > 0) {
        handleSelectPatient(searchResults[0].patient_id);
      } else if (searchQuery.trim()) {
        const qUpper = searchQuery.trim().toUpperCase();
        if (qUpper.startsWith('PAT-')) {
          handleSelectPatient(qUpper);
        }
      }
    } else if (e.key === 'Escape') {
      setSearchResults([]);
    }
  };

  const handleSelectPatient = (patientId) => {
    setSelectedPatientId(patientId);
    setSearchQuery('');
    setSearchResults([]);
  };

  const openEditModal = () => {
    if (!profile) return;
    setEditFirstName(profile.first_name || '');
    setEditLastName(profile.last_name || '');
    setEditPhone(profile.phone || '');
    setEditAddress(profile.address || '');
    setEditGender(profile.gender || 'Other');
    setEditDob(profile.date_of_birth ? profile.date_of_birth.toString().split('T')[0] : '');
    setEditReason('');
    setIsEditModalOpen(true);
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    try {
      setEditSubmitting(true);
      setError(null);
      await patientService.updatePatientProfile(selectedPatientId, {
        first_name: editFirstName.trim(),
        last_name: editLastName.trim(),
        phone: editPhone.trim(),
        address: editAddress.trim(),
        gender: editGender,
        date_of_birth: editDob || undefined,
        updated_by: 'Authorized Staff',
        notes: editReason.trim() || 'Demographic update via staff profile view',
      });

      setIsEditModalOpen(false);
      setSuccessMsg('Patient demographic and contact details updated with audit record.');
      setTimeout(() => setSuccessMsg(null), 5000);
      await fetchProfile(selectedPatientId, maskSensitive);
    } catch (err) {
      console.error('Failed to update patient profile:', err);
      setError(err.message || 'Failed to update patient details');
    } finally {
      setEditSubmitting(false);
    }
  };

  return (
    <div className="patient-profile-container">
      {/* Search Header */}
      <div className="checkin-header">
        <div>
          <h2 className="checkin-header-title">Patient Profile & Record History</h2>
          <p className="checkin-header-subtitle">
            Search patient records, view operational visit timestamps, token history, and maintain demographics with audit logging.
          </p>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div style={{
          padding: '0.75rem 1rem',
          borderRadius: '8px',
          background: '#fee2e2',
          color: '#991b1b',
          fontSize: '0.875rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontWeight: 700, color: '#991b1b' }}
            aria-label="Close"
          >
            Close
          </button>
        </div>
      )}

      {successMsg && (
        <div style={{
          padding: '0.75rem 1rem',
          borderRadius: '8px',
          background: '#dcfce7',
          color: '#166534',
          fontSize: '0.875rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>{successMsg}</span>
          <button
            onClick={() => setSuccessMsg(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontWeight: 700, color: '#166534' }}
            aria-label="Close"
          >
            Close
          </button>
        </div>
      )}

      {/* Search Bar & Quick Selectors */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <div className="checkin-search-bar" style={{ position: 'relative' }}>
          <div style={{ position: 'relative', width: '100%', display: 'flex', alignItems: 'center' }}>
            <input
              type="text"
              className="checkin-search-input"
              style={{ width: '100%', paddingRight: searchQuery ? '2.5rem' : '1rem' }}
              placeholder="Search patient by Name, Patient ID (e.g. PAT-001), or Phone Number..."
              value={searchQuery}
              onChange={handleSearch}
              onKeyDown={handleKeyDown}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => { setSearchQuery(''); setSearchResults([]); setIsSearching(false); }}
                style={{
                  position: 'absolute',
                  right: '0.75rem',
                  background: 'none',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  padding: '0.25rem',
                  display: 'flex',
                  alignItems: 'center',
                }}
                aria-label="Clear search"
              >
                Clear
              </button>
            )}
          </div>

          {searchQuery.trim().length > 0 && (
            <div style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              right: 0,
              background: '#ffffff',
              border: '1px solid #cbd5e1',
              borderRadius: '8px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
              zIndex: 30,
              marginTop: '4px',
              maxHeight: '260px',
              overflowY: 'auto'
            }}>
              {searchResults.length > 0 ? (
                searchResults.map((p) => (
                  <div
                    key={p.patient_id}
                    onClick={() => handleSelectPatient(p.patient_id)}
                    style={{
                      padding: '0.75rem 1rem',
                      borderBottom: '1px solid #f1f5f9',
                      cursor: 'pointer',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#f8fafc'}
                    onMouseLeave={(e) => e.currentTarget.style.background = '#ffffff'}
                  >
                    <div>
                      <strong>{p.patient_name || [p.first_name, p.last_name].filter(Boolean).join(' ') || 'Patient'}</strong>
                      <span style={{ fontSize: '0.75rem', color: '#64748b', marginLeft: '0.5rem' }}>({p.patient_id})</span>
                    </div>
                    <span style={{ fontSize: '0.8125rem', color: '#475569' }}>{p.phone}</span>
                  </div>
                ))
              ) : isSearching ? (
                <div style={{ padding: '0.875rem 1rem', color: '#64748b', fontSize: '0.875rem', textAlign: 'center' }}>
                  Searching patients...
                </div>
              ) : searchQuery.trim().length >= 2 ? (
                <div style={{ padding: '0.875rem 1rem', color: '#64748b', fontSize: '0.875rem', textAlign: 'center' }}>
                  No patients found matching "{searchQuery}".
                </div>
              ) : null}
            </div>
          )}
        </div>

        {selectedPatientId && (
          <div style={{ marginTop: '0.5rem' }}>
            <button
              className="btn btn-outline"
              onClick={() => { setSelectedPatientId(null); setProfile(null); }}
              style={{ fontSize: '0.8125rem', padding: '0.35rem 0.75rem' }}
            >
              &larr; Back to Patient List
            </button>
          </div>
        )}
      </div>

      {loading ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>
          Loading patient profile record...
        </div>
      ) : !selectedPatientId ? (
        <div className="checkin-table-wrapper" style={{ marginTop: '1rem' }}>
          <table className="checkin-table">
            <thead>
              <tr>
                <th>Patient ID</th>
                <th>Full Name</th>
                <th>Phone</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {allPatients.length === 0 ? (
                <tr><td colSpan="4" style={{ textAlign: 'center', padding: '2rem' }}>No patients found.</td></tr>
              ) : (
                allPatients.map(p => (
                  <tr key={p.patient_id} onClick={() => handleSelectPatient(p.patient_id)} style={{ cursor: 'pointer' }}>
                    <td><strong>{p.patient_id}</strong></td>
                    <td>{p.patient_name || [p.first_name, p.last_name].filter(Boolean).join(' ') || 'Unknown'}</td>
                    <td>{p.phone || 'N/A'}</td>
                    <td><span className="badge-normal">{p.status || 'Registered'}</span></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : !profile ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>
          No patient record found. Select a patient above to view details.
        </div>
      ) : (
        <>
          {/* Demographics Card */}
          <div className="profile-card">
            <div className="profile-header-row">
              <div className="profile-identity">
                <div className="profile-avatar-circle">
                  {(profile.first_name || profile.patient_name || 'P').trim()[0].toUpperCase()}
                </div>
                <div>
                  <h3 className="profile-name">
                    {profile.patient_name || [profile.first_name, profile.last_name].filter(Boolean).join(' ') || profile.name || 'Patient Record'}
                  </h3>
                  <div className="profile-meta-tags">
                    <span className="profile-id-badge">ID: {profile.patient_id}</span>
                    <span className="badge-normal">{profile.gender || 'Not Specified'}</span>
                    <span className="badge-scheduled">
                      {profile.age ? `${profile.age} yrs` : 'Age N/A'}
                    </span>
                    <span className="badge-checkedin">{profile.status}</span>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                <button
                  className="btn btn-secondary"
                  onClick={openEditModal}
                  style={{ fontSize: '0.8125rem', padding: '0.5rem 1rem' }}
                >
                  Edit Demographics
                </button>
              </div>
            </div>

            {/* Privacy Masking Bar */}
            <div className="privacy-control-bar">
              <label className="privacy-toggle-label">
                <input
                  type="checkbox"
                  checked={maskSensitive}
                  onChange={(e) => setMaskSensitive(e.target.checked)}
                />
                <span>Privacy Data Masking Mode (Role-based PII Protection)</span>
              </label>
              <span style={{ fontSize: '0.75rem', color: maskSensitive ? '#b91c1c' : '#15803d', fontWeight: 600 }}>
                {maskSensitive ? 'Sensitive Data Masked' : 'Full Data Visible (Authorized)'}
              </span>
            </div>

            {/* Demographics Info Grid */}
            <div className="profile-info-grid">
              <div className="profile-info-item">
                <span className="profile-info-label">Phone Number</span>
                <span className="profile-info-val">{profile.phone}</span>
              </div>
              <div className="profile-info-item">
                <span className="profile-info-label">Residential Address</span>
                <span className="profile-info-val">{profile.address || 'No address recorded'}</span>
              </div>
              <div className="profile-info-item">
                <span className="profile-info-label">Date of Birth</span>
                <span className="profile-info-val">
                  {profile.date_of_birth ? profile.date_of_birth.toString().split('T')[0] : 'Not recorded'}
                </span>
              </div>
              <div className="profile-info-item">
                <span className="profile-info-label">Registration Date</span>
                <span className="profile-info-val">
                  {new Date(profile.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="profile-info-item">
                <span className="profile-info-label">Last Arrival</span>
                <span className="profile-info-val">
                  {profile.last_arrival_time
                    ? new Date(profile.last_arrival_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    : 'None today'}
                </span>
              </div>
            </div>
          </div>

          {/* Sub-Views Tabs */}
          <div className="checkin-tabs">
            <button
              className={`checkin-tab-btn ${activeTab === 'active' ? 'active' : ''}`}
              onClick={() => setActiveTab('active')}
            >
              Active Appointments ({profile.active_appointments.length})
            </button>
            <button
              className={`checkin-tab-btn ${activeTab === 'history' ? 'active' : ''}`}
              onClick={() => setActiveTab('history')}
            >
              Visit History & Timestamps ({profile.visit_history.length})
            </button>
            <button
              className={`checkin-tab-btn ${activeTab === 'tokens' ? 'active' : ''}`}
              onClick={() => setActiveTab('tokens')}
            >
              Token History ({profile.token_history.length})
            </button>
            <button
              className={`checkin-tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
              onClick={() => setActiveTab('audit')}
            >
              Demographic Audit Trail ({profile.audit_trail.length})
            </button>
          </div>

          {/* Tab 1: Active Appointments */}
          {activeTab === 'active' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {profile.active_appointments.length === 0 ? (
                <div className="profile-card" style={{ textAlign: 'center', color: '#64748b', padding: '2.5rem' }}>
                  No active appointments currently scheduled for this patient.
                </div>
              ) : (
                profile.active_appointments.map((apt) => (
                  <div key={apt.appointment_id} className="profile-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <div>
                        <strong style={{ fontSize: '1.125rem', color: '#0f172a' }}>{apt.appointment_time}</strong>
                        <span style={{ fontSize: '0.875rem', color: '#64748b', marginLeft: '0.5rem' }}>{apt.appointment_date}</span>
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <span className={apt.priority === 'Emergency' ? 'badge-emergency' : 'badge-normal'}>
                          {apt.priority}
                        </span>
                        <span className="badge-scheduled">{apt.status}</span>
                      </div>
                    </div>

                    <div style={{ marginTop: '0.75rem', display: 'flex', gap: '1.5rem', flexWrap: 'wrap', fontSize: '0.875rem' }}>
                      <div>
                        <span style={{ color: '#64748b' }}>Doctor: </span>
                        <strong>{apt.doctor_name}</strong>
                      </div>
                      <div>
                        <span style={{ color: '#64748b' }}>Department: </span>
                        <strong>{apt.department_name}</strong>
                      </div>
                      <div>
                        <span style={{ color: '#64748b' }}>Visit Type: </span>
                        <span>{apt.is_walk_in ? 'Walk-In' : 'Scheduled'}</span>
                      </div>
                    </div>

                    {/* Operational Timestamps */}
                    <div className="timestamps-grid">
                      <div className="timestamp-box">
                        <span className="timestamp-title">Booking Time</span>
                        <span className="timestamp-time">
                          {apt.booking_time ? new Date(apt.booking_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'N/A'}
                        </span>
                      </div>
                      <div className="timestamp-box">
                        <span className="timestamp-title">Check-In Arrival</span>
                        <span className="timestamp-time">
                          {apt.check_in_time ? new Date(apt.check_in_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Pending Arrival'}
                        </span>
                      </div>
                      <div className="timestamp-box">
                        <span className="timestamp-title">Queue Entry</span>
                        <span className="timestamp-time">
                          {apt.queue_entry_time ? new Date(apt.queue_entry_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Not Queued'}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Tab 2: Visit History & Timestamps */}
          {activeTab === 'history' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {profile.visit_history.length === 0 ? (
                <div className="profile-card" style={{ textAlign: 'center', color: '#64748b', padding: '2.5rem' }}>
                  No prior completed visits on record for this patient.
                </div>
              ) : (
                profile.visit_history.map((v) => (
                  <div key={v.appointment_id} className="profile-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <div>
                        <strong style={{ fontSize: '1rem', color: '#0f172a' }}>{v.appointment_date} at {v.appointment_time}</strong>
                        <span style={{ fontSize: '0.8125rem', color: '#64748b', marginLeft: '0.5rem' }}>({v.appointment_id})</span>
                      </div>
                      <span className={v.status === 'Completed' ? 'badge-checkedin' : 'badge-normal'}>
                        {v.status}
                      </span>
                    </div>

                    <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: '#334155' }}>
                      <span>Attended by <strong>{v.doctor_name}</strong> in <strong>{v.department_name}</strong></span>
                      {v.notes && <p style={{ margin: '0.35rem 0 0', color: '#64748b', fontSize: '0.8125rem' }}>Notes: {v.notes}</p>}
                    </div>

                    {/* Full Operational Timestamps */}
                    <div className="timestamps-grid">
                      <div className="timestamp-box">
                        <span className="timestamp-title">Booked</span>
                        <span className="timestamp-time">
                          {v.booking_time ? new Date(v.booking_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'N/A'}
                        </span>
                      </div>
                      <div className="timestamp-box">
                        <span className="timestamp-title">Physical Arrival</span>
                        <span className="timestamp-time">
                          {v.check_in_time ? new Date(v.check_in_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'N/A'}
                        </span>
                      </div>
                      <div className="timestamp-box">
                        <span className="timestamp-title">Queue Entry</span>
                        <span className="timestamp-time">
                          {v.queue_entry_time ? new Date(v.queue_entry_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'N/A'}
                        </span>
                      </div>
                      <div className="timestamp-box">
                        <span className="timestamp-title">Consultation Start</span>
                        <span className="timestamp-time">
                          {v.consultation_start_time ? new Date(v.consultation_start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'N/A'}
                        </span>
                      </div>
                      <div className="timestamp-box">
                        <span className="timestamp-title">Visit Completed</span>
                        <span className="timestamp-time">
                          {v.completion_time ? new Date(v.completion_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Tab 3: Token History */}
          {activeTab === 'tokens' && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
              {profile.token_history.length === 0 ? (
                <div className="profile-card" style={{ gridColumn: '1 / -1', textAlign: 'center', color: '#64748b', padding: '2.5rem' }}>
                  No token records found for this patient.
                </div>
              ) : (
                profile.token_history.map((tok) => (
                  <div key={tok.token_id} className="token-history-card">
                    <div>
                      <div className="token-code-tag">{tok.token_number}</div>
                      <div style={{ marginTop: '0.35rem', fontSize: '0.8125rem', color: '#334155', fontWeight: 600 }}>
                        {tok.doctor_name || 'Clinic Doctor'}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                        {tok.department_name} - {tok.priority}
                      </div>
                    </div>
                    <span className="badge-normal">{tok.status}</span>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Tab 4: Demographic Audit Trail */}
          {activeTab === 'audit' && (
            <div className="checkin-table-wrapper">
              <table className="checkin-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Changed By</th>
                    <th>Field Modified</th>
                    <th>Previous Value</th>
                    <th>New Value</th>
                    <th>Reason / Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {profile.audit_trail.length === 0 ? (
                    <tr>
                      <td colSpan="6" style={{ textAlign: 'center', padding: '2.5rem', color: '#64748b' }}>
                        No demographic modifications have been logged for this patient yet.
                      </td>
                    </tr>
                  ) : (
                    profile.audit_trail.map((rec) => (
                      <tr key={rec.audit_id}>
                        <td>{new Date(rec.timestamp).toLocaleString()}</td>
                        <td><strong>{rec.changed_by}</strong></td>
                        <td><code>{rec.field_name}</code></td>
                        <td style={{ color: '#b91c1c' }}>{rec.old_value || '(empty)'}</td>
                        <td style={{ color: '#15803d', fontWeight: 600 }}>{rec.new_value}</td>
                        <td style={{ color: '#64748b' }}>{rec.notes || 'Routine update'}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Edit Demographics Modal */}
      {isEditModalOpen && (
        <div className="checkin-modal-overlay" onClick={() => setIsEditModalOpen(false)}>
          <div className="checkin-receipt-card" style={{ maxWidth: '540px' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, fontSize: '1.125rem', color: '#0f172a' }}>
                Update Patient Demographics
              </h3>
              <button
                onClick={() => setIsEditModalOpen(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontWeight: 700, color: '#64748b' }}
                aria-label="Close"
              >
                Close
              </button>
            </div>

            <form onSubmit={handleEditSubmit}>
              <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div className="form-group">
                    <label className="form-label">First Name</label>
                    <input
                      type="text"
                      className="form-control"
                      value={editFirstName}
                      onChange={(e) => setEditFirstName(e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Last Name</label>
                    <input
                      type="text"
                      className="form-control"
                      value={editLastName}
                      onChange={(e) => setEditLastName(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Contact Phone</label>
                  <input
                    type="tel"
                    className="form-control"
                    value={editPhone}
                    onChange={(e) => setEditPhone(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Residential Address</label>
                  <input
                    type="text"
                    className="form-control"
                    value={editAddress}
                    onChange={(e) => setEditAddress(e.target.value)}
                    required
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div className="form-group">
                    <label className="form-label">Gender</label>
                    <select
                      className="form-control"
                      value={editGender}
                      onChange={(e) => setEditGender(e.target.value)}
                    >
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Date of Birth</label>
                    <input
                      type="date"
                      className="form-control"
                      value={editDob}
                      onChange={(e) => setEditDob(e.target.value)}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Reason for Modification (Audit Log) *</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="e.g. Patient moved to new apartment / phone change"
                    value={editReason}
                    onChange={(e) => setEditReason(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div style={{ padding: '1rem 1.5rem', background: '#f8fafc', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setIsEditModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={editSubmitting}
                >
                  {editSubmitting ? 'Saving...' : 'Save & Log Audit'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

PatientProfile.propTypes = {
  initialPatientId: PropTypes.string,
};

export default PatientProfile;
