import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.schemas.excel import (
    ExcelConnectionStatusResponse,
    WeighingSyncRequest,
    WeighingSyncResponse,
)
from app.services.onedrive_service import onedrive_service

logger = logging.getLogger("ExcelEndpoint")
router = APIRouter()


@router.get(
    "/status",
    response_model=ExcelConnectionStatusResponse,
    summary="Check Azure Entra ID and OneDrive integration status",
)
def get_excel_integration_status() -> ExcelConnectionStatusResponse:
    """Checks whether the backend is configured with Azure Entra ID credentials for Option 1 (Headless)."""
    tenant_set = bool(settings.AZURE_TENANT_ID and settings.AZURE_TENANT_ID.strip())
    client_set = bool(settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_ID.strip())
    secret_set = bool(settings.AZURE_CLIENT_SECRET and settings.AZURE_CLIENT_SECRET.strip())

    configured = tenant_set and client_set and secret_set

    if not configured:
        return ExcelConnectionStatusResponse(
            configured=False,
            tenant_id_set=tenant_set,
            client_id_set=client_set,
            client_secret_set=secret_set,
            auth_status="Not Configured",
            message="Kredensial Azure Entra ID belum lengkap di .env backend. Harap isi AZURE_TENANT_ID, AZURE_CLIENT_ID, dan AZURE_CLIENT_SECRET.",
        )

    try:
        # Test token acquisition
        token = onedrive_service.get_access_token()
        return ExcelConnectionStatusResponse(
            configured=True,
            tenant_id_set=tenant_set,
            client_id_set=client_set,
            client_secret_set=secret_set,
            auth_status="Authenticated",
            message="Backend berhasil terhubung ke Microsoft Entra ID (Client Credentials) dan siap menyinkronkan data.",
        )
    except Exception as e:
        logger.warning(f"Failed to acquire token during status check: {e}")
        return ExcelConnectionStatusResponse(
            configured=True,
            tenant_id_set=tenant_set,
            client_id_set=client_set,
            client_secret_set=secret_set,
            auth_status="Error",
            message=f"Kredensial terisi tetapi gagal otentikasi ke Microsoft: {str(e)}",
        )


@router.post(
    "/append-row",
    response_model=WeighingSyncResponse,
    summary="Append a weighing record to Excel OneDrive table (Option 1: No User Login)",
)
async def append_weighing_row(request: WeighingSyncRequest) -> WeighingSyncResponse:
    """Receives a weighing record from the mobile app / client and inserts it into the
    specified OneDrive Excel table via Microsoft Graph API without requiring user login.
    """
    record_id = request.record_id or f"REC-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now()

    # Parse or format captured_at
    if request.captured_at:
        try:
            # Try parsing ISO
            dt = datetime.fromisoformat(request.captured_at.replace("Z", "+00:00"))
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M:%S")
        except Exception:
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")
    else:
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

    # Excel row values: [ID, Tanggal, Waktu, Berat, Unit, Status]
    row_values = [
        record_id,
        date_str,
        time_str,
        request.weight,
        request.unit,
        "Synced",
    ]

    try:
        details = await onedrive_service.append_row_to_excel(
            row_values=row_values,
            table_name=request.table_name,
            drive_id=request.drive_id,
            item_id=request.item_id,
            sharing_url=request.sharing_url,
            file_path=request.file_path,
            user_email=request.user_email,
        )

        return WeighingSyncResponse(
            success=True,
            message="Record timbangan berhasil disinkronkan ke Excel OneDrive via Backend (Opsi 1).",
            record_id=record_id,
            synced_at=now.isoformat(),
            details=details,
        )
    except ValueError as ve:
        logger.error(f"Configuration or input error: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"Failed to append row to OneDrive Excel: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gagal menyinkronkan data ke Microsoft Graph API: {str(e)}",
        )
