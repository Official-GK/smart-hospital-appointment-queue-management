import { getAuthHeaders } from './utils/apiClient';

const API_BASE = 'http://localhost:8000/api/v1';

async function fetchWithAuth(url, options = {}) {
  const headers = getAuthHeaders(options.headers || {
    'Content-Type': 'application/json'
  });
  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'API request failed');
  }
  const json = await res.json();
  // Return just the data part if it's wrapped in APIResponse
  return json.data !== undefined ? json.data : json;
}

export async function apiLogin(userId, password) {
  const formData = new URLSearchParams();
  formData.append('username', userId);
  formData.append('password', password);

  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Login failed');
  }

  const data = await res.json();
  // Map our backend's response format to what the copied components expect
  return {
    token: data.access_token,
    user_id: data.employee_id,
    full_name: data.employee_id, // We use employee_id as full_name for now
    role: data.role,
  };
}

export async function apiLogout() {
  // We use JWT tokens, so logout is purely client-side.
  // The Sidebar component already clears localStorage, so we just return true.
  return true;
}

export async function apiGetUsers() {
  const data = await fetchWithAuth(`${API_BASE}/users`);
  return data; // Returns list of users
}

export async function apiCreateUser(userData) {
  const data = await fetchWithAuth(`${API_BASE}/users`, {
    method: 'POST',
    body: JSON.stringify(userData),
  });
  return data;
}

export async function apiDeleteUser(userId) {
  const data = await fetchWithAuth(`${API_BASE}/users/${userId}`, {
    method: 'DELETE',
  });
  return data;
}

export async function apiGetAuditLogs(params = {}) {
  const query = new URLSearchParams(params).toString();
  const data = await fetchWithAuth(`${API_BASE}/audit/logs${query ? `?${query}` : ''}`);
  return data; // Returns array of logs
}

export async function apiExportAuditLogsUrl(params = {}) {
  // We can't use fetchWithAuth easily for direct file downloads via <a> tags because of the Authorization header.
  // We will fetch the blob and trigger download programmatically.
  const query = new URLSearchParams(params).toString();
  const url = `${API_BASE}/audit/logs/export${query ? `?${query}` : ''}`;
  const headers = getAuthHeaders();
  
  const res = await fetch(url, { headers });
  if (!res.ok) throw new Error('Export failed');
  
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}
