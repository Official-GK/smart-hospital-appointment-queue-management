import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * ProtectedRoute — wraps pages that require authentication.
 * Redirects to /login if no valid session token is found.
 */
export default function ProtectedRoute({ children, allowedRoles }) {
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('hqms_token') || localStorage.getItem('access_token');
    if (!token) {
      navigate('/admin/login', { replace: true });
      return;
    }

    if (allowedRoles && allowedRoles.length > 0) {
      // Allow if role is stored under hqms_user or user_role
      let userRole = localStorage.getItem('user_role');
      if (!userRole) {
        try {
          const userStr = localStorage.getItem('hqms_user');
          if (userStr) {
            userRole = JSON.parse(userStr).role;
          }
        } catch (e) {}
      }
      
      if (!allowedRoles.includes(userRole) && !allowedRoles.includes(userRole?.toLowerCase())) {
        navigate('/admin/login', { replace: true });
      }
    }
  }, [navigate, allowedRoles]);

  const token = localStorage.getItem('hqms_token') || localStorage.getItem('access_token');
  if (!token) return null;

  return children;
}
