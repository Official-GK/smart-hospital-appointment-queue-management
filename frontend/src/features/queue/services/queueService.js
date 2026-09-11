const API_URL = 'http://localhost:8000/api';

export const queueService = {
  getLiveQueue: async (departmentId = null, doctorId = null) => {
    let url = `${API_URL}/queue/live`;
    const params = new URLSearchParams();
    if (departmentId) params.append('department_id', departmentId);
    if (doctorId) params.append('doctor_id', doctorId);
    
    if (params.toString()) {
      url += `?${params.toString()}`;
    }

    const response = await fetch(url);
    const result = await response.json();
    if (!result.success) throw new Error(result.message);
    return result.data;
  },

  updateStatus: async (appointmentId, status) => {
    const response = await fetch(`${API_URL}/queue/${appointmentId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });
    const result = await response.json();
    if (!result.success) throw new Error(result.message);
    return result.data;
  }
};
