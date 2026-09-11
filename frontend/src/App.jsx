import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import StaffDashboard from './pages/StaffDashboard';
import StaffLogin from './pages/StaffLogin';
import AdminLogin from './pages/AdminLogin';
import AdminDashboard from './pages/AdminDashboard';
import AdminUsers from './pages/AdminUsers';
import AdminAuditLogs from './pages/AdminAuditLogs';
import ProtectedRoute from './components/ProtectedRoute';
import './App.css';

// Legacy Staff Login wrapper to maintain exact existing behavior without breaking it
function LegacyStaffApp() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  return (
    <>
      {!isLoggedIn ? (
        <StaffLogin onLogin={() => setIsLoggedIn(true)} />
      ) : (
        <StaffDashboard />
      )}
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Staff Routes (Legacy root route) */}
        <Route path="/" element={<LegacyStaffApp />} />

        {/* Admin Routes */}
        <Route path="/admin/login" element={<AdminLogin />} />
        
        <Route
          path="/admin/dashboard"
          element={
            <ProtectedRoute allowedRoles={['admin', 'Admin']}>
              <AdminDashboard />
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/admin/users"
          element={
            <ProtectedRoute allowedRoles={['admin', 'Admin']}>
              <AdminUsers />
            </ProtectedRoute>
          }
        />

        <Route
          path="/admin/audit-logs"
          element={
            <ProtectedRoute allowedRoles={['admin', 'Admin']}>
              <AdminAuditLogs />
            </ProtectedRoute>
          }
        />
        
        {/* Fallback to Staff Login for unknown routes */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
