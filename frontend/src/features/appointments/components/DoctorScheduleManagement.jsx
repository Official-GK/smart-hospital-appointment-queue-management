import React, { useState, useEffect, useCallback } from 'react';
import { appointmentService } from '../services/appointmentService';
import Card from '../../../components/common/Card';
import Button from '../../../components/common/Button';
import Input from '../../../components/common/Input';
import Loading from '../../../components/common/Loading';

const DAYS_OF_WEEK = [
  { value: 0, label: 'Monday' },
  { value: 1, label: 'Tuesday' },
  { value: 2, label: 'Wednesday' },
  { value: 3, label: 'Thursday' },
  { value: 4, label: 'Friday' },
  { value: 5, label: 'Saturday' },
  { value: 6, label: 'Sunday' }
];

const DoctorScheduleManagement = () => {
  const [metadata, setMetadata] = useState(null);
  const [selectedDoctorId, setSelectedDoctorId] = useState('');
  
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState('');

  // Form states
  const [workingDays, setWorkingDays] = useState([]);
  const [shiftStart, setShiftStart] = useState('09:00 AM');
  const [shiftEnd, setShiftEnd] = useState('05:00 PM');
  const [breakStart, setBreakStart] = useState('01:00 PM');
  const [breakEnd, setBreakEnd] = useState('02:00 PM');
  const [slotDuration, setSlotDuration] = useState(30);

  // Blocked time states
  const [blockDate, setBlockDate] = useState('');
  const [blockStartTime, setBlockStartTime] = useState('');
  const [blockEndTime, setBlockEndTime] = useState('');
  const [blockReason, setBlockReason] = useState('');

  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const data = await appointmentService.fetchFilterMetadata();
        setMetadata(data);
        if (data.doctors.length > 0) setSelectedDoctorId(data.doctors[0].doctor_id);
      } catch (err) {
        setError('Failed to load metadata.');
      }
    };
    fetchMetadata();
  }, []);

  const fetchSchedule = useCallback(async () => {
    if (!selectedDoctorId) return;
    setLoading(true);
    setError(null);
    setSuccessMsg('');
    try {
      const data = await appointmentService.getSchedule(selectedDoctorId);
      setSchedule(data);
      setWorkingDays(data.working_days);
      setShiftStart(data.shift_start);
      setShiftEnd(data.shift_end);
      setBreakStart(data.break_start || '');
      setBreakEnd(data.break_end || '');
      setSlotDuration(data.slot_duration_minutes);
    } catch (err) {
      setError('Could not fetch schedule. ' + err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedDoctorId]);

  useEffect(() => {
    fetchSchedule();
  }, [fetchSchedule]);

  const handleSaveSchedule = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccessMsg('');
    try {
      const payload = {
        doctor_id: selectedDoctorId,
        working_days: workingDays,
        shift_start: shiftStart,
        shift_end: shiftEnd,
        break_start: breakStart || null,
        break_end: breakEnd || null,
        slot_duration_minutes: parseInt(slotDuration, 10),
        blocked_times: schedule.blocked_times || []
      };
      const updated = await appointmentService.updateSchedule(selectedDoctorId, payload);
      setSchedule(updated);
      setSuccessMsg('Schedule updated successfully!');
    } catch (err) {
      setError('Failed to update schedule. ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleAddBlock = async (e) => {
    e.preventDefault();
    if (!blockDate || !blockStartTime || !blockEndTime || !blockReason) {
      setError('Please fill in all blocked time fields.');
      return;
    }
    setSaving(true);
    setError(null);
    setSuccessMsg('');
    try {
      // Create full ISO strings for start/end
      const startDateTime = new Date(`${blockDate}T${blockStartTime}:00`).toISOString();
      const endDateTime = new Date(`${blockDate}T${blockEndTime}:00`).toISOString();

      const payload = {
        start_time: startDateTime,
        end_time: endDateTime,
        reason: blockReason
      };
      
      const updated = await appointmentService.blockTime(selectedDoctorId, payload);
      setSchedule(updated);
      setBlockDate('');
      setBlockStartTime('');
      setBlockEndTime('');
      setBlockReason('');
      setSuccessMsg('Time blocked successfully!');
    } catch (err) {
      setError('Failed to block time. ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const toggleDay = (dayVal) => {
    setWorkingDays(prev => 
      prev.includes(dayVal) ? prev.filter(d => d !== dayVal) : [...prev, dayVal]
    );
  };

  if (!metadata) return <Loading />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', backgroundColor: 'var(--bg-surface)', padding: '1rem', borderRadius: 'var(--radius-md)' }}>
        <h3 style={{ margin: 0, minWidth: '150px' }}>Select Doctor:</h3>
        <select 
          className="input-field" 
          value={selectedDoctorId} 
          onChange={(e) => setSelectedDoctorId(e.target.value)}
          style={{ maxWidth: '300px', marginBottom: 0 }}
        >
          {metadata.doctors.map(d => (
            <option key={d.doctor_id} value={d.doctor_id}>{d.doctor_name} - {d.department_name}</option>
          ))}
        </select>
      </div>

      {error && <div style={{ padding: '0.75rem', backgroundColor: '#f8d7da', color: '#721c24', borderRadius: '4px' }}>{error}</div>}
      {successMsg && <div style={{ padding: '0.75rem', backgroundColor: '#d4edda', color: '#155724', borderRadius: '4px' }}>{successMsg}</div>}

      {loading ? (
        <Loading />
      ) : schedule ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', alignItems: 'start' }}>
          
          <Card title="Shift & Working Hours">
            <form onSubmit={handleSaveSchedule} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              
              <div>
                <label className="input-label" style={{ marginBottom: '0.5rem', display: 'block' }}>Working Days</label>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {DAYS_OF_WEEK.map(day => (
                    <div 
                      key={day.value}
                      onClick={() => toggleDay(day.value)}
                      style={{
                        padding: '0.5rem 1rem',
                        borderRadius: '20px',
                        cursor: 'pointer',
                        border: '1px solid var(--border-color)',
                        backgroundColor: workingDays.includes(day.value) ? 'var(--primary-color)' : 'transparent',
                        color: workingDays.includes(day.value) ? 'white' : 'var(--text-main)',
                        fontWeight: workingDays.includes(day.value) ? 'bold' : 'normal',
                      }}
                    >
                      {day.label}
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '1rem' }}>
                <div style={{ flex: 1 }}>
                  <Input label="Shift Start Time" value={shiftStart} onChange={(e) => setShiftStart(e.target.value)} placeholder="e.g. 09:00 AM" required />
                </div>
                <div style={{ flex: 1 }}>
                  <Input label="Shift End Time" value={shiftEnd} onChange={(e) => setShiftEnd(e.target.value)} placeholder="e.g. 05:00 PM" required />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '1rem' }}>
                <div style={{ flex: 1 }}>
                  <Input label="Break Start Time" value={breakStart} onChange={(e) => setBreakStart(e.target.value)} placeholder="e.g. 01:00 PM" />
                </div>
                <div style={{ flex: 1 }}>
                  <Input label="Break End Time" value={breakEnd} onChange={(e) => setBreakEnd(e.target.value)} placeholder="e.g. 02:00 PM" />
                </div>
              </div>

              <div>
                <Input type="number" label="Slot Duration (minutes)" value={slotDuration} onChange={(e) => setSlotDuration(e.target.value)} required />
              </div>

              <Button type="submit" variant="primary" disabled={saving}>{saving ? 'Saving...' : 'Save Schedule'}</Button>
            </form>
          </Card>

          <Card title="Blocked Times (Leaves, Meetings)">
            <form onSubmit={handleAddBlock} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem' }}>
              <Input type="date" label="Date" value={blockDate} onChange={(e) => setBlockDate(e.target.value)} required />
              <div style={{ display: 'flex', gap: '1rem' }}>
                <div style={{ flex: 1 }}>
                  <Input type="time" label="Start Time" value={blockStartTime} onChange={(e) => setBlockStartTime(e.target.value)} required />
                </div>
                <div style={{ flex: 1 }}>
                  <Input type="time" label="End Time" value={blockEndTime} onChange={(e) => setBlockEndTime(e.target.value)} required />
                </div>
              </div>
              <Input label="Reason" value={blockReason} onChange={(e) => setBlockReason(e.target.value)} placeholder="e.g. Emergency Meeting" required />
              <Button type="submit" variant="secondary" disabled={saving}>Add Blocked Time</Button>
            </form>

            <h4 style={{ margin: '0 0 1rem 0' }}>Current Blocked Times</h4>
            {schedule.blocked_times && schedule.blocked_times.length > 0 ? (
              <ul style={{ paddingLeft: '1.25rem', margin: 0 }}>
                {schedule.blocked_times.map(block => {
                  const s = new Date(block.start_time);
                  const e = new Date(block.end_time);
                  return (
                    <li key={block.block_id} style={{ marginBottom: '0.5rem' }}>
                      <strong>{s.toLocaleDateString()}</strong>: {s.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})} - {e.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})} 
                      <br />
                      <span style={{ color: 'var(--text-muted)' }}>Reason: {block.reason}</span>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p style={{ color: 'var(--text-muted)', margin: 0 }}>No blocked times configured.</p>
            )}
          </Card>

        </div>
      ) : null}
    </div>
  );
};

export default DoctorScheduleManagement;
