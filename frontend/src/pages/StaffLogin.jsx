import React, { useState } from 'react';
import Input from '../components/common/Input';
import './StaffLogin.css';

const StaffLogin = ({ onLogin }) => {
  const [credentials, setCredentials] = useState({ staffId: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setCredentials({ ...credentials, [e.target.name]: e.target.value });
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!credentials.staffId || !credentials.password) {
      setError('Please enter both Staff ID and Password.');
      return;
    }
    setError('');
    setLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append('username', credentials.staffId);
      formData.append('password', credentials.password);

      const response = await fetch('http://localhost:8000/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Invalid Staff ID or Password.');
      }

      const data = await response.json();
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('user_role', data.role);
      localStorage.setItem('employee_id', data.employee_id);
      
      console.log('Login successful for:', data.employee_id);
      if (onLogin) onLogin();
    } catch (err) {
      setError(err.message || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      
      {/* Left side: Premium Branding & Gradient Hero */}
      <div className="login-left">
        <div className="login-brand-logo">
          <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15h-2v-4H5v-2h4V7h2v4h4v2h-4v4z"/>
          </svg>
          <span>Smart Hospital</span>
        </div>
        
        <h1 className="login-hero-text">
          Modernizing<br />
          Healthcare<br />
          Management.
        </h1>
        <p className="login-sub-text">
          Welcome to the Smart Hospital Staff Portal. Streamline your appointments, manage the live queue, and monitor patient flows all in one unified dashboard.
        </p>
      </div>

      {/* Right side: Clean, minimalist login form */}
      <div className="login-right">
        <div className="login-form-wrapper">
          
          <div className="login-header">
            <h2>Welcome back</h2>
            <p>Please enter your credentials to access the portal.</p>
          </div>

          {error && (
            <div className="login-error-alert">
              <svg style={{width:'20px', height:'20px'}} fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd"></path></svg>
              {error}
            </div>
          )}
          
          <form onSubmit={handleLogin}>
            <Input 
              label="Staff ID or Email" 
              name="staffId" 
              placeholder="e.g. STAFF-001 or admin@hospital.com" 
              value={credentials.staffId} 
              onChange={handleChange} 
              required
            />
            
            <Input 
              label="Password" 
              type="password" 
              name="password" 
              placeholder="••••••••" 
              value={credentials.password} 
              onChange={handleChange} 
              required
            />
            
            <button 
              type="submit" 
              className="login-btn"
              disabled={loading}
            >
              {loading ? (
                <>
                  <svg style={{animation: 'rotateGradient 1s linear infinite', width:'20px', height:'20px'}} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" strokeDasharray="32" strokeLinecap="round" opacity="0.5"></circle></svg>
                  Authenticating...
                </>
              ) : 'Sign In'}
            </button>
          </form>
          
          <div className="login-footer-links">
            <a href="#">Forgot your password?</a>
          </div>
        </div>
      </div>
      
    </div>
  );
};

export default StaffLogin;
