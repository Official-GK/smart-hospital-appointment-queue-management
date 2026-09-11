import React from 'react';
import PropTypes from 'prop-types';

const StaffLayout = ({ children, activeTab = 'Dashboard', onTabChange = () => {} }) => {
  return (
    <div className="dashboard-layout">
      <header className="dashboard-header">
        <div className="header-brand">Smart Hospital Admin</div>
        <div className="header-user" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span>Staff Member</span>
          <button style={{ 
            background: 'none', 
            border: '1px solid var(--border-color)', 
            padding: '0.25rem 0.75rem', 
            borderRadius: 'var(--radius-md)',
            cursor: 'pointer',
            fontSize: '0.875rem',
            color: 'var(--text-muted)'
          }}>
            Logout
          </button>
        </div>
      </header>
      
      <div className="dashboard-body">
        <aside className="dashboard-sidebar">
          <nav>
            <ul>
              <li className={activeTab === 'Dashboard' ? 'active' : ''} onClick={() => onTabChange('Dashboard')} style={{ cursor: 'pointer' }}>Dashboard</li>
              <li className={activeTab === 'Patients' ? 'active' : ''} onClick={() => onTabChange('Patients')} style={{ cursor: 'pointer' }}>Patients</li>
              <li className={activeTab === 'Queue' ? 'active' : ''} onClick={() => onTabChange('Queue')} style={{ cursor: 'pointer' }}>Queue</li>
            </ul>
          </nav>
        </aside>
        
        <main className="dashboard-main">
          {children}
        </main>
      </div>
    </div>
  );
};

StaffLayout.propTypes = {
  children: PropTypes.node.isRequired,
  activeTab: PropTypes.string,
  onTabChange: PropTypes.func,
};

export default StaffLayout;
