from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.services.appointment.api.appointment_router import router as appointment_router
from backend.services.queue.api.queue_router import router as queue_router

app = FastAPI(
    title="Smart Hospital API",
    description="Smart Hospital Appointment & Queue Management API",
    version="1.0.0",
)

# CORS middleware for frontend communication
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
app.include_router(appointment_router)
app.include_router(queue_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
