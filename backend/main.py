from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.services.appointment.api.appointment_router import router as appointment_router
from backend.services.queue.api import queue_router
from backend.services.audit.api import audit_router
from backend.services.auth.api.auth_router import router as auth_router
from backend.services.user.api.user_router import router as user_router

app = FastAPI(
    title="Smart Hospital API",
    description="Smart Hospital Appointment & Queue Management API",
    version="1.0.0",
)

# Note: HTTPS is enforced in production via reverse proxy.
# Local development runs over HTTP to avoid certificate issues.

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global HTTPException handler conforming to standard response envelope
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail if isinstance(exc.detail, str) else "Request failed",
            "error": exc.detail if not isinstance(exc.detail, str) else {"detail": exc.detail},
        },
    )


# Include domain routers
app.include_router(auth_router)
app.include_router(appointment_router)
app.include_router(queue_router.router)
app.include_router(audit_router.router)
app.include_router(user_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
