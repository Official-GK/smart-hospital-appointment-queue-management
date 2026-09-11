import React, { useState, useEffect, useCallback } from 'react';
import PropTypes from 'prop-types';
import { patientService } from '../services/patientService';
import '../patients.css';

const PatientRegistration = ({
  onRegistrationSuccess = () => {},
  onCheckInPatient = () => {},
  onViewProfile = () => {},
}) => {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [age, setAge] = useState('');
  const [dob, setDob] = useState('');
  const [gender, setGender] = useState('Male');
  const [contactNumber, setContactNumber] = useState('');
  const [address, setAddress] = useState('');
  const [identifier, setIdentifier] = useState('');
  const [notes, setNotes] = useState('');

  const [isCheckingDuplicate, setIsCheckingDuplicate] = useState(false);
  const [duplicateWarning, setDuplicateWarning] = useState(null);
  const [duplicateData, setDuplicateData] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [registeredPatient, setRegisteredPatient] = useState(null);

  // Sync Date of Birth when Age is entered
  const handleAgeChange = (val) => {
    setAge(val);
    const parsedAge = parseInt(val, 10);
    if (!isNaN(parsedAge) && parsedAge >= 0 && parsedAge <= 125) {
      const currentYear = new Date().getFullYear();
      const birthYear = currentYear - parsedAge;
      // Default to January 1st of that birth year if no DOB set
      setDob(`${birthYear}-01-01`);
    } else if (val === '') {
      setDob('');
    }
  };

  // Sync Age when Date of Birth is picked
  const handleDobChange = (val) => {
    setDob(val);
    if (val) {
      const birthDate = new Date(val);
      const today = new Date();
      if (!isNaN(birthDate.getTime())) {
        let calculatedAge = today.getFullYear() - birthDate.getFullYear();
        const m = today.getMonth() - birthDate.getMonth();
        if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
          calculatedAge--;
        }
        if (calculatedAge >= 0) {
          setAge(String(calculatedAge));
        }
      }
    }
  };

  // Duplicate check trigger
  const runDuplicateCheck = useCallback(async (phoneVal, idVal) => {
    const cleanPhone = (phoneVal || '').trim();
    const cleanId = (idVal || '').trim();
    if (cleanPhone.length < 7 && !cleanId) {
      setDuplicateWarning(null);
      setDuplicateData(null);
      return;
    }

    try {
      setIsCheckingDuplicate(true);
      const result = await patientService.checkDuplicate({
        contactNumber: cleanPhone,
        identifier: cleanId,
      });

      if (result && result.is_duplicate) {
        setDuplicateWarning(result.message || 'Duplicate patient record detected.');
        setDuplicateData(result);
      } else {
        setDuplicateWarning(null);
        setDuplicateData(null);
      }
    } catch (err) {
      console.warn('Duplicate check could not complete:', err);
    } finally {
      setIsCheckingDuplicate(false);
    }
  }, []);

  const handleContactBlur = () => {
    runDuplicateCheck(contactNumber, identifier);
  };

  const handleIdentifierBlur = () => {
    runDuplicateCheck(contactNumber, identifier);
  };

  // Form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!firstName.trim()) {
      setError('First name is required.');
      return;
    }
    if (!lastName.trim()) {
      setError('Last name is required.');
      return;
    }
    if (!contactNumber.trim()) {
      setError('Contact number is required.');
      return;
    }
    if (age === '' && !dob) {
      setError('Patient age or date of birth is required.');
      return;
    }

    if (duplicateWarning) {
      setError(`Cannot register duplicate patient: ${duplicateWarning}`);
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        age: age !== '' ? parseInt(age, 10) : null,
        date_of_birth: dob || null,
        gender,
        contact_number: contactNumber.trim(),
        phone: contactNumber.trim(),
        address: address.trim() || null,
        identifier: identifier.trim() || null,
        notes: notes.trim() || null,
      };

      const newPatient = await patientService.registerPatient(payload);
      setRegisteredPatient(newPatient);
      onRegistrationSuccess(newPatient);
    } catch (err) {
      console.error('Registration failed:', err);
      const errMsg = err.message || 'Registration failed. Please check details and try again.';
      setError(errMsg);
      const match = errMsg.match(/PAT-\d{3,}/);
      if (match) {
        setDuplicateData((prev) => ({
          ...prev,
          is_duplicate: true,
          existing_patient_id: match[0],
          message: errMsg,
        }));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleResetForm = () => {
    setFirstName('');
    setLastName('');
    setAge('');
    setDob('');
    setGender('Male');
    setContactNumber('');
    setAddress('');
    setIdentifier('');
    setNotes('');
    setDuplicateWarning(null);
    setDuplicateData(null);
    setError(null);
    setRegisteredPatient(null);
  };

  return (
    <div className="patient-registration-container">
      {/* Header */}
      <div className="registration-header">
        <div>
          <h2 className="registration-title">New Patient Registration</h2>
          <p className="registration-subtitle">
            Create a central patient record for appointment scheduling and queue tracking
          </p>
        </div>
      </div>

      {/* Success View */}
      {registeredPatient ? (
        <div className="registration-success-card">
          <div className="registration-success-banner">
            <div className="success-icon-badge">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <h3 className="success-title">Patient Successfully Registered</h3>
              <p className="success-desc">
                Central patient record created and immediately active in the hospital system.
              </p>
            </div>
          </div>

          <div className="registered-patient-summary">
            <div className="summary-id-row">
              <span className="summary-id-label">System-Generated Patient ID</span>
              <span className="summary-id-badge">{registeredPatient.patient_id}</span>
            </div>

            <div className="summary-grid">
              <div className="summary-field">
                <span className="summary-field-label">Full Name</span>
                <span className="summary-field-val">{registeredPatient.patient_name}</span>
              </div>
              <div className="summary-field">
                <span className="summary-field-label">Age / Gender</span>
                <span className="summary-field-val">
                  {registeredPatient.age ? `${registeredPatient.age} yrs` : 'N/A'} • {registeredPatient.gender || 'Other'}
                </span>
              </div>
              <div className="summary-field">
                <span className="summary-field-label">Contact Number</span>
                <span className="summary-field-val">{registeredPatient.phone}</span>
              </div>
              <div className="summary-field">
                <span className="summary-field-label">Status</span>
                <span className="summary-field-val status-badge-registered">
                  {registeredPatient.status || 'Registered'}
                </span>
              </div>
              {registeredPatient.address && (
                <div className="summary-field full-width">
                  <span className="summary-field-label">Address</span>
                  <span className="summary-field-val">{registeredPatient.address}</span>
                </div>
              )}
            </div>
          </div>

          {/* Immediate Actions */}
          <div className="registration-actions-bar">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => onCheckInPatient(registeredPatient)}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '6px' }}>
                <path d="M9 11l3 3L22 4" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Check In Patient Now
            </button>

            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => onViewProfile(registeredPatient.patient_id)}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '6px' }}>
                <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
              View Patient Profile
            </button>

            <button
              type="button"
              className="btn btn-outline"
              onClick={handleResetForm}
            >
              Register Another Patient
            </button>
          </div>
        </div>
      ) : (
        /* Registration Form */
        <div className="registration-card">
          {error && (
            <div className="registration-error-alert" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '0.625rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <span>{error}</span>
              </div>
              {duplicateData?.existing_patient_id && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: '0.8125rem', padding: '0.35rem 0.75rem', alignSelf: 'flex-start' }}
                  onClick={() => onViewProfile(duplicateData.existing_patient_id)}
                >
                  View Existing Patient Profile ({duplicateData.existing_patient_id})
                </button>
              )}
            </div>
          )}

          {duplicateWarning && (
            <div className="registration-duplicate-alert">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
              <div style={{ flex: 1 }}>
                <strong>Existing Patient Found</strong>
                <p>{duplicateWarning}</p>
                <span className="duplicate-hint">
                  Same patient does not require a new ID. You can access and manage their profile directly.
                </span>
                {duplicateData?.existing_patient_id && (
                  <div style={{ marginTop: '0.625rem' }}>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ fontSize: '0.8125rem', padding: '0.35rem 0.75rem' }}
                      onClick={() => onViewProfile(duplicateData.existing_patient_id)}
                    >
                      View Existing Patient Profile ({duplicateData.existing_patient_id})
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="registration-form">
            {/* Section 1: Demographics */}
            <div className="form-section-title">
              <span>1. Basic Demographics</span>
            </div>

            <div className="registration-form-grid">
              {/* First Name */}
              <div className="form-group">
                <label className="form-label" htmlFor="reg-first-name">
                  First Name <span className="text-danger">*</span>
                </label>
                <input
                  id="reg-first-name"
                  type="text"
                  className="form-input"
                  placeholder="e.g. Samantha"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  required
                />
              </div>

              {/* Last Name */}
              <div className="form-group">
                <label className="form-label" htmlFor="reg-last-name">
                  Last Name <span className="text-danger">*</span>
                </label>
                <input
                  id="reg-last-name"
                  type="text"
                  className="form-input"
                  placeholder="e.g. Hayes"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  required
                />
              </div>

              {/* Age */}
              <div className="form-group">
                <label className="form-label" htmlFor="reg-age">
                  Age <span className="text-danger">*</span>
                </label>
                <input
                  id="reg-age"
                  type="number"
                  min="0"
                  max="125"
                  className="form-input"
                  placeholder="e.g. 28"
                  value={age}
                  onChange={(e) => handleAgeChange(e.target.value)}
                  required
                />
                <span className="field-hint">Auto-computes year of birth</span>
              </div>

              {/* Date of Birth */}
              <div className="form-group">
                <label className="form-label" htmlFor="reg-dob">
                  Date of Birth
                </label>
                <input
                  id="reg-dob"
                  type="date"
                  className="form-input"
                  value={dob}
                  onChange={(e) => handleDobChange(e.target.value)}
                />
                <span className="field-hint">Optional if age is provided</span>
              </div>

              {/* Gender */}
              <div className="form-group">
                <label className="form-label" htmlFor="reg-gender">
                  Gender <span className="text-danger">*</span>
                </label>
                <select
                  id="reg-gender"
                  className="form-select"
                  value={gender}
                  onChange={(e) => setGender(e.target.value)}
                  required
                >
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              {/* Identifier (Optional) */}
              <div className="form-group">
                <label className="form-label" htmlFor="reg-identifier">
                  Custom Identifier / National ID
                </label>
                <input
                  id="reg-identifier"
                  type="text"
                  className="form-input"
                  placeholder="e.g. NAT-90210 (Optional)"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  onBlur={handleIdentifierBlur}
                />
                <span className="field-hint">Checked for duplicate conflicts</span>
              </div>
            </div>

            {/* Section 2: Contact & Address */}
            <div className="form-section-title" style={{ marginTop: '1.5rem' }}>
              <span>2. Contact & Address</span>
            </div>

            <div className="registration-form-grid">
              {/* Contact Number */}
              <div className="form-group">
                <label className="form-label" htmlFor="reg-contact">
                  Contact Number <span className="text-danger">*</span>
                  {isCheckingDuplicate && (
                    <span className="checking-indicator">Checking duplicates...</span>
                  )}
                </label>
                <input
                  id="reg-contact"
                  type="tel"
                  className={`form-input ${duplicateWarning ? 'input-conflict' : ''}`}
                  placeholder="e.g. +1-555-0199"
                  value={contactNumber}
                  onChange={(e) => {
                    setContactNumber(e.target.value);
                    if (duplicateWarning) setDuplicateWarning(null);
                  }}
                  onBlur={handleContactBlur}
                  required
                />
                <span className="field-hint">Used for patient lookup & duplicate verification</span>
              </div>

              {/* Address */}
              <div className="form-group full-width">
                <label className="form-label" htmlFor="reg-address">
                  Residential Address
                </label>
                <input
                  id="reg-address"
                  type="text"
                  className="form-input"
                  placeholder="e.g. 742 Evergreen Terrace, Springfield"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                />
              </div>

              {/* Notes / Special Instructions */}
              <div className="form-group full-width">
                <label className="form-label" htmlFor="reg-notes">
                  Registration Notes / Medical Alerts
                </label>
                <textarea
                  id="reg-notes"
                  className="form-textarea"
                  rows="2"
                  placeholder="e.g. Referred by Dr. Smith, requires wheelchair access (Optional)"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </div>
            </div>

            {/* ID Auto-generation Notice */}
            <div className="id-generation-notice">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
              <span>
                A unique Patient ID (e.g. <strong>PAT-009</strong>) will be automatically generated upon submission.
              </span>
            </div>

            {/* Form Action Buttons */}
            <div className="form-actions" style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem' }}>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={submitting || Boolean(duplicateWarning)}
                style={{ minWidth: '160px' }}
              >
                {submitting ? 'Registering...' : 'Register Patient'}
              </button>

              <button
                type="button"
                className="btn btn-outline"
                onClick={handleResetForm}
                disabled={submitting}
              >
                Clear Form
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};

PatientRegistration.propTypes = {
  onRegistrationSuccess: PropTypes.func,
  onCheckInPatient: PropTypes.func,
  onViewProfile: PropTypes.func,
};

export default PatientRegistration;
