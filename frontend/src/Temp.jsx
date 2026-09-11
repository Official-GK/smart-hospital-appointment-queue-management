import React, { useState } from 'react';
import { PatientCheckIn, PatientProfile, PatientRegistration } from './features/patients';
import QueueDashboard from './features/queue/components/QueueDashboard';
import StaffDashboard from './pages/StaffDashboard';
import './App.css';

const Temp = () => {
  const [view, setView] = useState('registration'); // 'registration' | 'checkin' | 'profile' | 'split' | 'dashboard'
  const [refreshKey, setRefreshKey] = useState(0);

  const handleCheckInSuccess = (receipt) => {
    console.log('Check-in success receipt:', receipt);
    // Increment refresh key to trigger live queue refresh
    setRefreshKey(prev => prev + 1);
  };

  const handleRegistrationSuccess = (patient) => {
    console.log('Patient registered successfully:', patient);
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
            onClick={() => setView('checkin')}
            style={{
              background: view === 'checkin' ? '#2563eb' : '#334155',
              color: '#ffffff',
              border: 'none',
              padding: '0.4rem 0.9rem',
              borderRadius: '6px',
              fontSize: '0.8125rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Patient Check-In
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
            onClick={() => setView('split')}
            style={{
              background: view === 'split' ? '#2563eb' : '#334155',
              color: '#ffffff',
              border: 'none',
              padding: '0.4rem 0.9rem',
              borderRadius: '6px',
              fontSize: '0.8125rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Side-by-Side (Check-In + Queue)
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
            onCheckInPatient={() => setView('checkin')}
            onViewProfile={() => setView('profile')}
          />
        </main>
      )}

      {view === 'checkin' && (
        <main style={{ maxWidth: '1200px', margin: '2rem auto', padding: '0 1.5rem' }}>
          <div style={{
            background: '#ffffff',
            borderRadius: '12px',
            padding: '1.5rem',
            border: '1px solid #e2e8f0',
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
            marginBottom: '2rem'
          }}>
            <PatientCheckIn onCheckInSuccess={handleCheckInSuccess} />
          </div>

          <div style={{
            background: '#ffffff',
            borderRadius: '12px',
            padding: '1.5rem',
            border: '1px solid #e2e8f0',
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
          }}>
            <h3 style={{ margin: '0 0 1rem', fontSize: '1.125rem', color: '#1e293b' }}>
              Live Active Queue (Auto-Updates upon Check-In)
            </h3>
            <QueueDashboard key={refreshKey} />
          </div>
        </main>
      )}

      {view === 'profile' && (
        <main style={{ maxWidth: '1200px', margin: '2rem auto', padding: '0 1.5rem' }}>
          <PatientProfile />
        </main>
      )}

      {view === 'split' && (
        <main style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))',
          gap: '1.5rem',
          margin: '1.5rem',
          alignItems: 'start'
        }}>
          <div style={{
            background: '#ffffff',
            borderRadius: '12px',
            padding: '1.5rem',
            border: '1px solid #e2e8f0',
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
          }}>
            <PatientCheckIn onCheckInSuccess={handleCheckInSuccess} />
          </div>

          <div style={{
            background: '#ffffff',
            borderRadius: '12px',
            padding: '1.5rem',
            border: '1px solid #e2e8f0',
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
          }}>
            <QueueDashboard key={refreshKey} />
          </div>
        </main>
      )}

      {view === 'dashboard' && (
        <StaffDashboard />
      )}
    </div>
  );
};

export default Temp;
