import React, { useState } from 'react';
import { PatientProfile, PatientRegistration } from './features/patients';
import StaffDashboard from './pages/StaffDashboard';
import './App.css';

const Temp = () => {
  const [view, setView] = useState('registration'); // 'registration' | 'profile' | 'dashboard'
  const [selectedPatientId, setSelectedPatientId] = useState('PAT-001');

  const handleRegistrationSuccess = (patient) => {
    console.log('Patient registered successfully:', patient);
    if (patient?.patient_id) {
      setSelectedPatientId(patient.patient_id);
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc' }}>
      {/* Test Navigation Bar */}
      <header style={{
        background: '#0f172a',
        color: '#ffffff',
        padding: '0.75rem 1.5rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
        position: 'sticky',
        top: 0,
        zIndex: 50
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontWeight: 700, fontSize: '1rem', letterSpacing: '0.02em' }}>
            Patient Feature Test Environment
          </span>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            onClick={() => setView('registration')}
            style={{
              background: view === 'registration' ? '#2563eb' : '#334155',
              color: '#ffffff',
              border: 'none',
              padding: '0.4rem 0.9rem',
              borderRadius: '6px',
              fontSize: '0.8125rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Register Patient
          </button>
          <button
            onClick={() => setView('profile')}
            style={{
              background: view === 'profile' ? '#2563eb' : '#334155',
              color: '#ffffff',
              border: 'none',
              padding: '0.4rem 0.9rem',
              borderRadius: '6px',
              fontSize: '0.8125rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Patient Profile
          </button>
          <button
            onClick={() => setView('dashboard')}
            style={{
              background: view === 'dashboard' ? '#2563eb' : '#334155',
              color: '#ffffff',
              border: 'none',
              padding: '0.4rem 0.9rem',
              borderRadius: '6px',
              fontSize: '0.8125rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Full Staff Dashboard
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      {view === 'registration' && (
        <main style={{ maxWidth: '900px', margin: '2rem auto', padding: '0 1.5rem' }}>
          <PatientRegistration
            onRegistrationSuccess={handleRegistrationSuccess}
            onCheckInPatient={() => setView('dashboard')}
            onViewProfile={(patientId) => {
              if (patientId) setSelectedPatientId(patientId);
              setView('profile');
            }}
          />
        </main>
      )}

      {view === 'profile' && (
        <main style={{ maxWidth: '1200px', margin: '2rem auto', padding: '0 1.5rem' }}>
          <PatientProfile initialPatientId={selectedPatientId} key={selectedPatientId} />
        </main>
      )}

      {view === 'dashboard' && (
        <StaffDashboard />
      )}
    </div>
  );
};

export default Temp;
