const API_BASE_URL = 'http://localhost:8000/api';

/**
 * Service handling patient check-in, arrival recording, and queue placement.
 * Supports direct patient router endpoints with graceful fallback to appointment/queue APIs.
 */
export const patientService = {
  /**
   * Retrieves appointments scheduled for today that are eligible for check-in.
   */
  async getEligibleCheckIns() {
    try {
      // 1. Try dedicated patient endpoint first
      const res = await fetch(`${API_BASE_URL}/patients/check-in/eligible`);
      if (res.ok) {
        const json = await res.json();
        return json.data || [];
      }
    } catch (e) {
      // Fallback
    }

    // Fallback: Fetch from appointments API where status = Scheduled
    try {
      const res = await fetch(`${API_BASE_URL}/appointments?status=Scheduled`);
      if (!res.ok) throw new Error('Failed to fetch eligible appointments');
      const json = await res.json();
      const appointments = json.data || [];

      return appointments.map(apt => ({
        appointment_id: apt.appointment_id,
        patient_id: apt.patient_id,
        patient_name: apt.patient_name,
        phone: apt.phone || null,
        appointment_date: apt.appointment_date,
        appointment_time: apt.appointment_time,
        doctor_id: apt.doctor_id,
        doctor_name: apt.doctor_name,
        department_id: apt.department_id,
        department_name: apt.department_name,
        priority: apt.priority || 'Normal',
        is_walk_in: Boolean(apt.is_walk_in),
        status: apt.status,
        can_check_in: apt.status === 'Scheduled',
      }));
    } catch (err) {
      console.error('Error fetching eligible appointments:', err);
      throw err;
    }
  },

  /**
   * Executes patient check-in for an appointment or walk-in visit.
   * Records arrival timestamp and enqueues into active queue.
   */
  async checkInPatient(payload) {
    const arrivalTime = new Date().toISOString();

    // 1. Try dedicated patient check-in endpoint first
    try {
      const res = await fetch(`${API_BASE_URL}/patients/check-in`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...payload,
          arrival_time: arrivalTime,
        }),
      });

      if (res.ok) {
        const json = await res.json();
        return json.data;
      }
    } catch (e) {
      // Fallback to existing endpoints
    }

    // 2. Fallback: Check-in for an existing appointment
    if (payload.appointment_id && !payload.is_walk_in) {
      const res = await fetch(`${API_BASE_URL}/appointments/${payload.appointment_id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          new_status: 'Checked-In',
          changed_by: payload.checked_in_by || 'Front-Desk Staff',
          notes: payload.notes || `Arrived at ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.message || 'Failed to check in appointment');
      }

      const json = await res.json();
      const updated = json.data;

      // Fetch live queue to get current position
      let queuePosition = 1;
      let estimatedWait = 15;
      try {
        const qRes = await fetch(`${API_BASE_URL}/queue/live?doctor_id=${updated.doctor_id}`);
        if (qRes.ok) {
          const qJson = await qRes.json();
          const list = qJson.data || [];
          const idx = list.findIndex(item => item.appointment_id === updated.appointment_id);
          if (idx !== -1) {
            queuePosition = idx + 1;
            estimatedWait = list[idx].estimated_wait_minutes || estimatedWait;
          } else {
            queuePosition = list.length || 1;
          }
        }
      } catch (qErr) {
        console.warn('Could not fetch queue position', qErr);
      }

      return {
        check_in_id: `CHK-${Date.now().toString(36).toUpperCase()}`,
        patient_id: updated.patient_id,
        patient_name: updated.patient_name,
        appointment_id: updated.appointment_id,
        status: 'Checked-In',
        arrival_time: arrivalTime,
        token_id: updated.token_id,
        token_number: updated.token_number,
        queue_position: queuePosition,
        estimated_wait_minutes: estimatedWait,
        doctor_id: updated.doctor_id,
        doctor_name: updated.doctor_name,
        department_id: updated.department_id,
        department_name: updated.department_name,
        priority: updated.priority,
        is_walk_in: false,
        notes: payload.notes,
      };
    }

    // 3. Fallback: Walk-in appointment creation and check-in
    const todayStr = new Date().toISOString().split('T')[0];
    const timeStr = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });

    const createRes = await fetch(`${API_BASE_URL}/appointments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_name: payload.patient_name || 'Walk-in Patient',
        doctor_id: payload.doctor_id || 'DOC-001',
        department_id: payload.department_id || 'DEP-GEN',
        appointment_date: todayStr,
        appointment_time: timeStr,
        priority: payload.priority || 'Normal',
        is_walk_in: true,
        notes: payload.notes || 'Walk-in visit',
        staff_id: payload.checked_in_by || 'Front-Desk Staff',
      }),
    });

    if (!createRes.ok) {
      const errJson = await createRes.json().catch(() => ({}));
      throw new Error(errJson.message || 'Failed to create walk-in appointment');
    }

    const createdData = (await createRes.json()).data;

    // Transition created walk-in to Checked-In
    const checkInRes = await fetch(`${API_BASE_URL}/appointments/${createdData.appointment_id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        new_status: 'Checked-In',
        changed_by: payload.checked_in_by || 'Front-Desk Staff',
        notes: `Walk-in arrival check-in at ${timeStr}`,
      }),
    });

    if (!checkInRes.ok) {
      const errJson = await checkInRes.json().catch(() => ({}));
      throw new Error(errJson.message || 'Failed to check in walk-in appointment');
    }

    const updatedApt = (await checkInRes.json()).data;

    return {
      check_in_id: `CHK-${Date.now().toString(36).toUpperCase()}`,
      patient_id: updatedApt.patient_id,
      patient_name: updatedApt.patient_name,
      appointment_id: updatedApt.appointment_id,
      status: 'Checked-In',
      arrival_time: arrivalTime,
      token_id: updatedApt.token_id,
      token_number: updatedApt.token_number,
      queue_position: 1,
      estimated_wait_minutes: 15,
      doctor_id: updatedApt.doctor_id,
      doctor_name: updatedApt.doctor_name,
      department_id: updatedApt.department_id,
      department_name: updatedApt.department_name,
      priority: payload.priority || 'Normal',
      is_walk_in: true,
      notes: payload.notes,
    };
  },

  /**
   * Search patients by name, ID, or phone.
   */
  async searchPatients(query = '') {
    try {
      const res = await fetch(`${API_BASE_URL}/patients?query=${encodeURIComponent(query)}`);
      if (res.ok) {
        const json = await res.json();
        return json.data || [];
      }
    } catch (e) {
      // Return empty if not available
    }
    return [];
  },

  /**
   * Fetch active queue for real-time verification.
   */
  async getLiveQueue(departmentId, doctorId) {
    let url = `${API_BASE_URL}/queue/live`;
    const params = new URLSearchParams();
    if (departmentId) params.append('department_id', departmentId);
    if (doctorId) params.append('doctor_id', doctorId);
    const qs = params.toString();
    if (qs) url += `?${qs}`;

    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch live queue');
    const json = await res.json();
    return json.data || [];
  },
};
