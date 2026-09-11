# Technical Contracts and Development Standards

This document defines the common technical rules and contracts for the Smart Hospital Appointment & Queue Management System. All developers must follow these standards.

## 1. Project Technical Baseline
- **Frontend**: React, Vite, JavaScript/JSX
- **Backend**: Python, FastAPI
- **Architecture**: Microservices-oriented architecture
- **API**: REST API
- **Real-time communication**: WebSocket (To be implemented later)
- **Authentication**: JWT + Refresh Token (To be implemented later)
- **Hosting**: AWS EC2
- **Storage**: AWS-based storage (Exact service: TBD)
- **Security**: HTTPS/TLS, Audit logging, Data masking where required
- **Version Control**: GitHub (`main`, `develop`, feature branches)

## 2. Module Boundaries
- **Auth Service**: Login/authentication, JWT/refresh token handling (later), Role-based access control, Authorization.
- **Patient Service**: Patient registration, Patient profile, Patient check-in related operations.
- **Appointment Service**: Appointment booking, modification, cancellation, and status.
- **Queue Service**: Token generation, Queue management, Queue prioritization, Doctor allocation operations, Waiting time, Queue status, No-show, Queue abandonment, Operational timestamps.

## 3. Data Naming Standards
- **Backend (Python)**: `snake_case` for variables and functions. `PascalCase` for classes.
- **Frontend (React)**: `PascalCase` for React components. `camelCase` for variables and functions.
- **API Fields**: Use consistent `snake_case` for API request/response fields to align frontend and backend.
  - Examples: `patient_id`, `appointment_id`, `doctor_id`, `created_at`, `updated_at`.
- *Note: Developers must not independently rename fields across boundaries.*

## 4. Common API Response Format
All REST API responses must follow this standard structure:

**Success Example:**
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {}
}
```

**Error Example:**
```json
{
  "success": false,
  "message": "Request failed",
  "error": {}
}
```

## 5. Common Error Handling
Backend services must use standard HTTP status codes:
- `200` → Successful request
- `201` → Resource created
- `400` → Invalid request
- `401` → Unauthenticated
- `403` → Unauthorized
- `404` → Resource not found
- `409` → Conflict
- `422` → Validation error
- `500` → Internal server error

## 6. Request Validation
- All API input must be validated before business processing.
- Backend validation is handled using FastAPI/Pydantic schemas.
- Developers must NOT directly trust client input.

## 7. Basic Data Contracts
Conceptual data fields required for communication between modules.

**USER**
- `user_id`
- `employee_id`
- `role`

**PATIENT**
- `patient_id`
- `first_name`
- `last_name`
- `date_of_birth`
- `gender`
- `phone`
- `address`

**APPOINTMENT**
- `appointment_id`
- `patient_id`
- `doctor_id`
- `department_id`
- `appointment_date`
- `appointment_time`
- `status`

**QUEUE/TOKEN**
- `token_id`
- `token_number`
- `patient_id`
- `doctor_id`
- `department_id`
- `priority`
- `status`
- `created_at`

**DOCTOR**
- `doctor_id`
- `department_id`
- `availability/status`

*Note: Database tables and models are TBD based on the final storage solution.*

## 8. Queue Business Rules
- **Queue States**: Waiting → Called → In Consultation → Completed
- Emergency patients always have the highest priority.
- Token numbers are generated automatically when a patient enters the queue.
- Queue status must be updated consistently.
- Operational timestamps must be captured.
- No-show and queue abandonment are treated as separate queue outcomes.

## 9. Doctor Allocation Contract
Staff selects the final doctor. The system logic flow:
1. Identify eligible doctors.
2. Check selected department.
3. Check doctor schedule.
4. Check doctor attendance/availability.
5. Exclude doctors not available for new allocation.
6. Consider current workload/queue.
7. Rank eligible doctors by lower estimated delay.
8. Display the ranked list to Staff.
9. Staff makes the final selection.

*Note: The exact estimated-delay formula and weighting are TBD.*

## 10. Frontend-Backend Communication
**Standard Request Flow:**
`React Frontend` → `REST API` → `FastAPI Services` → `AWS-based Storage (TBD)`

**Future Real-Time Flow:**
`React Frontend` ↔ `WebSocket` ↔ `Queue Service`
*(WebSocket implementation details: TBD)*

## 11. Authorization Expectations
Access control will be managed via Authentication, Role-based access control, and Authorization.

**Confirmed Roles:**
1. Administrator
2. Reception / Staff
3. Doctor
4. Laboratory / Pathology Staff
5. Management

*(Exact JWT, password-reset, and auth implementation details: TBD)*

## 12. Common Timestamp Rule
Operational timestamps must use a consistent format. Standard timestamp fields:
- `created_at`
- `updated_at`
- `check_in_time`
- `queue_entry_time`
- `consultation_start_time`
- `consultation_end_time`

## 13. Frontend Structure Rule
Strict separation of frontend responsibilities in `frontend/src/`:
- `components/`: Reusable UI components.
- `pages/`: Application screens/pages.
- `layouts/`: Common page layouts.
- `services/`: Frontend API communication.
- `hooks/`: Reusable React hooks.
- `utils/`: Reusable helper functions.
- `constants/`: Shared constants.
- `assets/`: Images/static frontend assets.

## 14. Backend Structure Rule
Strict separation of service responsibilities in `backend/services/`:
- `api/`: API routes/controllers.
- `schemas/`: Request/response validation schemas.
- `services/`: Business/service logic.
- `models/`: Data/domain models (When domain model is finalized - TBD).

## 15. Common Code Rule
Reusable functionality must be placed in `backend/common/` to avoid duplication.
- `common/exceptions/`
- `common/middleware/`
- `common/schemas/`
- `common/utils/`

Code specific to a business module must remain inside that service's folder.

## 16. File Ownership Rule
Developers modify files within their assigned feature/service branches. 
Modifications to shared files (`backend/main.py`, `backend/common/*`, `frontend/src/App.jsx`, `frontend/src/services/*`) should be avoided unnecessarily and must be justified in Pull Requests.

## 17. Git Development Rule
Workflow strictly follows:
`develop` → `feature branch` → `development` → `testing` → `commit` → `push` → `Pull Request to develop` → `Tech Lead review` → `approve/request changes` → `merge`.
