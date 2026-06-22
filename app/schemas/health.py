"""Health check response schemas."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    database: str
    redis: str
