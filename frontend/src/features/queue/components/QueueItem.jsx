import React from 'react';
import { appointmentService } from '../../appointments/services/appointmentService';
import { queueService } from '../services/queueService';

const QueueItem = ({ item, onRefresh }) => {
  const formatTime = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'Waiting': return 'badge-warning';
      case 'Called': return 'badge-success';
      case 'In Consultation': return 'badge-primary';
      default: return 'badge-default';
    }
  };

  const handleCall = async () => {
    try {
      await queueService.updateStatus(item.appointment_id, 'Called');
      onRefresh();
    } catch (err) {
      console.error(err);
    }
  };

  const handleStartConsultation = async () => {
    try {
      await appointmentService.transitionStatus(item.appointment_id, 'In Consultation');
      onRefresh();
    } catch (err) {
      console.error(err);
    }
  };

  const handleComplete = async () => {
    try {
      await appointmentService.transitionStatus(item.appointment_id, 'Completed');
      onRefresh();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div style={{ 
      border: '1px solid var(--border-color)', 
      borderRadius: 'var(--radius-md)', 
      padding: '1rem', 
      marginBottom: '1rem',
      backgroundColor: 'var(--bg-surface)'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <h4 style={{ margin: 0, fontSize: '1.125rem', color: 'var(--text-main)' }}>{item.token_number}</h4>
        <span className={`badge ${getStatusBadgeClass(item.status)}`}>{item.status}</span>
      </div>
      <p style={{ margin: '0 0 0.5rem 0', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
        <strong>Patient:</strong> {item.patient_name} <br/>
        <strong>Doctor:</strong> {item.doctor_name} <br/>
        <strong>Dept:</strong> {item.department_name} <br/>
        <strong>Added:</strong> {formatTime(item.queue_entry_time)}
      </p>
      
      
    </div>
  );
};

export default QueueItem;
