import React, { useState } from 'react';
import StaffLayout from '../layouts/StaffLayout';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import AppointmentManagement from '../features/appointments/components/AppointmentManagement';
import QueueDashboard from '../features/queue/components/QueueDashboard';
import TokenGeneration from '../features/appointments/components/TokenGeneration';

const StaffDashboard = () => {
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleGenerate = () => setRefreshTrigger(prev => prev + 1);

  return (
    <StaffLayout activeTab={activeTab} onTabChange={setActiveTab}>
      
      {activeTab === 'Dashboard' && (
        <>
          <h1 className="page-title">Staff Dashboard</h1>
          <div className="dashboard-grid" style={{ marginBottom: '2rem' }}>
            <section className="dashboard-section">
              <TokenGeneration onGenerate={handleGenerate} />
            </section>
            
            {/* Patient Section Placeholder */}
            <section className="dashboard-section">
              <Card title="Patient Management">
                <p className="placeholder-text">Patient feature components will be integrated here.</p>
                <div className="placeholder-actions">
                  <Button variant="primary">Register Patient</Button>
                </div>
              </Card>
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
        <div>
          <h1 className="page-title">Patient Management</h1>
          <p>Patient management features coming soon.</p>
        </div>
      )}

    </StaffLayout>
  );
};

export default StaffDashboard;
