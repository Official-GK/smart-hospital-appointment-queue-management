import React from 'react';
import StaffLayout from '../layouts/StaffLayout';
import Card from '../components/common/Card';
import Button from '../components/common/Button';

const StaffDashboard = () => {
  return (
    <StaffLayout>
      <h1 className="page-title">Staff Dashboard</h1>
      
      <div className="dashboard-grid">
        {/* Patient Section Placeholder */}
        <section className="dashboard-section">
          <Card title="Patient Management">
            <p className="placeholder-text">Patient feature components will be integrated here.</p>
            <div className="placeholder-actions">
              <Button variant="primary">Register Patient</Button>
            </div>
          </Card>
        </section>

        {/* Appointment Section Placeholder */}
        <section className="dashboard-section">
          <Card title="Appointment Management">
            <p className="placeholder-text">Appointment feature components will be integrated here.</p>
            <div className="placeholder-actions">
              <Button variant="primary">Book Appointment</Button>
            </div>
          </Card>
        </section>

        {/* Queue Section Placeholder */}
        <section className="dashboard-section">
          <Card title="Queue Management">
            <p className="placeholder-text">Queue feature components will be integrated here.</p>
            <div className="placeholder-actions">
              <Button variant="primary">Manage Queue</Button>
            </div>
          </Card>
        </section>
      </div>
    </StaffLayout>
  );
};

export default StaffDashboard;
