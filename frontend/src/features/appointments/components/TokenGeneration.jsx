import React, { useState, useEffect } from 'react';
import { appointmentService } from '../services/appointmentService';

const TokenGeneration = ({ onGenerate }) => {
  const [patientName, setPatientName] = useState('');
  const [departmentId, setDepartmentId] = useState('');
  const [doctorId, setDoctorId] = useState('');
  const [metadata, setMetadata] = useState(null);
  const [error, setError] = useState('');

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
    if (!patientName.trim() || !departmentId || !doctorId) return;
    setError('');

    try {
      // 1. Create a Walk-in Appointment for today
      const now = new Date();
      // Round to next 30 minutes for simplicity
      const minutes = now.getMinutes() > 30 ? 60 : 30;
      now.setMinutes(minutes);
      
      const timeStr = now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' });
      const dateStr = now.toISOString().split('T')[0];

      const payload = {
        patient_id: '',
        patient_name: patientName,
        doctor_id: doctorId,
        department_id: departmentId,
        appointment_date: dateStr,
        appointment_time: timeStr,
        priority: 'Normal',
        notes: 'Walk-in generated token',
        staff_id: 'Staff Member'
      };

      const apt = await appointmentService.createAppointment(payload);
      
      // 2. Transition status to CHECKED_IN to generate Token
      await appointmentService.transitionStatus(apt.appointment_id, 'Checked-In');

      setPatientName('');
      if (onGenerate) onGenerate();
    } catch (err) {
      setError(err.message);
    }
  };

  if (!metadata) return <div>Loading token generator...</div>;

  return (
    <div className="card" style={{ marginBottom: '1.5rem' }}>
      <h3 className="card-title">Walk-In Token Generation</h3>
      {error && <div style={{ color: 'var(--danger-color)', marginBottom: '1rem' }}>{error}</div>}
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
        <div className="input-group" style={{ flex: 1, minWidth: '200px', marginBottom: 0 }}>
          <label className="input-label">Patient Name</label>
          <input 
            type="text" 
            className="input-field" 
            value={patientName} 
            onChange={(e) => setPatientName(e.target.value)}
            placeholder="Enter patient name"
            required
          />
        </div>
        <div className="input-group" style={{ flex: 1, minWidth: '150px', marginBottom: 0 }}>
          <label className="input-label">Department</label>
          <select 
            className="input-field" 
            value={departmentId} 
            onChange={(e) => {
              setDepartmentId(e.target.value);
              // Auto-select first doctor in department
              const doc = metadata.doctors.find(d => d.department_id === e.target.value);
              if (doc) setDoctorId(doc.doctor_id);
            }}
          >
            {metadata.departments.map(d => (
              <option key={d.department_id} value={d.department_id}>{d.department_name}</option>
            ))}
          </select>
        </div>
        <div className="input-group" style={{ flex: 1, minWidth: '150px', marginBottom: 0 }}>
          <label className="input-label">Doctor</label>
          <select 
            className="input-field" 
            value={doctorId} 
            onChange={(e) => setDoctorId(e.target.value)}
          >
            {metadata.doctors.filter(d => d.department_id === departmentId).map(d => (
              <option key={d.doctor_id} value={d.doctor_id}>{d.doctor_name}</option>
            ))}
          </select>
        </div>
        <button type="submit" className="btn btn-primary">Generate Token</button>
      </form>
    </div>
  );
};

export default TokenGeneration;
