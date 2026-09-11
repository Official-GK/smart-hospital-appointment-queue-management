import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { patientService } from '../services/patientService';
import '../patients.css';

const DEPARTMENTS_DATA = [
  { id: 'DEP-GEN', name: 'General Medicine' },
  { id: 'DEP-CARD', name: 'Cardiology' },
  { id: 'DEP-ORTHO', name: 'Orthopedics' },
  { id: 'DEP-PED', name: 'Pediatrics' },
  { id: 'DEP-DERM', name: 'Dermatology' },
];

const DOCTORS_DATA = [
  { id: 'DOC-001', name: 'Dr. Sarah Jenkins', departmentId: 'DEP-CARD' },
  { id: 'DOC-002', name: 'Dr. Marcus Johnson', departmentId: 'DEP-ORTHO' },
  { id: 'DOC-003', name: 'Dr. Emily Rodriguez', departmentId: 'DEP-GEN' },
  { id: 'DOC-004', name: 'Dr. James Chen', departmentId: 'DEP-PED' },
  { id: 'DOC-005', name: 'Dr. Aisha Patel', departmentId: 'DEP-DERM' },
];

const PatientCheckIn = ({ onCheckInSuccess = () => {} }) => {
  const [activeTab, setActiveTab] = useState('scheduled'); // 'scheduled' | 'walkin'
  const [eligibleList, setEligibleList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [processingId, setProcessingId] = useState(null);
  const [receipt, setReceipt] = useState(null);

  // Walk-in form state
  const [walkinName, setWalkinName] = useState('');
  const [walkinPhone, setWalkinPhone] = useState('');
  const [walkinDept, setWalkinDept] = useState('DEP-GEN');
  const [walkinDoctor, setWalkinDoctor] = useState('DOC-003');
  const [walkinPriority, setWalkinPriority] = useState('Normal');
  const [walkinNotes, setWalkinNotes] = useState('');
  const [walkinSubmitting, setWalkinSubmitting] = useState(false);

  const fetchEligible = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await patientService.getEligibleCheckIns();
      setEligibleList(data);
    } catch (err) {
      console.error('Failed to load eligible check-in appointments', err);
      setError('Could not load appointments. Please check connection to backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEligible();
  }, []);

  // Update doctor choices when department changes
  useEffect(() => {
    const matched = DOCTORS_DATA.filter(d => d.departmentId === walkinDept);
    if (matched.length > 0) {
      setWalkinDoctor(matched[0].id);
    }
  }, [walkinDept]);

  const handleExecuteCheckIn = async (item) => {
    try {
      setProcessingId(item.appointment_id);
      setError(null);

      const checkInReceipt = await patientService.checkInPatient({
        appointment_id: item.appointment_id,
        patient_id: item.patient_id,
        patient_name: item.patient_name,
        doctor_id: item.doctor_id,
        department_id: item.department_id,
        priority: item.priority || 'Normal',
        is_walk_in: false,
        notes: `Physical front-desk check-in for scheduled slot ${item.appointment_time}`,
      });

      setReceipt(checkInReceipt);
      onCheckInSuccess(checkInReceipt);
      await fetchEligible();
    } catch (err) {
      console.error('Check-in error', err);
      setError(err.message || 'Failed to check in patient');
    } finally {
      setProcessingId(null);
    }
  };

  const handleWalkInSubmit = async (e) => {
    e.preventDefault();
    if (!walkinName.trim()) {
      setError('Please enter the patient name for walk-in check-in.');
      return;
    }

    try {
      setWalkinSubmitting(true);
      setError(null);

      const docObj = DOCTORS_DATA.find(d => d.id === walkinDoctor);
      const deptObj = DEPARTMENTS_DATA.find(d => d.id === walkinDept);

      const checkInReceipt = await patientService.checkInPatient({
        patient_name: walkinName.trim(),
        phone: walkinPhone.trim() || undefined,
        department_id: walkinDept,
        department_name: deptObj ? deptObj.name : undefined,
        doctor_id: walkinDoctor,
        doctor_name: docObj ? docObj.name : undefined,
        priority: walkinPriority,
        is_walk_in: true,
        notes: walkinNotes.trim() || 'Walk-in arrival',
      });

      setReceipt(checkInReceipt);
      onCheckInSuccess(checkInReceipt);

      // Reset walk-in form
      setWalkinName('');
      setWalkinPhone('');
      setWalkinNotes('');
      setWalkinPriority('Normal');
      await fetchEligible();
    } catch (err) {
      console.error('Walk-in check-in error', err);
      setError(err.message || 'Failed to check in walk-in patient');
    } finally {
      setWalkinSubmitting(false);
    }
  };

  const filteredEligible = eligibleList.filter(item => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    return (
      (item.patient_name && item.patient_name.toLowerCase().includes(q)) ||
      (item.patient_id && item.patient_id.toLowerCase().includes(q)) ||
      (item.appointment_id && item.appointment_id.toLowerCase().includes(q)) ||
      (item.phone && item.phone.includes(q))
    );
  });

  return (
    <div className="patient-checkin-container">
      {/* Header */}
      <div className="checkin-header">
        <div>
          <h2 className="checkin-header-title">Patient Arrival Check-In</h2>
          <p className="checkin-header-subtitle">
            Record physical arrival, update patient status to Checked-In, and assign active queue tokens.
          </p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={fetchEligible}
          disabled={loading}
        >
          {loading ? 'Refreshing...' : 'Refresh List'}
        </button>
      </div>

      {/* Error alert */}
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
          >
            ✕
          </button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="checkin-tabs">
        <button
          className={`checkin-tab-btn ${activeTab === 'scheduled' ? 'active' : ''}`}
          onClick={() => setActiveTab('scheduled')}
        >
          Scheduled Appointments ({eligibleList.length})
        </button>
        <button
          className={`checkin-tab-btn ${activeTab === 'walkin' ? 'active' : ''}`}
          onClick={() => setActiveTab('walkin')}
        >
          Walk-In Patient Check-In
        </button>
      </div>

      {/* Tab 1: Scheduled Appointments */}
      {activeTab === 'scheduled' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="checkin-search-bar">
            <input
              type="text"
              className="checkin-search-input"
              placeholder="Search scheduled arriving patient by name, phone, or appointment ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="checkin-table-wrapper">
            <table className="checkin-table">
              <thead>
                <tr>
                  <th>Time / Date</th>
                  <th>Patient</th>
                  <th>Department & Doctor</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {loading && eligibleList.length === 0 ? (
                  <tr>
                    <td colSpan="6" style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
                      Loading arriving appointments...
                    </td>
                  </tr>
                ) : filteredEligible.length === 0 ? (
                  <tr>
                    <td colSpan="6" style={{ textAlign: 'center', padding: '2.5rem', color: '#64748b' }}>
                      {searchQuery ? 'No matching scheduled arrivals found.' : 'No pending scheduled appointments awaiting check-in.'}
                    </td>
                  </tr>
                ) : (
                  filteredEligible.map((item) => (
                    <tr key={item.appointment_id}>
                      <td>
                        <strong style={{ display: 'block', color: 'var(--text-main)' }}>{item.appointment_time}</strong>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{item.appointment_date}</span>
                      </td>
                      <td>
                        <strong style={{ display: 'block', color: 'var(--text-main)' }}>{item.patient_name}</strong>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{item.patient_id}</span>
                      </td>
                      <td>
                        <div style={{ fontWeight: 600 }}>{item.department_name}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{item.doctor_name}</div>
                      </td>
                      <td>
                        <span className={item.priority === 'Emergency' ? 'badge-emergency' : 'badge-normal'}>
                          {item.priority || 'Normal'}
                        </span>
                      </td>
                      <td>
                        <span className="badge-scheduled">Scheduled</span>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          className="btn-checkin-action"
                          onClick={() => handleExecuteCheckIn(item)}
                          disabled={processingId === item.appointment_id}
                        >
                          {processingId === item.appointment_id ? (
                            'Checking In...'
                          ) : (
                            <>
                              <span>✓</span> Check In
                            </>
                          )}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Walk-In Check-In Form */}
      {activeTab === 'walkin' && (
        <div className="walkin-card">
          <h3 style={{ margin: '0 0 0.5rem', fontSize: '1.125rem', color: 'var(--text-main)' }}>
            Instant Walk-In Arrival Registration
          </h3>
          <p style={{ margin: '0 0 1.25rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
            Directly register and queue a walk-in patient without an existing prior booking.
          </p>

          <form onSubmit={handleWalkInSubmit}>
            <div className="walkin-form-grid">
              <div className="form-group">
                <label className="form-label">Patient Full Name *</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g. John Doe"
                  value={walkinName}
                  onChange={(e) => setWalkinName(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Contact Phone</label>
                <input
                  type="tel"
                  className="form-control"
                  placeholder="e.g. +1-555-0199"
                  value={walkinPhone}
                  onChange={(e) => setWalkinPhone(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Department *</label>
                <select
                  className="form-control"
                  value={walkinDept}
                  onChange={(e) => setWalkinDept(e.target.value)}
                >
                  {DEPARTMENTS_DATA.map(dept => (
                    <option key={dept.id} value={dept.id}>{dept.name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Attending Doctor *</label>
                <select
                  className="form-control"
                  value={walkinDoctor}
                  onChange={(e) => setWalkinDoctor(e.target.value)}
                >
                  {DOCTORS_DATA.filter(d => d.departmentId === walkinDept).map(doc => (
                    <option key={doc.id} value={doc.id}>{doc.name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Queue Priority</label>
                <select
                  className="form-control"
                  value={walkinPriority}
                  onChange={(e) => setWalkinPriority(e.target.value)}
                >
                  <option value="Normal">Normal Priority</option>
                  <option value="Emergency">🚨 Emergency (Immediate Triage)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Reason / Notes</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g. Fever, persistent cough"
                  value={walkinNotes}
                  onChange={(e) => setWalkinNotes(e.target.value)}
                />
              </div>
            </div>

            <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                type="submit"
                className="btn-checkin-action"
                style={{ padding: '0.625rem 1.5rem', fontSize: '0.875rem' }}
                disabled={walkinSubmitting}
              >
                {walkinSubmitting ? 'Checking In...' : '✓ Check In Walk-In Patient'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Confirmation Receipt Modal */}
      {receipt && (
        <div className="checkin-modal-overlay" onClick={() => setReceipt(null)}>
          <div className="checkin-receipt-card" onClick={(e) => e.stopPropagation()}>
            <div className="receipt-header">
              <div style={{ fontSize: '0.875rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Check-In Confirmed
              </div>
              <div className="receipt-token-chip">
                {receipt.token_number || 'T-ACTIVE'}
              </div>
              <div style={{ fontSize: '0.8125rem', opacity: 0.9, marginTop: '0.35rem' }}>
                Queue Token Assigned
              </div>
            </div>

            <div className="receipt-body">
              <div className="receipt-row">
                <span className="receipt-label">Patient Name</span>
                <span className="receipt-value">{receipt.patient_name}</span>
              </div>
              <div className="receipt-row">
                <span className="receipt-label">Status</span>
                <span className="badge-checkedin">Checked-In</span>
              </div>
              <div className="receipt-row">
                <span className="receipt-label">Arrival Timestamp</span>
                <span className="receipt-value">
                  {new Date(receipt.arrival_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              </div>
              <div className="receipt-row">
                <span className="receipt-label">Doctor & Department</span>
                <span className="receipt-value">
                  {receipt.doctor_name} ({receipt.department_name})
                </span>
              </div>
              <div className="receipt-row">
                <span className="receipt-label">Active Queue Position</span>
                <span className="receipt-value" style={{ color: '#16a34a' }}>
                  Position #{receipt.queue_position || 1}
                </span>
              </div>
              <div className="receipt-row">
                <span className="receipt-label">Est. Wait Time</span>
                <span className="receipt-value">
                  ~{receipt.estimated_wait_minutes || 15} mins
                </span>
              </div>
              <div className="receipt-row">
                <span className="receipt-label">Visit Type</span>
                <span className="receipt-value">
                  {receipt.is_walk_in ? 'Walk-In Visit' : 'Scheduled Appointment'}
                </span>
              </div>
            </div>

            <div className="receipt-footer">
              <button
                className="btn btn-primary"
                onClick={() => setReceipt(null)}
              >
                Close Receipt
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

PatientCheckIn.propTypes = {
  onCheckInSuccess: PropTypes.func,
};

export default PatientCheckIn;
