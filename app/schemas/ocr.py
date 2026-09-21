from typing import List, Optional
from pydantic import BaseModel, Field


class OcrCandidateDto(BaseModel):
    weight: float
    formatted_weight: str
    detected_unit: Optional[str] = "kg"
    confidence: float = 1.0


class OcrResponse(BaseModel):
    success: bool = Field(..., description="Whether OCR processing succeeded")
    weight_text: str = Field(..., description="Recognized weight string, e.g. '12.345'")
    numeric_value: Optional[float] = Field(None, description="Parsed floating-point weight value")
    confidence: float = Field(..., description="Estimated confidence score between 0.0 and 1.0")
    raw_digits: List[str] = Field(default_factory=list, description="List of recognized individual symbols")
    processing_time_ms: float = Field(..., description="Execution time in milliseconds")
    message: Optional[str] = Field(None, description="Optional informational or warning message")


class HealthResponse(BaseModel):
    status: str
    version: str
