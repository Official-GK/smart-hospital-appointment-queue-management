import React, { useState } from 'react';
import StaffLayout from '../layouts/StaffLayout';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import AppointmentManagement from '../features/appointments/components/AppointmentManagement';
import QueueDashboard from '../features/queue/components/QueueDashboard';
import TokenGeneration from '../features/appointments/components/TokenGeneration';
import PatientManagement from '../features/patients/components/PatientManagement';

const StaffDashboard = () => {
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleGenerate = () => setRefreshTrigger(prev => prev + 1);

  return (
    <StaffLayout activeTab={activeTab} onTabChange={setActiveTab}>
      
      {activeTab === 'Dashboard' && (
        <>
          <h1 className="page-title">Staff Dashboard</h1>
          <div style={{ marginBottom: '2rem', width: '100%' }}>
            <section className="dashboard-section" style={{ width: '100%' }}>
              <TokenGeneration onGenerate={handleGenerate} />
            </section>
          </div>
          <section style={{ marginBottom: '3rem', width: '100%' }}>
            <AppointmentManagement refreshTrigger={refreshTrigger} />
          </section>
        </>
      )}

      {activeTab === 'Queue' && (
        <section style={{ width: '100%' }}>
          <QueueDashboard />
        </section>
      )}

      {activeTab === 'Patients' && (
        <section style={{ width: '100%' }}>
          <PatientManagement />
        </section>
      )}

    </StaffLayout>
  );
};

export default StaffDashboard;
