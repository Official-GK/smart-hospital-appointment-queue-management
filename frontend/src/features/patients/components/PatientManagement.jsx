import React, { useState } from 'react';
import PatientCheckIn from './PatientCheckIn';
import PatientRegistration from './PatientRegistration';
import PatientProfile from './PatientProfile';

const PatientManagement = () => {
  const [activeSubTab, setActiveSubTab] = useState('checkin');
  const [profileId, setProfileId] = useState(null);

  // Handlers for Registration success
  const handleRegistrationSuccess = (newPatient) => {
    setProfileId(newPatient.patient_id);
    setActiveSubTab('profile');
  };

  const handleCheckInPatient = (patient) => {
    setActiveSubTab('checkin');
  };

  const handleViewProfile = (patientId) => {
    setProfileId(patientId);
    setActiveSubTab('profile');
  };

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ display: 'flex', gap: '1rem', borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem' }}>
        <button
          onClick={() => setActiveSubTab('checkin')}
          style={{
            padding: '0.5rem 1rem',
            background: 'none',
            border: 'none',
            borderBottom: activeSubTab === 'checkin' ? '2px solid #0ea5e9' : '2px solid transparent',
            color: activeSubTab === 'checkin' ? '#0f172a' : '#64748b',
            fontWeight: activeSubTab === 'checkin' ? 600 : 400,
            cursor: 'pointer',
            fontSize: '1rem'
          }}
        >
          Check-In
        </button>
        <button
          onClick={() => setActiveSubTab('registration')}
          style={{
            padding: '0.5rem 1rem',
            background: 'none',
            border: 'none',
            borderBottom: activeSubTab === 'registration' ? '2px solid #0ea5e9' : '2px solid transparent',
            color: activeSubTab === 'registration' ? '#0f172a' : '#64748b',
            fontWeight: activeSubTab === 'registration' ? 600 : 400,
            cursor: 'pointer',
            fontSize: '1rem'
          }}
        >
          New Registration
        </button>
        <button
          onClick={() => setActiveSubTab('profile')}
          style={{
            padding: '0.5rem 1rem',
            background: 'none',
            border: 'none',
            borderBottom: activeSubTab === 'profile' ? '2px solid #0ea5e9' : '2px solid transparent',
            color: activeSubTab === 'profile' ? '#0f172a' : '#64748b',
            fontWeight: activeSubTab === 'profile' ? 600 : 400,
            cursor: 'pointer',
            fontSize: '1rem'
          }}
        >
          Patient Profiles
        </button>
      </div>

      <div>
        {activeSubTab === 'checkin' && (
          <PatientCheckIn onCheckInSuccess={() => {}} />
        )}
        
        {activeSubTab === 'registration' && (
          <PatientRegistration 
            onRegistrationSuccess={handleRegistrationSuccess}
            onCheckInPatient={handleCheckInPatient}
            onViewProfile={handleViewProfile}
          />
        )}
        
        {activeSubTab === 'profile' && (
          <PatientProfile initialPatientId={profileId || null} />
        )}
      </div>
    </div>
  );
};

export default PatientManagement;
