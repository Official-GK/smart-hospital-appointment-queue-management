const API_BASE_URL = 'http://localhost:8000/api';

const DEMO_PATIENT_RECORDS = [
  { patient_id: 'PAT-001', patient_name: 'James Wilson', first_name: 'James', last_name: 'Wilson', phone: '+1-555-0101', address: '124 Oak Street, Springfield', date_of_birth: '1985-04-12', age: 41, gender: 'Male', status: 'Registered' },
  { patient_id: 'PAT-002', patient_name: 'Michael Chen', first_name: 'Michael', last_name: 'Chen', phone: '+1-555-0102', address: '452 Elm Street, Springfield', date_of_birth: '1990-08-23', age: 36, gender: 'Male', status: 'Checked-In' },
  { patient_id: 'PAT-003', patient_name: 'Elena Rodriguez', first_name: 'Elena', last_name: 'Rodriguez', phone: '+1-555-0103', address: '789 Pine Road, Springfield', date_of_birth: '1978-11-05', age: 47, gender: 'Female', status: 'In-Consultation' },
  { patient_id: 'PAT-004', patient_name: 'Robert Taylor', first_name: 'Robert', last_name: 'Taylor', phone: '+1-555-0104', address: '321 Maple Avenue, Springfield', date_of_birth: '1965-02-17', age: 61, gender: 'Male', status: 'Completed' },
  { patient_id: 'PAT-005', patient_name: 'Sophia Martinez', first_name: 'Sophia', last_name: 'Martinez', phone: '+1-555-0105', address: '654 Cedar Blvd, Springfield', date_of_birth: '1995-06-30', age: 31, gender: 'Female', status: 'Registered' },
  { patient_id: 'PAT-006', patient_name: 'David Kim', first_name: 'David', last_name: 'Kim', phone: '+1-555-0106', address: '987 Birch Lane, Springfield', date_of_birth: '1988-09-14', age: 37, gender: 'Male', status: 'Registered' },
  { patient_id: 'PAT-007', patient_name: 'Emily Watson', first_name: 'Emily', last_name: 'Watson', phone: '+1-555-0107', address: '150 Walnut Court, Springfield', date_of_birth: '1992-03-18', age: 34, gender: 'Female', status: 'Registered' },
  { patient_id: 'PAT-008', patient_name: 'Alexander Wright', first_name: 'Alexander', last_name: 'Wright', phone: '+1-555-0108', address: '882 Cypress Drive, Springfield', date_of_birth: '1983-12-02', age: 42, gender: 'Male', status: 'Registered' },
];

const localRegisteredPatients = new Map();

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
        if (json.data && json.data.length > 0) {
          return json.data;
        }
      }
    } catch (e) {
      // Fallback
    }

    // Fallback: search across local registered cache and demo patients
    const all = [
      ...Array.from(localRegisteredPatients.values()),
      ...DEMO_PATIENT_RECORDS,
    ];
    const qLower = (query || '').toLowerCase().trim();
    if (!qLower) return all;
    return all.filter(
      p => (p.patient_name || '').toLowerCase().includes(qLower) ||
           (p.patient_id || '').toLowerCase().includes(qLower) ||
           (p.phone || '').includes(qLower)
    );
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

  /**
   * Retrieve full patient profile with demographics, active appointments,
   * visit history with operational timestamps, token history, and audit trail.
   */
  async getPatientProfile(patientId, maskSensitive = false, role = 'Staff') {
    try {
      const res = await fetch(
        `${API_BASE_URL}/patients/${patientId}/profile?mask_sensitive=${Boolean(maskSensitive)}`,
        {
          headers: { 'X-User-Role': role },
        }
      );
      if (res.ok) {
        const json = await res.json();
        return json.data;
      }
    } catch (e) {
      // Fallback
    }

    // Fallback: Assemble profile from demo/local patient and appointments
    try {
      const cached = localRegisteredPatients.get(patientId) || DEMO_PATIENT_RECORDS.find(p => p.patient_id === patientId);

      const aptsRes = await fetch(`${API_BASE_URL}/appointments`).catch(() => null);
      const allApts = (aptsRes && aptsRes.ok) ? (await aptsRes.json()).data || [] : [];
      const patientApts = allApts.filter(a => a.patient_id === patientId);

      const activeStatuses = ['Scheduled', 'Checked-In', 'In-Consultation'];
      const active = [];
      const visits = [];
      const tokens = [];

      patientApts.forEach(apt => {
        const item = {
          appointment_id: apt.appointment_id,
          appointment_date: apt.appointment_date,
          appointment_time: apt.appointment_time,
          doctor_id: apt.doctor_id,
          doctor_name: apt.doctor_name,
          department_id: apt.department_id,
          department_name: apt.department_name,
          status: apt.status,
          priority: apt.priority || 'Normal',
          is_walk_in: Boolean(apt.is_walk_in),
          booking_time: apt.timestamps?.created_at || null,
          check_in_time: apt.timestamps?.check_in_time || null,
          queue_entry_time: apt.timestamps?.queue_entry_time || null,
          consultation_start_time: apt.timestamps?.consultation_start_time || null,
          completion_time: apt.timestamps?.consultation_end_time || null,
          notes: apt.notes || null,
        };

        if (activeStatuses.includes(apt.status)) {
          active.push(item);
        } else {
          visits.push(item);
        }

        if (apt.token_number) {
          tokens.push({
            token_id: apt.token_id || `TOK-${apt.token_number}`,
            token_number: apt.token_number,
            appointment_id: apt.appointment_id,
            doctor_id: apt.doctor_id,
            doctor_name: apt.doctor_name,
            department_id: apt.department_id,
            department_name: apt.department_name,
            priority: apt.priority || 'Normal',
            status: apt.status,
            created_at: apt.timestamps?.queue_entry_time || apt.timestamps?.created_at,
          });
        }
      });

      const sampleName = cached?.patient_name || (cached ? `${cached.first_name || ''} ${cached.last_name || ''}`.trim() : null) || patientApts[0]?.patient_name || 'James Wilson';
      const sampleFirst = cached?.first_name || sampleName.split(' ')[0] || 'James';
      const sampleLast = cached?.last_name || sampleName.split(' ')[1] || 'Wilson';
      let phone = cached?.phone || '+1-555-0101';
      let address = cached?.address || '124 Oak Street, Springfield';

      if (maskSensitive) {
        phone = phone.length >= 7 ? `${phone.slice(0, 4)}***-**${phone.slice(-4)}` : '***-***-****';
        address = '*** Oak Street, Springfield';
      }

      return {
        patient_id: patientId,
        first_name: sampleFirst,
        last_name: sampleLast,
        patient_name: sampleName,
        date_of_birth: cached?.date_of_birth || '1985-04-12',
        age: cached?.age || 41,
        gender: cached?.gender || 'Male',
        phone,
        address,
        status: cached?.status || 'Registered',
        created_at: cached?.created_at || '2026-08-01T09:00:00Z',
        last_arrival_time: cached?.last_arrival_time || null,
        is_masked: Boolean(maskSensitive),
        active_appointments: active,
        visit_history: visits,
        token_history: tokens,
        audit_trail: [],
      };
    } catch (err) {
      console.error('Error assembling fallback profile:', err);
      throw err;
    }
  },

  /**
   * Update demographic and contact information with audit logging.
   */
  async updatePatientProfile(patientId, updatePayload) {
    try {
      const res = await fetch(`${API_BASE_URL}/patients/${patientId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatePayload),
      });

      if (res.ok) {
        const json = await res.json();
        return json.data;
      }
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.message || 'Failed to update patient profile');
    } catch (err) {
      console.error('Error updating patient profile:', err);
      throw err;
    }
  },

  /**
   * Retrieve demographic update audit trail.
   */
  async getPatientAuditTrail(patientId) {
    try {
      const res = await fetch(`${API_BASE_URL}/patients/${patientId}/audit`);
      if (res.ok) {
        const json = await res.json();
        return json.data || [];
      }
    } catch (err) {
      console.error('Error fetching audit trail:', err);
    }
    return [];
  },

  /**
   * Check for duplicate patient record by contact number or identifier.
   */
  async checkDuplicate({ contactNumber, identifier }) {
    const params = new URLSearchParams();
    if (contactNumber) params.append('contact_number', contactNumber);
    if (identifier) params.append('identifier', identifier);
    const qs = params.toString();
    if (!qs) return { is_duplicate: false, message: 'No search params' };

    try {
      const res = await fetch(`${API_BASE_URL}/patients/check-duplicate?${qs}`);
      if (res.ok) {
        const json = await res.json();
        return json.data;
      }
    } catch (e) {
      // Fallback
    }

    // Fallback local check
    try {
      const all = await this.searchPatients('');
      const cleanPhone = (contactNumber || '').replace(/\D/g, '');
      const cleanId = (identifier || '').trim().toUpperCase();

      for (const p of all) {
        if (cleanId && p.patient_id.toUpperCase() === cleanId) {
          return {
            is_duplicate: true,
            existing_patient_id: p.patient_id,
            existing_patient_name: p.patient_name,
            matched_field: 'identifier',
            message: `Identifier is already registered to ${p.patient_name} (${p.patient_id})`,
          };
        }
        const pDigits = (p.phone || '').replace(/\D/g, '');
        if (cleanPhone && cleanPhone.length >= 7 && pDigits === cleanPhone) {
          return {
            is_duplicate: true,
            existing_patient_id: p.patient_id,
            existing_patient_name: p.patient_name,
            matched_field: 'contact_number',
            message: `Contact number is already registered to ${p.patient_name} (${p.patient_id})`,
          };
        }
      }
    } catch (err) {
      console.warn('Fallback duplicate check error:', err);
    }

    return { is_duplicate: false, message: 'No duplicate patient record found' };
  },

  /**
   * Register a new patient.
   */
  async registerPatient(payload) {
    try {
      const res = await fetch(`${API_BASE_URL}/patients`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const json = await res.json();
        if (json.data && json.data.patient_id) {
          localRegisteredPatients.set(json.data.patient_id, json.data);
        }
        return json.data;
      }

      if (res.status === 409) {
        const errJson = await res.json().catch(() => ({}));
        const errorMsg = errJson.message || errJson.detail || (errJson.error && errJson.error.detail) || 'Patient already registered with this contact number';
        throw new Error(errorMsg);
      }
    } catch (err) {
      if (err.message && (err.message.includes('already registered') || err.message.includes('already exists') || err.message.includes('Duplicate'))) {
        throw err;
      }
      console.warn('Backend /api/patients endpoint unavailable, using local patient registration fallback');
    }

    // Standalone / fallback patient registration
    const fullName = payload.patient_name || `${payload.first_name || ''} ${payload.last_name || ''}`.trim() || 'Patient';
    const patientId = `PAT-${Math.floor(100 + Math.random() * 900)}`;
    const phone = payload.phone || payload.contact_number || '+1-555-0199';

    const fallbackPatient = {
      patient_id: patientId,
      first_name: payload.first_name || fullName.split(' ')[0],
      last_name: payload.last_name || fullName.split(' ')[1] || '',
      patient_name: fullName,
      age: payload.age || 30,
      date_of_birth: payload.date_of_birth || '1995-01-01',
      gender: payload.gender || 'Other',
      phone: phone,
      address: payload.address || null,
      status: 'Registered',
      created_at: new Date().toISOString(),
    };
    localRegisteredPatients.set(patientId, fallbackPatient);
    return fallbackPatient;
  },
};

