from backend.services.appointment.api.appointment_router import router as appointment_router
from backend.services.appointment.services.appointment_service import appointment_service_instance

__all__ = ["appointment_router", "appointment_service_instance"]
