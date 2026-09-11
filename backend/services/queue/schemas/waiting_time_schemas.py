from pydantic import BaseModel, Field


class WaitTimeResponse(BaseModel):
    """Estimated waiting time details for a specific patient queue token."""
    token_id: str
    token_number: str
    patients_ahead: int = Field(..., description="Number of active patients ahead in the queue")
    average_consultation_minutes: float = Field(..., description="Average consultation duration used for computation")
    estimated_wait_minutes: int = Field(..., description="Computed estimated wait time in minutes")
    calculation_source: str = Field(..., description="Source: doctor_average, department_average, or default_benchmark")
    doctor_id: str
    department_id: str
