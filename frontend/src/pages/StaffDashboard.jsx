import React, { useState, useEffect, useCallback } from 'react';
import StaffLayout from '../layouts/StaffLayout';
import Table from '../components/common/Table';
import Card from '../components/common/Card';
import Modal from '../components/common/Modal';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import Loading from '../components/common/Loading';
import Input from '../components/common/Input';
import {
  fetchAppointments,
  fetchFilterMetadata,
  transitionAppointmentStatus,
  cancelAppointment,
  fetchSlotInventory,
  fetchAppointmentStatistics,
  rescheduleAppointment,
  createAppointment,
} from '../services/api';

const STATUS_OPTIONS = [
  'All',
  'Scheduled',
  'Checked-In',
  'In-Consultation',
  'Completed',
  'Cancelled',
  'No-Show',
];

const DEFAULT_CANCELLATION_REASONS = [
  'Patient Request',
  'Doctor Unavailable',
  'Scheduling Conflict',
  'Medical Emergency',
  'Weather / Transportation Delay',
  'Duplicate Booking',
  'Other',
];

const RESCHEDULE_REASONS = [
  'Patient Request',
  'Doctor Availability',
  'Medical Reschedule',
  'Urgent Reassignment',
  'Scheduling Conflict',
  'Other',
];

function formatTimestamp(isoStr) {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return isoStr;
  }
}

function formatShortTime(isoStr) {
  if (!isoStr) return null;
  try {
    const d = new Date(isoStr);
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return null;
  }
}

function getStatusBadgeVariant(status) {
  switch (status) {
    case 'Checked-In':
    case 'Completed':
      return 'success';
    case 'In-Consultation':
      return 'warning';
    case 'No-Show':
      return 'danger';
    case 'Scheduled':
    case 'Cancelled':
    default:
      return 'default';
  }
}

const StaffDashboard = () => {
  const [appointments, setAppointments] = useState([]);
  const [metadata, setMetadata] = useState({ statuses: [], departments: [], doctors: [], cancellation_reasons: [] });
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notification, setNotification] = useState(null);

  // Search & Filters State
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState({
    status: 'All',
    departmentId: 'All',
    doctorId: 'All',
    date: '',
  });

  // Modal State for Audit History
  const [historyModalOpen, setHistoryModalOpen] = useState(false);
  const [selectedAptForHistory, setSelectedAptForHistory] = useState(null);

  // Modal State for Appointment Cancellation
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [selectedAptForCancel, setSelectedAptForCancel] = useState(null);
  const [cancelForm, setCancelForm] = useState({
    reason: 'Patient Request',
    staffId: 'STF-001',
    notes: '',
  });
  const [cancelling, setCancelling] = useState(false);

  // Modal State for Appointment Reschedule / Modification
  const [rescheduleModalOpen, setRescheduleModalOpen] = useState(false);
  const [selectedAptForReschedule, setSelectedAptForReschedule] = useState(null);
  const [rescheduleForm, setRescheduleForm] = useState({
    doctorId: '',
    appointmentDate: '',
    appointmentTime: '',
    staffId: 'STF-001',
    reason: 'Patient Request',
    notes: '',
  });
  const [rescheduleSlots, setRescheduleSlots] = useState([]);
  const [loadingRescheduleSlots, setLoadingRescheduleSlots] = useState(false);
  const [rescheduling, setRescheduling] = useState(false);

  // Modal State for Slot Inventory & Released Slots
  const [slotsModalOpen, setSlotsModalOpen] = useState(false);
  const [slotInventory, setSlotInventory] = useState([]);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [slotDoctorFilter, setSlotDoctorFilter] = useState('All');

  // Modal State for New Appointment Booking
  const [bookModalOpen, setBookModalOpen] = useState(false);
  const [booking, setBooking] = useState(false);
  const [bookingSlots, setBookingSlots] = useState([]);
  const [loadingBookingSlots, setLoadingBookingSlots] = useState(false);
  const [bookingForm, setBookingForm] = useState({
    patientName: '',
    departmentId: '',
    doctorId: '',
    appointmentDate: '',
    appointmentTime: '',
    priority: 'Normal',
    staffId: 'STF-001',
    notes: '',
  });

  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 5000);
  };

  // Load Metadata & Statistics on Mount
  useEffect(() => {
    async function loadInitial() {
      try {
        const [metaData, statsData] = await Promise.all([
          fetchFilterMetadata(),
          fetchAppointmentStatistics(),
        ]);
        setMetadata(metaData);
        setStatistics(statsData);
      } catch (err) {
        console.error('Failed to load initial metadata or stats:', err);
      }
    }
    loadInitial();
  }, []);

  // Load Appointments & Statistics
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [apts, stats] = await Promise.all([
        fetchAppointments(filters),
        fetchAppointmentStatistics(),
      ]);
      setAppointments(apts);
      setStatistics(stats);
    } catch (err) {
      showNotification(`Failed to load data: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    let ignore = false;
    async function fetchData() {
      try {
        const [apts, stats] = await Promise.all([
          fetchAppointments(filters),
          fetchAppointmentStatistics(),
        ]);
        if (!ignore) {
          setAppointments(apts);
          setStatistics(stats);
          setLoading(false);
        }
      } catch (err) {
        if (!ignore) {
          showNotification(`Failed to load data: ${err.message}`, 'error');
          setLoading(false);
        }
      }
    }
    fetchData();
    return () => {
      ignore = true;
    };
  }, [filters]);

  // Handle Quick Status Transition
  const handleStatusTransition = async (appointmentId, nextStatus, options = {}) => {
    try {
      const updated = await transitionAppointmentStatus(
        appointmentId,
        nextStatus,
        `Status transitioned to ${nextStatus}`,
        'Staff Member'
      );
      showNotification(`Appointment ${appointmentId} transitioned to ${nextStatus}!`);
      setAppointments((prev) =>
        prev.map((a) => (a.appointment_id === appointmentId ? updated : a))
      );
      if (options.openHistory || nextStatus === 'Checked-In' || selectedAptForHistory?.appointment_id === appointmentId) {
        setSelectedAptForHistory(updated);
        setHistoryModalOpen(true);
      }
      const newStats = await fetchAppointmentStatistics();
      setStatistics(newStats);
    } catch (err) {
      showNotification(err.message, 'error');
    }
  };

  // Open Cancellation Modal
  const handleOpenCancelModal = (apt) => {
    setSelectedAptForCancel(apt);
    setCancelForm({
      reason: metadata.cancellation_reasons?.[0] || 'Patient Request',
      staffId: 'STF-001',
      notes: '',
    });
    setCancelModalOpen(true);
  };

  // Execute Appointment Cancellation
  const handleExecuteCancel = async () => {
    if (!selectedAptForCancel) return;
    if (!cancelForm.reason.trim()) {
      showNotification('Cancellation reason is required.', 'error');
      return;
    }
    if (!cancelForm.staffId.trim()) {
      showNotification('Staff ID is required.', 'error');
      return;
    }

    setCancelling(true);
    try {
      const updated = await cancelAppointment(selectedAptForCancel.appointment_id, {
        reason: cancelForm.reason,
        staffId: cancelForm.staffId,
        notes: cancelForm.notes,
      });

      showNotification(
        `Appointment ${updated.appointment_id} successfully cancelled. Slot ${updated.appointment_time} released back to inventory!`,
        'success'
      );

      setAppointments((prev) =>
        prev.map((a) => (a.appointment_id === updated.appointment_id ? updated : a))
      );
      if (selectedAptForHistory?.appointment_id === updated.appointment_id) {
        setSelectedAptForHistory(updated);
      }

      // Refresh cancellation and slot statistics
      const newStats = await fetchAppointmentStatistics();
      setStatistics(newStats);

      setCancelModalOpen(false);
      setSelectedAptForCancel(null);
    } catch (err) {
      showNotification(`Cancellation failed: ${err.message}`, 'error');
    } finally {
      setCancelling(false);
    }
  };

  // Open Reschedule Modal & Load Doctor Slots
  const handleOpenRescheduleModal = async (apt) => {
    setSelectedAptForReschedule(apt);
    const initialDoctorId = apt.doctor_id;
    const initialDate = apt.appointment_date;

    setRescheduleForm({
      doctorId: initialDoctorId,
      appointmentDate: initialDate,
      appointmentTime: apt.appointment_time,
      staffId: 'STF-001',
      reason: 'Patient Request',
      notes: '',
    });

    setRescheduleModalOpen(true);
    setLoadingRescheduleSlots(true);
    try {
      const slots = await fetchSlotInventory(initialDoctorId, initialDate);
      setRescheduleSlots(slots);
    } catch (err) {
      console.error('Failed to load slots for reschedule:', err);
    } finally {
      setLoadingRescheduleSlots(false);
    }
  };

  // On change of Doctor or Date inside Reschedule Modal
  const handleRescheduleDoctorOrDateChange = async (newDocId, newDate) => {
    setLoadingRescheduleSlots(true);
    try {
      const slots = await fetchSlotInventory(newDocId, newDate);
      setRescheduleSlots(slots);
    } catch (err) {
      console.error('Failed to update slots:', err);
    } finally {
      setLoadingRescheduleSlots(false);
    }
  };

  // Execute Reschedule
  const handleExecuteReschedule = async () => {
    if (!selectedAptForReschedule) return;
    if (!rescheduleForm.staffId.trim()) {
      showNotification('Staff ID is required.', 'error');
      return;
    }
    if (!rescheduleForm.appointmentDate) {
      showNotification('Appointment date is required.', 'error');
      return;
    }
    if (!rescheduleForm.appointmentTime) {
      showNotification('Appointment time slot is required.', 'error');
      return;
    }

    setRescheduling(true);
    try {
      const updated = await rescheduleAppointment(selectedAptForReschedule.appointment_id, {
        staffId: rescheduleForm.staffId,
        doctorId: rescheduleForm.doctorId,
        appointmentDate: rescheduleForm.appointmentDate,
        appointmentTime: rescheduleForm.appointmentTime,
        reason: rescheduleForm.reason,
        notes: rescheduleForm.notes,
      });

      showNotification(
        `Appointment ${updated.appointment_id} rescheduled to ${updated.appointment_date} at ${updated.appointment_time} with ${updated.doctor_name}!`,
        'success'
      );

      setAppointments((prev) =>
        prev.map((a) => (a.appointment_id === updated.appointment_id ? updated : a))
      );
      if (selectedAptForHistory?.appointment_id === updated.appointment_id) {
        setSelectedAptForHistory(updated);
      }

      // Refresh slot statistics
      const newStats = await fetchAppointmentStatistics();
      setStatistics(newStats);

      setRescheduleModalOpen(false);
      setSelectedAptForReschedule(null);
    } catch (err) {
      showNotification(`Reschedule failed: ${err.message}`, 'error');
    } finally {
      setRescheduling(false);
    }
  };

  // Load Slot Inventory Modal Data
  const handleOpenSlotsModal = async (doctorId = 'All') => {
    setLoadingSlots(true);
    setSlotsModalOpen(true);
    try {
      const slots = await fetchSlotInventory(doctorId, filters.date || '');
      setSlotInventory(slots);
    } catch (err) {
      showNotification(`Failed to load slot inventory: ${err.message}`, 'error');
    } finally {
      setLoadingSlots(false);
    }
  };

  const handleFilterSlotsByDoctor = async (doctorId) => {
    setSlotDoctorFilter(doctorId);
    setLoadingSlots(true);
    try {
      const slots = await fetchSlotInventory(doctorId, filters.date || '');
      setSlotInventory(slots);
    } catch (err) {
      showNotification(`Failed to load slots: ${err.message}`, 'error');
    } finally {
      setLoadingSlots(false);
    }
  };

  // Open Book Appointment Modal & Preload Availability
  const handleOpenBookModal = async () => {
    const todayStr = new Date().toISOString().split('T')[0];
    const defaultDept = metadata.departments?.[0]?.department_id || 'DEP-CARD';
    const docsInDept = metadata.doctors?.filter((d) => d.department_id === defaultDept) || [];
    const defaultDoc = docsInDept[0]?.doctor_id || metadata.doctors?.[0]?.doctor_id || 'DOC-001';

    setBookingForm({
      patientName: '',
      departmentId: defaultDept,
      doctorId: defaultDoc,
      appointmentDate: todayStr,
      appointmentTime: '',
      priority: 'Normal',
      staffId: 'STF-001',
      notes: '',
    });

    setBookModalOpen(true);
    setLoadingBookingSlots(true);
    try {
      const slots = await fetchSlotInventory(defaultDoc, todayStr);
      setBookingSlots(slots);
    } catch (err) {
      console.error('Failed to load slots for booking:', err);
    } finally {
      setLoadingBookingSlots(false);
    }
  };

  // Handle Department Change in Booking Form
  const handleBookingDepartmentChange = async (newDeptId) => {
    const docsInDept = metadata.doctors?.filter((d) => d.department_id === newDeptId) || [];
    const newDocId = docsInDept[0]?.doctor_id || '';
    setBookingForm((prev) => ({
      ...prev,
      departmentId: newDeptId,
      doctorId: newDocId,
      appointmentTime: '',
    }));
    if (newDocId) {
      setLoadingBookingSlots(true);
      try {
        const slots = await fetchSlotInventory(newDocId, bookingForm.appointmentDate || new Date().toISOString().split('T')[0]);
        setBookingSlots(slots);
      } catch (err) {
        console.error('Failed to update slots on department change:', err);
      } finally {
        setLoadingBookingSlots(false);
      }
    } else {
      setBookingSlots([]);
    }
  };

  // Handle Doctor or Date Change in Booking Form
  const handleBookingDoctorOrDateChange = async (newDocId, newDate) => {
    const docObj = metadata.doctors?.find((d) => d.doctor_id === newDocId);
    setBookingForm((prev) => ({
      ...prev,
      doctorId: newDocId,
      departmentId: docObj?.department_id || prev.departmentId,
      appointmentDate: newDate,
      appointmentTime: '',
    }));

    if (newDocId && newDate) {
      setLoadingBookingSlots(true);
      try {
        const slots = await fetchSlotInventory(newDocId, newDate);
        setBookingSlots(slots);
      } catch (err) {
        console.error('Failed to update booking slots:', err);
      } finally {
        setLoadingBookingSlots(false);
      }
    }
  };

  // Execute Appointment Booking
  const handleExecuteBooking = async () => {
    if (!bookingForm.patientName.trim()) {
      showNotification('Patient name is required.', 'error');
      return;
    }
    if (!bookingForm.departmentId) {
      showNotification('Department is required.', 'error');
      return;
    }
    if (!bookingForm.doctorId) {
      showNotification('Doctor is required.', 'error');
      return;
    }
    if (!bookingForm.appointmentDate) {
      showNotification('Appointment date is required.', 'error');
      return;
    }
    if (!bookingForm.appointmentTime) {
      showNotification('Please select an available time slot.', 'error');
      return;
    }

    setBooking(true);
    try {
      const newApt = await createAppointment({
        patient_name: bookingForm.patientName.trim(),
        department_id: bookingForm.departmentId,
        doctor_id: bookingForm.doctorId,
        appointment_date: bookingForm.appointmentDate,
        appointment_time: bookingForm.appointmentTime,
        priority: bookingForm.priority,
        staff_id: bookingForm.staffId,
        notes: bookingForm.notes,
      });

      showNotification(
        `Appointment ${newApt.appointment_id} successfully booked for ${newApt.patient_name} with ${newApt.doctor_name} at ${newApt.appointment_time}!`,
        'success'
      );

      setAppointments((prev) => [newApt, ...prev]);

      const newStats = await fetchAppointmentStatistics();
      setStatistics(newStats);

      setBookModalOpen(false);
    } catch (err) {
      showNotification(`Booking failed: ${err.message}`, 'error');
    } finally {
      setBooking(false);
    }
  };

  // Filter Handlers
  const handleFieldFilter = (field, value) => {
    setFilters((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleResetFilters = () => {
    setSearchQuery('');
    setFilters({
      status: 'All',
      departmentId: 'All',
      doctorId: 'All',
      date: '',
    });
  };

  // Apply search query filter on top of server filters
  const displayedAppointments = appointments.filter((apt) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase().trim();
    return (
      apt.patient_name.toLowerCase().includes(q) ||
      apt.appointment_id.toLowerCase().includes(q) ||
      apt.patient_id.toLowerCase().includes(q) ||
      apt.doctor_name.toLowerCase().includes(q) ||
      (apt.token_number && apt.token_number.toLowerCase().includes(q))
    );
  });

  const filteredDoctors = filters.departmentId && filters.departmentId !== 'All'
    ? metadata.doctors.filter((d) => d.department_id === filters.departmentId)
    : metadata.doctors;

  const cancellationReasons = metadata.cancellation_reasons?.length > 0
    ? metadata.cancellation_reasons
    : DEFAULT_CANCELLATION_REASONS;

  // KPI calculations
  const totalCount = displayedAppointments.length;
  const scheduledCount = displayedAppointments.filter((a) => a.status === 'Scheduled').length;
  const checkedInCount = displayedAppointments.filter((a) => a.status === 'Checked-In').length;
  const inConsultCount = displayedAppointments.filter((a) => a.status === 'In-Consultation').length;
  const completedCount = displayedAppointments.filter((a) => a.status === 'Completed').length;
  const cancelledCount = displayedAppointments.filter((a) => a.status === 'Cancelled').length;
  const noShowCount = displayedAppointments.filter((a) => a.status === 'No-Show').length;

  const tableHeaders = [
    'Patient & Token',
    'Doctor & Dept',
    'Schedule',
    'Status',
    'Operational Timestamps',
    'Actions',
  ];

  const slotHeaders = [
    'Slot Time',
    'Doctor',
    'Slot Status',
    'Inventory Availability / Booking Note',
  ];

  // Reschedule slot collision check
  const isSelectedSlotCollision = selectedAptForReschedule && rescheduleSlots.some((s) => {
    return (
      s.slot_time === rescheduleForm.appointmentTime &&
      s.status === 'BOOKED' &&
      s.appointment_id !== selectedAptForReschedule.appointment_id
    );
  });

  // Booking slot collision check (prevent overbooking / double-booking)
  const isSelectedBookingSlotCollision = Boolean(
    bookingSlots.some((s) => s.slot_time === bookingForm.appointmentTime && s.status === 'BOOKED')
  );

  return (
    <StaffLayout>
      <div className="dashboard-container">
        {/* Toast Notification Banner */}
        {notification && (
          <div className={`notification-banner ${notification.type}`}>
            <span>{notification.message}</span>
            <button
              type="button"
              className="notif-close"
              onClick={() => setNotification(null)}
            >
              &times;
            </button>
          </div>
        )}

        {/* Dashboard Top Header */}
        <div className="dashboard-header-block">
          <div className="dashboard-header-title-group">
            <h1 className="page-title">Appointment Lifecycle & Schedule Management</h1>
            <p className="page-subtitle">
              Modify appointment dates, time slots, and doctors with slot validation, cancel slots to restore inventory, and monitor real-time clinic capacity.
            </p>
          </div>
          <div className="dashboard-header-actions">
            <Button
              variant="primary"
              onClick={handleOpenBookModal}
              id="btn-book-appointment"
            >
              Book Appointment
            </Button>
            <Button
              variant="secondary"
              onClick={() => handleOpenSlotsModal(filters.doctorId !== 'All' ? filters.doctorId : 'All')}
              id="btn-view-slots"
            >
              View Slot Inventory
            </Button>
            <Button
              variant="secondary"
              onClick={loadData}
              disabled={loading}
              id="btn-refresh-all"
            >
              {loading ? 'Refreshing...' : 'Refresh'}
            </Button>
          </div>
        </div>

        {/* Cancellation & Completion Intelligence Card */}
        {statistics && (
          <Card className="stats-intelligence-card" id="cancellation-statistics-panel">
            <div className="stats-strip-container">
              <div className="stats-metrics-group">
                <div className="stat-pill-metric">
                  <span className="stat-pill-label">Completion Rate</span>
                  <div className="stat-pill-value-row">
                    <span className="stat-pill-number success">{statistics.completion_rate}%</span>
                    <span className="stat-pill-desc">({statistics.completed_count} done)</span>
                  </div>
                </div>

                <div className="stat-pill-metric">
                  <span className="stat-pill-label">Cancellation Rate</span>
                  <div className="stat-pill-value-row">
                    <span className="stat-pill-number danger">{statistics.cancellation_rate}%</span>
                    <span className="stat-pill-desc">({statistics.cancelled_count} cancelled)</span>
                  </div>
                </div>

                <div className="stat-pill-metric">
                  <span className="stat-pill-label">No-Show Rate</span>
                  <div className="stat-pill-value-row">
                    <span className="stat-pill-number warning">{statistics.no_show_rate}%</span>
                    <span className="stat-pill-desc">({statistics.no_show_count} missed)</span>
                  </div>
                </div>

                <div className="stat-pill-metric">
                  <span className="stat-pill-label">Released Slots</span>
                  <div className="stat-pill-value-row">
                    <span className="stat-pill-number">{statistics.released_slots_count}</span>
                    <span className="stat-pill-desc">slots restored</span>
                  </div>
                </div>
              </div>

              {/* Reasons Breakdown Pills */}
              {statistics.reasons_breakdown && Object.keys(statistics.reasons_breakdown).length > 0 && (
                <div className="reasons-breakdown-row">
                  <span className="reasons-title">Cancellation Reasons:</span>
                  {Object.entries(statistics.reasons_breakdown).map(([reason, count]) => (
                    <span key={reason} className="reason-chip">
                      {reason} <span className="reason-chip-count">{count}</span>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </Card>
        )}

        {/* KPI Metrics Strip */}
        <div className="kpi-grid">
          <div className="kpi-card">
            <div className="kpi-label">Filtered Appointments</div>
            <div className="kpi-value">{totalCount}</div>
            <div className="kpi-footer">Total in view</div>
          </div>
          <div className="kpi-card kpi-scheduled">
            <div className="kpi-label">Scheduled</div>
            <div className="kpi-value">{scheduledCount}</div>
            <div className="kpi-footer">Awaiting arrival</div>
          </div>
          <div className="kpi-card kpi-active-queue">
            <div className="kpi-label">In Live Queue</div>
            <div className="kpi-value">{checkedInCount + inConsultCount}</div>
            <div className="kpi-footer">
              {checkedInCount} waiting • {inConsultCount} in consult
            </div>
          </div>
          <div className="kpi-card kpi-completed">
            <div className="kpi-label">Completed</div>
            <div className="kpi-value">{completedCount}</div>
            <div className="kpi-footer">Consultation finished</div>
          </div>
          <div className="kpi-card kpi-inactive">
            <div className="kpi-label">Cancelled / Released</div>
            <div className="kpi-value">{cancelledCount}</div>
            <div className="kpi-footer">{noShowCount} no-show</div>
          </div>
        </div>

        {/* Filter & Search Section using common Card & Button */}
        <Card className="filter-card-container" id="appointment-filters-section">
          <div className="filter-header">
            <div className="filter-title-wrap">
              <h3 className="filter-heading">Search & Filter Appointments</h3>
            </div>
            <Button
              variant="secondary"
              onClick={handleResetFilters}
              className="btn-reset-compact"
            >
              Reset All
            </Button>
          </div>

          {/* Quick Search Field */}
          <div className="search-field-container">
            <input
              type="text"
              id="search-patient-input"
              className="search-input-field"
              placeholder="Search by Patient Name, ID (e.g. PAT-001), Appointment ID (e.g. APT-001), or Token Number..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="filter-grid">
            {/* Status Filter */}
            <div className="filter-field">
              <label htmlFor="filter-status" className="filter-label">Status</label>
              <select
                id="filter-status"
                className="filter-select"
                value={filters.status}
                onChange={(e) => handleFieldFilter('status', e.target.value)}
              >
                {STATUS_OPTIONS.map((st) => (
                  <option key={st} value={st}>
                    {st === 'All' ? 'All Statuses' : st}
                  </option>
                ))}
              </select>
            </div>

            {/* Department Filter */}
            <div className="filter-field">
              <label htmlFor="filter-department" className="filter-label">Department</label>
              <select
                id="filter-department"
                className="filter-select"
                value={filters.departmentId}
                onChange={(e) => {
                  const newDept = e.target.value;
                  setFilters((prev) => ({
                    ...prev,
                    departmentId: newDept,
                    doctorId: 'All',
                  }));
                }}
              >
                <option value="All">All Departments</option>
                {metadata.departments.map((dept) => (
                  <option key={dept.department_id} value={dept.department_id}>
                    {dept.department_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Doctor Filter */}
            <div className="filter-field">
              <label htmlFor="filter-doctor" className="filter-label">Doctor</label>
              <select
                id="filter-doctor"
                className="filter-select"
                value={filters.doctorId}
                onChange={(e) => handleFieldFilter('doctorId', e.target.value)}
              >
                <option value="All">All Doctors</option>
                {filteredDoctors.map((doc) => (
                  <option key={doc.doctor_id} value={doc.doctor_id}>
                    {doc.doctor_name} ({doc.department_name})
                  </option>
                ))}
              </select>
            </div>

            {/* Date Filter */}
            <div className="filter-field">
              <div className="filter-label-row">
                <label htmlFor="filter-date" className="filter-label">Date</label>
                <div className="filter-quick-dates">
                  <button
                    type="button"
                    className={`quick-date-chip ${filters.date === new Date().toISOString().split('T')[0] ? 'active' : ''}`}
                    onClick={() => handleFieldFilter('date', new Date().toISOString().split('T')[0])}
                  >
                    Today
                  </button>
                  <button
                    type="button"
                    className={`quick-date-chip ${!filters.date ? 'active' : ''}`}
                    onClick={() => handleFieldFilter('date', '')}
                  >
                    All
                  </button>
                </div>
              </div>
              <input
                type="date"
                id="filter-date"
                className="filter-input"
                value={filters.date || ''}
                onChange={(e) => handleFieldFilter('date', e.target.value)}
              />
            </div>
          </div>
        </Card>

        {/* Appointments Table Section using common Card & Table */}
        <Card
          title="Appointments Lifecycle & Schedule"
          className="appointments-lifecycle-card"
        >
          <div className="section-header-meta" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <span className="section-subtitle-text" style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
              Real-time lifecycle state progression, schedule modifications, and audit history.
            </span>
            <span className="results-count-badge">
              Showing {displayedAppointments.length} appointment{displayedAppointments.length === 1 ? '' : 's'}
            </span>
          </div>

          {loading ? (
            <Loading text="Loading appointment lifecycle data..." />
          ) : displayedAppointments.length === 0 ? (
            <div className="empty-appointments-card">
              <h3>No Appointments Found</h3>
              <p className="placeholder-text">
                No appointments match the selected search or filter criteria. Try resetting your filters.
              </p>
            </div>
          ) : (
            <div className="appointment-table-wrapper" id="appointment-table-card">
              <Table headers={tableHeaders} className="fit-table">
                {displayedAppointments.map((apt) => {
                  const ts = apt.timestamps || {};
                  const checkInTime = formatShortTime(ts.check_in_time);
                  const consultStartTime = formatShortTime(ts.consultation_start_time);
                  const consultEndTime = formatShortTime(ts.consultation_end_time);
                  const cancelledTime = formatShortTime(ts.cancelled_at);

                  return (
                    <tr key={apt.appointment_id} className={`apt-row status-row-${apt.status.toLowerCase()}`}>
                      {/* Patient & Token */}
                      <td className="td-patient-token">
                        <div className="patient-name-text">{apt.patient_name}</div>
                        <div className="patient-meta-row">
                          <span className="apt-id-code">{apt.appointment_id}</span>
                          {apt.token_number ? (
                            <span className="token-tag">Token #{apt.token_number}</span>
                          ) : (
                            <span className="no-token-tag">No Token</span>
                          )}
                          {apt.priority === 'Emergency' && (
                            <Badge text="EMERGENCY" variant="danger" className="badge-priority-sm" />
                          )}
                          {apt.priority === 'Senior' && (
                            <Badge text="SENIOR" variant="warning" className="badge-priority-sm" />
                          )}
                        </div>
                      </td>

                      {/* Doctor & Dept */}
                      <td className="td-doctor-dept">
                        <div className="doctor-name-text">{apt.doctor_name}</div>
                        <div className="department-tag">{apt.department_name}</div>
                      </td>

                      {/* Schedule */}
                      <td className="td-schedule-compact">
                        <div className="schedule-date">{apt.appointment_date}</div>
                        <div className="schedule-time">{apt.appointment_time}</div>
                      </td>

                      {/* Status Badge using common/Badge */}
                      <td className="td-status-cell">
                        <Badge
                          text={apt.status}
                          variant={getStatusBadgeVariant(apt.status)}
                          className={`status-badge-custom badge-${apt.status.toLowerCase()}`}
                        />
                        {apt.status === 'Cancelled' && (
                          <div style={{ marginTop: '0.2rem' }}>
                            <span className="slot-status-badge slot-status-released" title="Time slot released back to inventory">
                              Slot Released
                            </span>
                          </div>
                        )}
                      </td>

                      {/* Operational Timestamps */}
                      <td className="td-timestamps-compact">
                        <div className="ts-mini-list">
                          {checkInTime && (
                            <div className="ts-mini-item">
                              <span className="ts-mini-key">In:</span>
                              <span className="ts-mini-val">{checkInTime}</span>
                            </div>
                          )}
                          {consultStartTime && (
                            <div className="ts-mini-item">
                              <span className="ts-mini-key">Exam:</span>
                              <span className="ts-mini-val">{consultStartTime}</span>
                            </div>
                          )}
                          {consultEndTime && (
                            <div className="ts-mini-item">
                              <span className="ts-mini-key">Done:</span>
                              <span className="ts-mini-val">{consultEndTime}</span>
                            </div>
                          )}
                          {cancelledTime && (
                            <div className="ts-mini-item">
                              <span className="ts-mini-key">Cancelled:</span>
                              <span className="ts-mini-val" style={{ color: 'var(--danger-color)' }}>{cancelledTime}</span>
                            </div>
                          )}
                          {!checkInTime && !consultStartTime && !cancelledTime && (
                            <span className="ts-not-started">Pending check-in</span>
                          )}
                        </div>
                      </td>

                      {/* Actions using common/Button */}
                      <td className="td-actions-cell">
                        <div className="actions-structured-cell">
                          {apt.status === 'Scheduled' ? (
                            <>
                              <div className="actions-row-primary">
                                <Button
                                  variant="success"
                                  className="btn-act-primary"
                                  onClick={() => handleStatusTransition(apt.appointment_id, 'Checked-In', { openHistory: true })}
                                  title="Check-In patient and view audit history"
                                >
                                  Check-In
                                </Button>
                                <Button
                                  variant="secondary"
                                  className="btn-act-history"
                                  onClick={() => {
                                    setSelectedAptForHistory(apt);
                                    setHistoryModalOpen(true);
                                  }}
                                  title="View audit trail"
                                >
                                  History
                                </Button>
                              </div>
                              <div className="actions-row-secondary">
                                <Button
                                  variant="secondary"
                                  className="btn-act-secondary btn-act-reschedule"
                                  onClick={() => handleOpenRescheduleModal(apt)}
                                  title="Reschedule date, time slot, or doctor"
                                >
                                  Reschedule
                                </Button>
                                <Button
                                  variant="secondary"
                                  className="btn-act-secondary btn-act-cancel"
                                  onClick={() => handleOpenCancelModal(apt)}
                                  title="Cancel appointment and release slot"
                                >
                                  Cancel
                                </Button>
                                <Button
                                  variant="danger"
                                  className="btn-act-secondary btn-act-noshow"
                                  onClick={() => handleStatusTransition(apt.appointment_id, 'No-Show')}
                                  title="Mark patient as No-Show"
                                >
                                  No-Show
                                </Button>
                              </div>
                            </>
                          ) : (
                            <Button
                              variant="secondary"
                              className="btn-act-history-full"
                              onClick={() => {
                                setSelectedAptForHistory(apt);
                                setHistoryModalOpen(true);
                              }}
                              title="View full audit history for this appointment"
                            >
                              View Audit History
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </Table>
            </div>
          )}
        </Card>

        {/* Reschedule / Modification Modal using common Modal, Input & Button */}
        <Modal
          isOpen={rescheduleModalOpen}
          title={selectedAptForReschedule ? `Reschedule Appointment: ${selectedAptForReschedule.patient_name} (${selectedAptForReschedule.appointment_id})` : 'Reschedule Appointment'}
          onClose={() => {
            if (!rescheduling) {
              setRescheduleModalOpen(false);
              setSelectedAptForReschedule(null);
            }
          }}
          maxWidth="560px"
          footer={
            <>
              <Button
                variant="secondary"
                onClick={() => {
                  setRescheduleModalOpen(false);
                  setSelectedAptForReschedule(null);
                }}
                disabled={rescheduling}
              >
                Keep Current Schedule
              </Button>
              <Button
                variant="primary"
                onClick={handleExecuteReschedule}
                disabled={rescheduling || isSelectedSlotCollision}
                id="btn-confirm-reschedule"
              >
                {rescheduling ? 'Updating Schedule...' : 'Confirm Reschedule'}
              </Button>
            </>
          }
        >
          {selectedAptForReschedule && (
            <div>
              {/* Current Slot Info Banner */}
              <div className="reschedule-current-box">
                <div className="reschedule-current-title">Current Scheduled Slot</div>
                <div className="reschedule-current-values">
                  <div className="reschedule-curr-item">
                    Doctor: <strong>{selectedAptForReschedule.doctor_name}</strong> ({selectedAptForReschedule.department_name})
                  </div>
                  <div className="reschedule-curr-item">
                    Date: <strong>{selectedAptForReschedule.appointment_date}</strong>
                  </div>
                  <div className="reschedule-curr-item">
                    Time: <strong>{selectedAptForReschedule.appointment_time}</strong>
                  </div>
                </div>
              </div>

              <div className="cancel-form-grid">
                {/* Doctor Selection */}
                <div className="cancel-field-group">
                  <label htmlFor="reschedule-doctor-select" className="cancel-field-label">
                    Assigned Doctor *
                  </label>
                  <select
                    id="reschedule-doctor-select"
                    className="cancel-select-field"
                    value={rescheduleForm.doctorId}
                    onChange={(e) => {
                      const newDocId = e.target.value;
                      setRescheduleForm({ ...rescheduleForm, doctorId: newDocId });
                      handleRescheduleDoctorOrDateChange(newDocId, rescheduleForm.appointmentDate);
                    }}
                  >
                    {metadata.doctors.map((d) => (
                      <option key={d.doctor_id} value={d.doctor_id}>
                        {d.doctor_name} — {d.department_name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Date Picker using common Input */}
                <div className="cancel-field-group">
                  <Input
                    type="date"
                    label="New Appointment Date *"
                    name="appointmentDate"
                    value={rescheduleForm.appointmentDate}
                    onChange={(e) => {
                      const newDate = e.target.value;
                      setRescheduleForm({ ...rescheduleForm, appointmentDate: newDate });
                      handleRescheduleDoctorOrDateChange(rescheduleForm.doctorId, newDate);
                    }}
                  />
                </div>

                {/* Dynamic Slot Picker with Availability Status */}
                <div className="cancel-field-group">
                  <label className="cancel-field-label">
                    Available Time Slots for Selected Doctor *
                  </label>
                  {loadingRescheduleSlots ? (
                    <div style={{ padding: '0.5rem 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Checking doctor availability...
                    </div>
                  ) : rescheduleSlots.length === 0 ? (
                    <div style={{ padding: '0.5rem 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      No slots available for the selected date.
                    </div>
                  ) : (
                    <div className="reschedule-slots-grid">
                      {rescheduleSlots.map((slot) => {
                        const isCurrentSlot =
                          slot.slot_time === selectedAptForReschedule.appointment_time &&
                          slot.doctor_id === selectedAptForReschedule.doctor_id &&
                          rescheduleForm.appointmentDate === selectedAptForReschedule.appointment_date;
                        const isBookedByOther =
                          slot.status === 'BOOKED' && slot.appointment_id !== selectedAptForReschedule.appointment_id;
                        const isSelected = slot.slot_time === rescheduleForm.appointmentTime;

                        return (
                          <button
                            key={slot.slot_time}
                            type="button"
                            className={`slot-choice-btn ${isSelected ? 'selected' : ''} ${isBookedByOther ? 'disabled' : ''}`}
                            disabled={isBookedByOther}
                            onClick={() => setRescheduleForm({ ...rescheduleForm, appointmentTime: slot.slot_time })}
                            title={isBookedByOther ? 'Slot is already booked by another patient' : isCurrentSlot ? 'Current booked slot' : 'Available slot'}
                          >
                            {slot.slot_time}
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {isSelectedSlotCollision && (
                    <div className="slot-conflict-alert">
                      The selected time slot is already booked by another patient. Please select an available slot.
                    </div>
                  )}
                </div>

                {/* Reschedule Reason Selector */}
                <div className="cancel-field-group">
                  <label htmlFor="reschedule-reason-select" className="cancel-field-label">
                    Modification Reason *
                  </label>
                  <select
                    id="reschedule-reason-select"
                    className="cancel-select-field"
                    value={rescheduleForm.reason}
                    onChange={(e) => setRescheduleForm({ ...rescheduleForm, reason: e.target.value })}
                  >
                    {RESCHEDULE_REASONS.map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </div>

                {/* Authorized Staff ID Input using common Input */}
                <div className="cancel-field-group">
                  <Input
                    label="Authorized Staff ID *"
                    name="staffId"
                    placeholder="e.g. STF-001"
                    value={rescheduleForm.staffId}
                    onChange={(e) => setRescheduleForm({ ...rescheduleForm, staffId: e.target.value })}
                  />
                </div>

                {/* Additional Notes Textarea */}
                <div className="cancel-field-group">
                  <label htmlFor="reschedule-notes" className="cancel-field-label">
                    Rescheduling Notes (Optional)
                  </label>
                  <textarea
                    id="reschedule-notes"
                    className="cancel-textarea-field"
                    rows="2"
                    placeholder="Describe context for date/time/doctor modification..."
                    value={rescheduleForm.notes}
                    onChange={(e) => setRescheduleForm({ ...rescheduleForm, notes: e.target.value })}
                  />
                </div>
              </div>
            </div>
          )}
        </Modal>

        {/* Appointment Cancellation Modal using common Modal, Input & Button */}
        <Modal
          isOpen={cancelModalOpen}
          title={selectedAptForCancel ? `Cancel Appointment: ${selectedAptForCancel.patient_name} (${selectedAptForCancel.appointment_id})` : 'Cancel Appointment'}
          onClose={() => {
            if (!cancelling) {
              setCancelModalOpen(false);
              setSelectedAptForCancel(null);
            }
          }}
          maxWidth="520px"
          footer={
            <>
              <Button
                variant="secondary"
                onClick={() => {
                  setCancelModalOpen(false);
                  setSelectedAptForCancel(null);
                }}
                disabled={cancelling}
              >
                Keep Appointment
              </Button>
              <Button
                variant="danger"
                onClick={handleExecuteCancel}
                disabled={cancelling}
                id="btn-confirm-cancel"
              >
                {cancelling ? 'Cancelling...' : 'Confirm Cancellation'}
              </Button>
            </>
          }
        >
          {selectedAptForCancel && (
            <div>
              <div className="cancel-warning-banner">
                <div className="cancel-warning-text">
                  Cancelling this appointment will <strong>immediately release the time slot ({selectedAptForCancel.appointment_time})</strong> for <strong>{selectedAptForCancel.doctor_name}</strong> back into available inventory for walk-ins and other patients.
                </div>
              </div>

              <div className="cancel-form-grid">
                {/* Cancellation Reason Dropdown */}
                <div className="cancel-field-group">
                  <label htmlFor="cancel-reason-select" className="cancel-field-label">
                    Cancellation Reason <span className="required-star">*</span>
                  </label>
                  <select
                    id="cancel-reason-select"
                    className="cancel-select-field"
                    value={cancelForm.reason}
                    onChange={(e) => setCancelForm({ ...cancelForm, reason: e.target.value })}
                  >
                    {cancellationReasons.map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </div>

                {/* Staff ID Input using common Input */}
                <div className="cancel-field-group">
                  <Input
                    label="Authorized Staff ID *"
                    name="staffId"
                    placeholder="e.g. STF-001"
                    value={cancelForm.staffId}
                    onChange={(e) => setCancelForm({ ...cancelForm, staffId: e.target.value })}
                  />
                </div>

                {/* Additional Notes Textarea */}
                <div className="cancel-field-group">
                  <label htmlFor="cancel-notes" className="cancel-field-label">
                    Operational Notes (Optional)
                  </label>
                  <textarea
                    id="cancel-notes"
                    className="cancel-textarea-field"
                    rows="3"
                    placeholder="Provide additional details regarding patient cancellation..."
                    value={cancelForm.notes}
                    onChange={(e) => setCancelForm({ ...cancelForm, notes: e.target.value })}
                  />
                </div>
              </div>
            </div>
          )}
        </Modal>

        {/* Slot Inventory & Released Capacity Modal using common Modal & Table */}
        <Modal
          isOpen={slotsModalOpen}
          title="Daily Slot Inventory & Released Capacity"
          onClose={() => setSlotsModalOpen(false)}
          maxWidth="700px"
          footer={<Button variant="secondary" onClick={() => setSlotsModalOpen(false)}>Close</Button>}
        >
          <div style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <label htmlFor="modal-slot-doctor" style={{ fontSize: '0.75rem', fontWeight: 600 }}>Filter Doctor:</label>
              <select
                id="modal-slot-doctor"
                className="filter-select"
                style={{ width: 'auto', padding: '0.3rem 0.6rem', fontSize: '0.75rem' }}
                value={slotDoctorFilter}
                onChange={(e) => handleFilterSlotsByDoctor(e.target.value)}
              >
                <option value="All">All Doctors</option>
                {metadata.doctors.map((d) => (
                  <option key={d.doctor_id} value={d.doctor_id}>{d.doctor_name}</option>
                ))}
              </select>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Date: {filters.date || 'Today'}
            </span>
          </div>

          {loadingSlots ? (
            <Loading text="Loading slot inventory..." />
          ) : slotInventory.length === 0 ? (
            <p style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1.5rem 0' }}>No slots found.</p>
          ) : (
            <div style={{ maxHeight: '420px', overflowY: 'auto' }}>
              <Table headers={slotHeaders}>
                {slotInventory.map((slot, idx) => {
                  const doctorObj = metadata.doctors.find((d) => d.doctor_id === slot.doctor_id);
                  const doctorDisplayName = doctorObj ? doctorObj.doctor_name : slot.doctor_id;

                  return (
                    <tr key={`${slot.doctor_id}-${slot.slot_time}-${idx}`}>
                      <td style={{ fontWeight: 600, fontSize: '0.8125rem' }}>{slot.slot_time}</td>
                      <td style={{ fontSize: '0.8125rem' }}>{doctorDisplayName}</td>
                      <td>
                        {slot.status === 'AVAILABLE' && (
                          <span className="slot-status-badge slot-status-available">Available</span>
                        )}
                        {slot.status === 'BOOKED' && (
                          <span className="slot-status-badge slot-status-booked">Booked</span>
                        )}
                        {slot.status === 'RELEASED' && (
                          <span className="slot-status-badge slot-status-released">Released (Walk-in Ready)</span>
                        )}
                      </td>
                      <td style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                        {slot.status === 'RELEASED' && (
                          <span style={{ color: '#92400e', fontWeight: 600 }}>
                            Freed from {slot.appointment_id} {slot.patient_name ? `(${slot.patient_name})` : ''} - Available for other patients
                          </span>
                        )}
                        {slot.status === 'BOOKED' && (
                          <span>Booked by {slot.patient_name || 'Patient'} ({slot.appointment_id})</span>
                        )}
                        {slot.status === 'AVAILABLE' && (
                          <span style={{ color: 'var(--success-color)' }}>Open for scheduling</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </Table>
            </div>
          )}
        </Modal>

        {/* Audit History Modal using common Modal & Badge */}
        <Modal
          isOpen={historyModalOpen}
          title={selectedAptForHistory ? `Audit Trail: ${selectedAptForHistory.patient_name} (${selectedAptForHistory.appointment_id})` : 'Audit Trail'}
          onClose={() => {
            setHistoryModalOpen(false);
            setSelectedAptForHistory(null);
          }}
          maxWidth="640px"
        >
          {selectedAptForHistory && (
            <div className="audit-modal-inner">
              {/* Recorded Cancellation Details if Cancelled */}
              {selectedAptForHistory.cancellation_details && (
                <div className="cancellation-details-box">
                  <div className="cancellation-details-title">
                    <span>Cancellation & Slot Release Record</span>
                  </div>
                  <div className="cancellation-details-grid">
                    <div className="cancellation-stat-item">
                      <span className="cancellation-stat-label">Reason:</span>
                      <span className="cancellation-stat-val" style={{ fontWeight: 700, color: '#991b1b' }}>
                        {selectedAptForHistory.cancellation_details.reason}
                      </span>
                    </div>
                    <div className="cancellation-stat-item">
                      <span className="cancellation-stat-label">Authorized Staff ID:</span>
                      <span className="cancellation-stat-val">
                        {selectedAptForHistory.cancellation_details.cancelled_by}
                      </span>
                    </div>
                    <div className="cancellation-stat-item">
                      <span className="cancellation-stat-label">Timestamp:</span>
                      <span className="cancellation-stat-val">
                        {formatTimestamp(selectedAptForHistory.cancellation_details.cancelled_at)}
                      </span>
                    </div>
                    <div className="cancellation-stat-item">
                      <span className="cancellation-stat-label">Released Slot:</span>
                      <span className="cancellation-stat-val" style={{ color: '#047857', fontWeight: 600 }}>
                        {selectedAptForHistory.appointment_time} (Available)
                      </span>
                    </div>
                  </div>
                  {selectedAptForHistory.cancellation_details.notes && (
                    <div style={{ marginTop: '0.4rem', fontSize: '0.75rem', color: '#7f1d1d' }}>
                      <strong>Notes:</strong> {selectedAptForHistory.cancellation_details.notes}
                    </div>
                  )}
                </div>
              )}

              <div className="timestamps-summary-card">
                <h4 className="timestamps-card-title">Operational Timestamps</h4>
                <div className="timestamps-grid">
                  <div className="ts-item">
                    <span className="ts-label">Created / Booked:</span>
                    <span className="ts-value">{formatTimestamp(selectedAptForHistory.timestamps?.created_at)}</span>
                  </div>
                  <div className="ts-item">
                    <span className="ts-label">Check-In Time:</span>
                    <span className={`ts-value ${selectedAptForHistory.timestamps?.check_in_time ? 'highlight' : ''}`}>
                      {formatTimestamp(selectedAptForHistory.timestamps?.check_in_time)}
                    </span>
                  </div>
                  <div className="ts-item">
                    <span className="ts-label">Queue Entry:</span>
                    <span className="ts-value">{formatTimestamp(selectedAptForHistory.timestamps?.queue_entry_time)}</span>
                  </div>
                  <div className="ts-item">
                    <span className="ts-label">Consultation Start:</span>
                    <span className={`ts-value ${selectedAptForHistory.timestamps?.consultation_start_time ? 'highlight' : ''}`}>
                      {formatTimestamp(selectedAptForHistory.timestamps?.consultation_start_time)}
                    </span>
                  </div>
                  <div className="ts-item">
                    <span className="ts-label">Consultation End:</span>
                    <span className={`ts-value ${selectedAptForHistory.timestamps?.consultation_end_time ? 'highlight' : ''}`}>
                      {formatTimestamp(selectedAptForHistory.timestamps?.consultation_end_time)}
                    </span>
                  </div>
                  <div className="ts-item">
                    <span className="ts-label">Cancelled At:</span>
                    <span className={`ts-value ${selectedAptForHistory.timestamps?.cancelled_at ? 'highlight' : ''}`} style={selectedAptForHistory.timestamps?.cancelled_at ? { color: 'var(--danger-color)' } : {}}>
                      {formatTimestamp(selectedAptForHistory.timestamps?.cancelled_at)}
                    </span>
                  </div>
                </div>
              </div>

              <h4 className="timeline-heading" style={{ marginTop: '1.25rem', marginBottom: '0.75rem' }}>
                Status Progression & Modification Audit Log
              </h4>
              <div className="audit-timeline">
                {(selectedAptForHistory.history || []).map((record, index) => (
                  <div key={record.history_id || index} className="timeline-item">
                    <div className="timeline-marker">
                      <span className="timeline-bullet" />
                      {index < (selectedAptForHistory.history?.length || 0) - 1 && <span className="timeline-line" />}
                    </div>
                    <div className="timeline-content">
                      <div className="timeline-header-row">
                        <div className="timeline-status-transition">
                          {record.from_status ? (
                            <>
                              <Badge
                                text={record.from_status}
                                variant={getStatusBadgeVariant(record.from_status)}
                                className="status-badge-sm"
                              />
                              <span className="transition-arrow">→</span>
                            </>
                          ) : (
                            <span className="created-tag">Initial Entry:</span>
                          )}
                          <Badge
                            text={record.to_status}
                            variant={getStatusBadgeVariant(record.to_status)}
                            className="status-badge-sm"
                          />
                        </div>
                        <span className="timeline-time">{formatTimestamp(record.changed_at)}</span>
                      </div>
                      <div className="timeline-meta">
                        <span className="timeline-actor">
                          <strong>Staff ID / Actor:</strong> {record.changed_by || 'Staff Member'}
                        </span>
                      </div>

                      {/* Structured Reschedule Comparison if available */}
                      {record.old_slot_details && record.new_slot_details && (
                        <div className="audit-reschedule-box">
                          <div className="audit-reschedule-title">Schedule Modification Details</div>
                          <div className="audit-reschedule-slots">
                            <span className="audit-slot-pill">
                              {record.old_slot_details.doctor_name} • {record.old_slot_details.appointment_date} {record.old_slot_details.appointment_time}
                            </span>
                            <span className="transition-arrow">→</span>
                            <span className="audit-slot-pill" style={{ borderColor: '#86efac', fontWeight: 600 }}>
                              {record.new_slot_details.doctor_name} • {record.new_slot_details.appointment_date} {record.new_slot_details.appointment_time}
                            </span>
                          </div>
                        </div>
                      )}

                      {record.notes && (
                        <div className="timeline-notes">
                          <span className="notes-text">&quot;{record.notes}&quot;</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Modal>

        {/* Book Appointment Modal using common Modal, Input, Button */}
        <Modal
          isOpen={bookModalOpen}
          title="Book Patient Appointment"
          onClose={() => {
            if (!booking) {
              setBookModalOpen(false);
            }
          }}
          maxWidth="580px"
          footer={
            <>
              <Button
                variant="secondary"
                onClick={() => setBookModalOpen(false)}
                disabled={booking}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleExecuteBooking}
                disabled={booking || !bookingForm.appointmentTime || isSelectedBookingSlotCollision}
                id="btn-confirm-booking"
              >
                {booking ? 'Booking Appointment...' : 'Confirm Booking'}
              </Button>
            </>
          }
        >
          <div className="cancel-form-grid">
            {/* Patient Name */}
            <div className="cancel-field-group">
              <Input
                label="Patient Full Name *"
                name="patientName"
                placeholder="e.g. John Doe"
                value={bookingForm.patientName}
                onChange={(e) => setBookingForm({ ...bookingForm, patientName: e.target.value })}
              />
            </div>

            {/* Department Selection */}
            <div className="cancel-field-group">
              <label htmlFor="book-dept-select" className="cancel-field-label">
                Department *
              </label>
              <select
                id="book-dept-select"
                className="cancel-select-field"
                value={bookingForm.departmentId}
                onChange={(e) => handleBookingDepartmentChange(e.target.value)}
              >
                {metadata.departments.map((dept) => (
                  <option key={dept.department_id} value={dept.department_id}>
                    {dept.department_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Doctor Selection */}
            <div className="cancel-field-group">
              <label htmlFor="book-doctor-select" className="cancel-field-label">
                Assigned Doctor *
              </label>
              <select
                id="book-doctor-select"
                className="cancel-select-field"
                value={bookingForm.doctorId}
                onChange={(e) => handleBookingDoctorOrDateChange(e.target.value, bookingForm.appointmentDate)}
              >
                {metadata.doctors
                  .filter((d) => !bookingForm.departmentId || d.department_id === bookingForm.departmentId)
                  .map((d) => (
                    <option key={d.doctor_id} value={d.doctor_id}>
                      {d.doctor_name} ({d.department_name})
                    </option>
                  ))}
              </select>
            </div>

            {/* Date Picker */}
            <div className="cancel-field-group">
              <Input
                type="date"
                label="Appointment Date *"
                name="appointmentDate"
                value={bookingForm.appointmentDate}
                onChange={(e) => handleBookingDoctorOrDateChange(bookingForm.doctorId, e.target.value)}
              />
            </div>

            {/* Time Slot Picker */}
            <div className="cancel-field-group">
              <label className="cancel-field-label">
                Available Time Slots for Selected Doctor *
              </label>
              {loadingBookingSlots ? (
                <div style={{ padding: '0.5rem 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Loading doctor availability...
                </div>
              ) : bookingSlots.length === 0 ? (
                <div style={{ padding: '0.5rem 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  No slots found for this doctor and date.
                </div>
              ) : (
                <div className="reschedule-slots-grid">
                  {bookingSlots.map((slot) => {
                    const isBooked = slot.status === 'BOOKED';
                    const isSelected = slot.slot_time === bookingForm.appointmentTime;

                    return (
                      <button
                        key={slot.slot_time}
                        type="button"
                        className={`slot-choice-btn ${isSelected ? 'selected' : ''} ${isBooked ? 'disabled' : ''}`}
                        disabled={isBooked}
                        onClick={() => setBookingForm({ ...bookingForm, appointmentTime: slot.slot_time })}
                        title={isBooked ? 'Already reserved (overbooking prevented)' : 'Open time slot'}
                      >
                        {slot.slot_time}
                      </button>
                    );
                  })}
                </div>
              )}

              {isSelectedBookingSlotCollision && (
                <div className="slot-conflict-alert">
                  This time slot is already reserved. Overbooking or double-booking is strictly prevented. Please choose another slot.
                </div>
              )}
            </div>

            {/* Priority and Staff ID row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <div className="cancel-field-group">
                <label htmlFor="book-priority-select" className="cancel-field-label">
                  Priority Level
                </label>
                <select
                  id="book-priority-select"
                  className="cancel-select-field"
                  value={bookingForm.priority}
                  onChange={(e) => setBookingForm({ ...bookingForm, priority: e.target.value })}
                >
                  <option value="Normal">Normal</option>
                  <option value="Emergency">Emergency</option>
                  <option value="Senior">Senior</option>
                </select>
              </div>

              <div className="cancel-field-group">
                <Input
                  label="Staff ID *"
                  name="staffId"
                  value={bookingForm.staffId}
                  onChange={(e) => setBookingForm({ ...bookingForm, staffId: e.target.value })}
                />
              </div>
            </div>

            {/* Notes */}
            <div className="cancel-field-group">
              <Input
                label="Appointment / Clinical Notes"
                name="notes"
                placeholder="Reason for visit, symptoms, or special instructions"
                value={bookingForm.notes}
                onChange={(e) => setBookingForm({ ...bookingForm, notes: e.target.value })}
              />
            </div>
          </div>
        </Modal>
      </div>
    </StaffLayout>
  );
};

export default StaffDashboard;
