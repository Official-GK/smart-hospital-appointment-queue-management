import React, { useState, useEffect } from 'react';
import { appointmentService } from '../services/appointmentService';

const TokenGeneration = ({ onGenerate }) => {
  const [patientId, setPatientId] = useState('');
  const [departmentId, setDepartmentId] = useState('');
  const [doctorId, setDoctorId] = useState('');
  const [priority, setPriority] = useState('Normal');
  const [notes, setNotes] = useState('');
  const [metadata, setMetadata] = useState(null);
  const [error, setError] = useState('');
  const [generatedTokenInfo, setGeneratedTokenInfo] = useState(null);

  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const data = await appointmentService.getMetadata();
        setMetadata(data);
        if (data.departments.length > 0) setDepartmentId(data.departments[0].department_id);
        if (data.doctors.length > 0) setDoctorId(data.doctors[0].doctor_id);
      } catch (err) {
        setError(err.message);
      }
    };
    fetchMetadata();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!patientId.trim() || !departmentId || !doctorId) return;
    setError('');

    try {
      // 1. Create a Walk-in Appointment for today
      const now = new Date();
      const getLocalYYYYMMDD = (d) => {
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        return `${yyyy}-${mm}-${dd}`;
      };
      const dateStr = getLocalYYYYMMDD(now);
      const currentTimeStr = now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' });

      // Helper to convert "02:30 PM" to "14:30" for accurate comparison
      const parseTime = (time12h) => {
        const [time, modifier] = time12h.split(' ');
        let [hours, minutes] = time.split(':');
        if (hours === '12') hours = '00';
        if (modifier === 'PM') hours = parseInt(hours, 10) + 12;
        return `${hours.toString().padStart(2, '0')}:${minutes}`;
      };

      // Fetch available slots for the selected doctor
      const slots = await appointmentService.fetchSlotInventory({ doctor_id: doctorId, date: dateStr });
      
      // Get the absolute earliest free slot in the schedule for this day
      const availableSlots = slots.filter(s => s.status === 'AVAILABLE');
      
      let timeStr = currentTimeStr;
      if (availableSlots.length > 0) {
        // Pick the earliest available slot (morning -> afternoon)
        availableSlots.sort((a, b) => parseTime(a.slot_time).localeCompare(parseTime(b.slot_time)));
        timeStr = availableSlots[0].slot_time;
      }

      const payload = {
        patient_id: patientId,
        patient_name: "Lookup Pending",
        doctor_id: doctorId,
        department_id: departmentId,
        appointment_date: dateStr,
        appointment_time: timeStr,
        priority: priority,
        is_walk_in: true,
        notes: notes.trim() || 'Walk-in generated token',
        staff_id: 'Staff Member'
      };

      const apt = await appointmentService.createAppointment(payload);
      
      // 2. Transition status to CHECKED_IN to generate Token
      const updatedApt = await appointmentService.transitionStatus(apt.appointment_id, 'Checked-In');

      setGeneratedTokenInfo({
        token: updatedApt.token_number,
        name: updatedApt.patient_name,
        id: updatedApt.patient_id
      });
      setPatientId('');
      setPriority('Normal');
      setNotes('');
      if (onGenerate) onGenerate();
    } catch (err) {
      setError(err.message);
    }
  };

  if (!metadata) return <div>Loading token generator...</div>;

  return (
    <div style={{ 
      marginBottom: '2.5rem', 
      border: '1px solid #e2e8f0', 
      boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.025)', 
      borderRadius: '12px', 
      background: '#ffffff',
      overflow: 'hidden'
    }}>
      <div style={{ 
        padding: '1.25rem 1.75rem', 
        borderBottom: '1px solid #f1f5f9', 
        background: 'linear-gradient(to right, #f8fafc, #ffffff)' 
      }}>
        <h3 style={{ margin: 0, color: '#0f172a', fontSize: '1.25rem', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ padding: '0.5rem', background: '#eff6ff', borderRadius: '8px', display: 'flex' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--primary-color)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <line x1="19" y1="8" x2="19" y2="14"></line>
              <line x1="22" y1="11" x2="16" y2="11"></line>
            </svg>
          </div>
          Instant Walk-In Registration
        </h3>
        <p style={{ margin: '0.5rem 0 0 0', color: '#64748b', fontSize: '0.9rem' }}>Quickly register patients without prior bookings and assign them to the live queue.</p>
      </div>

      <div style={{ padding: '1.75rem' }}>
        {error && <div style={{ color: '#b91c1c', backgroundColor: '#fef2f2', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', fontSize: '0.9rem', border: '1px solid #fecaca', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
          {error}
        </div>}
        
        {generatedTokenInfo && (
          <div style={{ padding: '1.25rem', backgroundColor: '#ecfdf5', color: '#065f46', borderRadius: '8px', marginBottom: '1.5rem', border: '1px solid #a7f3d0', display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
            <div style={{ padding: '0.25rem', background: '#d1fae5', borderRadius: '50%' }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
            </div>
            <div>
              <strong style={{ display: 'block', fontSize: '1.1rem', marginBottom: '0.25rem', color: '#047857' }}>Token {generatedTokenInfo.token} Generated Successfully!</strong>
              <span style={{ fontSize: '0.95rem' }}>{generatedTokenInfo.name} ({generatedTokenInfo.id}) has been added to the waiting queue.</span>
            </div>
          </div>
        )}
        
        <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '1.25rem', alignItems: 'flex-end', overflowX: 'auto', paddingBottom: '0.5rem' }}>
          
          <div className="input-group" style={{ flex: 1, minWidth: '180px', marginBottom: 0 }}>
            <label style={{ display: 'block', fontWeight: '500', color: '#475569', fontSize: '0.875rem', marginBottom: '0.5rem' }}>Patient ID <span style={{ color: '#ef4444' }}>*</span></label>
            <input 
              type="text" 
              style={{ width: '100%', backgroundColor: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '0.625rem 0.875rem', color: '#0f172a', outline: 'none', transition: 'border-color 0.2s' }}
              value={patientId} 
              onChange={(e) => {
                setPatientId(e.target.value.toUpperCase());
                if (generatedTokenInfo) setGeneratedTokenInfo(null);
              }}
              onFocus={(e) => e.target.style.borderColor = 'var(--primary-color)'}
              onBlur={(e) => e.target.style.borderColor = '#cbd5e1'}
              placeholder="e.g. PAT-001"
              required
            />
          </div>

          <div className="input-group" style={{ flex: 1, minWidth: '160px', marginBottom: 0 }}>
            <label style={{ display: 'block', fontWeight: '500', color: '#475569', fontSize: '0.875rem', marginBottom: '0.5rem' }}>Department <span style={{ color: '#ef4444' }}>*</span></label>
            <select 
              style={{ width: '100%', backgroundColor: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '0.625rem 0.875rem', color: '#0f172a', outline: 'none' }}
              value={departmentId} 
              onChange={(e) => {
                setDepartmentId(e.target.value);
                const doc = metadata.doctors.find(d => d.department_id === e.target.value);
                if (doc) setDoctorId(doc.doctor_id);
              }}
            >
              {metadata.departments.map(d => (
                <option key={d.department_id} value={d.department_id}>{d.department_name}</option>
              ))}
            </select>
          </div>

          <div className="input-group" style={{ flex: 1, minWidth: '160px', marginBottom: 0 }}>
            <label style={{ display: 'block', fontWeight: '500', color: '#475569', fontSize: '0.875rem', marginBottom: '0.5rem' }}>Doctor <span style={{ color: '#ef4444' }}>*</span></label>
            <select 
              style={{ width: '100%', backgroundColor: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '0.625rem 0.875rem', color: '#0f172a', outline: 'none' }}
              value={doctorId} 
              onChange={(e) => setDoctorId(e.target.value)}
            >
              {metadata.doctors.filter(d => d.department_id === departmentId).map(d => (
                <option key={d.doctor_id} value={d.doctor_id}>{d.doctor_name}</option>
              ))}
            </select>
          </div>

          <div className="input-group" style={{ flex: 1, minWidth: '150px', marginBottom: 0 }}>
            <label style={{ display: 'block', fontWeight: '500', color: '#475569', fontSize: '0.875rem', marginBottom: '0.5rem' }}>Queue Priority</label>
            <select 
              style={{ width: '100%', backgroundColor: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '0.625rem 0.875rem', color: '#0f172a', outline: 'none' }}
              value={priority} 
              onChange={(e) => setPriority(e.target.value)}
            >
              <option value="Normal">Normal</option>
              <option value="Emergency">Emergency</option>
              <option value="Senior">Senior</option>
            </select>
          </div>

          <div className="input-group" style={{ flex: 2, minWidth: '220px', marginBottom: 0 }}>
            <label style={{ display: 'block', fontWeight: '500', color: '#475569', fontSize: '0.875rem', marginBottom: '0.5rem' }}>Reason / Notes</label>
            <input 
              type="text" 
              style={{ width: '100%', backgroundColor: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '0.625rem 0.875rem', color: '#0f172a', outline: 'none' }}
              value={notes} 
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Fever..."
            />
          </div>

          <div style={{ marginBottom: 0, flexShrink: 0 }}>
            <button type="submit" style={{ 
              padding: '0.75rem 1.5rem', 
              whiteSpace: 'nowrap', 
              background: 'var(--primary-color)', 
              color: 'white', 
              border: 'none', 
              borderRadius: '6px',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
            }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
              Generate Token
            </button>
          </div>

        </form>
      </div>
    </div>
  );
};

export default TokenGeneration;
