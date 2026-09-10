const API_URL = 'http://localhost:8000/api';

export const appointmentService = {
  getMetadata: async () => {
    const response = await fetch(`${API_URL}/appointments/metadata/filters`);
    const result = await response.json();
    if (!result.success) throw new Error(result.message);
    return result.data;
  },

  createAppointment: async (payload) => {
    const response = await fetch(`${API_URL}/appointments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!result.success) throw new Error(result.message);
    return result.data;
  },

  transitionStatus: async (appointmentId, newStatus) => {
    const response = await fetch(`${API_URL}/appointments/${appointmentId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_status: newStatus })
    });
    const result = await response.json();
    if (!result.success) throw new Error(result.message);
    return result.data;
  }
};
