const API_BASE_URL = 'http://localhost:8000/api';

/**
 * Helper to perform fetch with JSON handling
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const res = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data?.message || data?.error?.detail || `HTTP ${res.status}`);
    }
    return data;
  } catch (err) {
    console.warn(`Backend API request to ${url} failed:`, err.message);
    throw err;
  }
}

export async function fetchAppointments(filters = {}) {
  const params = new URLSearchParams();
  if (filters.status && filters.status !== 'All') params.append('status', filters.status);
  if (filters.departmentId && filters.departmentId !== 'All') params.append('department_id', filters.departmentId);
  if (filters.doctorId && filters.doctorId !== 'All') params.append('doctor_id', filters.doctorId);
  if (filters.date) params.append('date', filters.date);

  const query = params.toString() ? `?${params.toString()}` : '';
  const response = await request(`/appointments${query}`);
  return response.data;
}

export async function fetchFilterMetadata() {
  const response = await request('/appointments/metadata/filters');
  return response.data;
}

export async function transitionAppointmentStatus(appointmentId, newStatus, notes = '', changedBy = 'Staff Member') {
  const response = await request(`/appointments/${appointmentId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({
      new_status: newStatus,
      notes: notes,
      changed_by: changedBy,
    }),
  });
  return response.data;
}

export async function fetchAppointmentHistory(appointmentId) {
  const response = await request(`/appointments/${appointmentId}/history`);
  return response.data;
}

export async function createAppointment(payload) {
  const response = await request('/appointments', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return response.data;
}

export async function cancelAppointment(appointmentId, { reason, staffId, notes = '' }) {
  const response = await request(`/appointments/${appointmentId}/cancel`, {
    method: 'POST',
    body: JSON.stringify({
      reason,
      staff_id: staffId,
      notes,
    }),
  });
  return response.data;
}

export async function fetchSlotInventory(doctorId, date) {
  const params = new URLSearchParams();
  if (doctorId && doctorId !== 'All') params.append('doctor_id', doctorId);
  if (date) params.append('date', date);
  const query = params.toString() ? `?${params.toString()}` : '';
  const response = await request(`/appointments/inventory/slots${query}`);
  return response.data;
}

export async function fetchAppointmentStatistics() {
  const response = await request('/appointments/statistics/summary');
  return response.data;
}

export async function rescheduleAppointment(appointmentId, { staffId, doctorId, appointmentDate, appointmentTime, reason = 'Patient Request', notes = '' }) {
  const response = await request(`/appointments/${appointmentId}/reschedule`, {
    method: 'PATCH',
    body: JSON.stringify({
      staff_id: staffId,
      doctor_id: doctorId,
      appointment_date: appointmentDate,
      appointment_time: appointmentTime,
      reason,
      notes,
    }),
  });
  return response.data;
}

export async function fetchLiveQueue() {
  const response = await request('/queue/live');
  return response.data;
}
