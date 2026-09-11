const API_URL = 'http://localhost:8000/api';

export const fetchAppointments = async (filters = {}) => {
  // Map frontend camelCase filter keys to backend snake_case keys and ignore "All" or empty values
  const mappedFilters = {};
  for (const [key, value] of Object.entries(filters)) {
    if (value != null && value !== '' && value !== 'All') {
      if (key === 'departmentId') mappedFilters['department_id'] = value;
      else if (key === 'doctorId') mappedFilters['doctor_id'] = value;
      else mappedFilters[key] = value;
    }
  }
  const queryParams = new URLSearchParams(mappedFilters).toString();
  const url = queryParams ? `${API_URL}/appointments?${queryParams}` : `${API_URL}/appointments`;
  const response = await fetch(url);
  const result = await response.json();
  if (!result.success) throw new Error(result.message);
  return result.data;
};

export const fetchFilterMetadata = async () => {
  const response = await fetch(`${API_URL}/appointments/metadata/filters`);
  const result = await response.json();
  if (!result.success) throw new Error(result.message);
  return result.data;
};

export const transitionAppointmentStatus = async (appointmentId, new_status) => {
  // The backend expects { new_status: "Checked-In" } inside the body request
  const body = typeof new_status === 'object' ? new_status : { new_status };
  const response = await fetch(`${API_URL}/appointments/${appointmentId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  const result = await response.json();
  if (!result.success) throw new Error(result.message);
  return result.data;
};

export const cancelAppointment = async (appointmentId, request) => {
  const response = await fetch(`${API_URL}/appointments/${appointmentId}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });
  const result = await response.json();
  if (!result.success) throw new Error(result.message);
  return result.data;
};

export const fetchSlotInventory = async (filters = {}) => {
  const cleanFilters = Object.fromEntries(Object.entries(filters).filter(([_, v]) => v != null && v !== ''));
  const queryParams = new URLSearchParams(cleanFilters).toString();
  const url = queryParams ? `${API_URL}/appointments/inventory/slots?${queryParams}` : `${API_URL}/appointments/inventory/slots`;
  const response = await fetch(url);
  const result = await response.json();
  if (!result.success) throw new Error(result.message);
  return result.data;
};

export const fetchAppointmentStatistics = async () => {
  const response = await fetch(`${API_URL}/appointments/statistics/summary`);
  const result = await response.json();
  if (!result.success) throw new Error(result.message);
  return result.data;
};

export const rescheduleAppointment = async (appointmentId, request) => {
  const response = await fetch(`${API_URL}/appointments/${appointmentId}/reschedule`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });
  const result = await response.json();
  if (!result.success) throw new Error(result.message);
  return result.data;
};

export const createAppointment = async (payload) => {
  const response = await fetch(`${API_URL}/appointments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const result = await response.json();
  if (!result.success) throw new Error(result.message);
  return result.data;
};

export const appointmentService = {
  getMetadata: fetchFilterMetadata,
  createAppointment,
  transitionStatus: transitionAppointmentStatus,
  fetchSlotInventory
};
