import React from 'react';
import PropTypes from 'prop-types';

const StaffLayout = ({ children, activeTab = 'Dashboard', onTabChange = () => {} }) => {
  return (
    <div className="dashboard-layout">
      <header className="dashboard-header">
        <div className="header-brand">Smart Hospital Admin</div>
        <div className="header-user" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span>Staff Member</span>
          <button 
            onClick={() => window.location.href = '/'}
            style={{ 
            background: '#f8fafc', 
            border: '1px solid #cbd5e1', 
            padding: '0.375rem 1rem', 
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '0.875rem',
            fontWeight: '500',
            color: '#475569',
            transition: 'all 0.2s',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
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
