from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class WeighingSyncRequest(BaseModel):
    record_id: Optional[str] = Field(default=None, description="Unique record ID. Generated if not provided.")
    weight: float = Field(..., description="Captured weighing value.")
    unit: str = Field(default="kg", description="Unit of measurement (e.g., kg, g, lbs).")
    captured_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 string or formatted datetime when the weight was captured.",
    )
    raw_text: Optional[str] = Field(default=None, description="Original raw OCR text detected.")
    
    # Optional destination overrides (if not using backend default settings)
    drive_id: Optional[str] = Field(default=None, description="OneDrive / SharePoint Drive ID.")
    item_id: Optional[str] = Field(default=None, description="Excel file Item ID in OneDrive.")
    sharing_url: Optional[str] = Field(default=None, description="OneDrive / SharePoint sharing URL.")
    file_path: Optional[str] = Field(default=None, description="Relative file path in user drive.")
    table_name: Optional[str] = Field(default=None, description="Excel Table Name (e.g. WeighingTable).")
    user_email: Optional[str] = Field(default=None, description="Target Microsoft 365 user email.")


class WeighingSyncResponse(BaseModel):
    success: bool
    message: str
    record_id: str
    synced_at: str
    details: Optional[Dict[str, Any]] = None


class ExcelConnectionStatusResponse(BaseModel):
    configured: bool
    tenant_id_set: bool
    client_id_set: bool
    client_secret_set: bool
    auth_status: str
    message: str
