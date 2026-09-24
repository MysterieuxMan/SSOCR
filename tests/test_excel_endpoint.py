import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.onedrive_service import OneDriveService

client = TestClient(app)


def test_excel_status_unconfigured():
    """When credentials are not set, /excel/status should report not configured."""
    with patch("app.core.config.settings.AZURE_TENANT_ID", ""), \
         patch("app.core.config.settings.AZURE_CLIENT_ID", ""), \
         patch("app.core.config.settings.AZURE_CLIENT_SECRET", ""):
        response = client.get("/api/v1/excel/status")
        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is False
        assert data["auth_status"] == "Not Configured"


def test_excel_encode_sharing_url():
    """Verify standard base64url encoding for Microsoft Graph sharing URLs."""
    url = "https://1drv.ms/x/s!AnZ12345678"
    encoded = OneDriveService.encode_sharing_url(url)
    assert encoded.startswith("u!")
    assert "=" not in encoded
    assert "/" not in encoded
    assert "+" not in encoded


@pytest.mark.asyncio
async def test_excel_append_row_success():
    """Test successful row append with mocked OneDriveService."""
    mock_details = {"id": "row-123", "values": [["REC-001", "2026-09-24", "10:00:00", 12.5, "kg", "Synced"]]}
    
    with patch(
        "app.api.v1.endpoints.excel.onedrive_service.append_row_to_excel",
        new_callable=AsyncMock,
        return_value=mock_details,
    ):
        payload = {
            "record_id": "REC-001",
            "weight": 12.5,
            "unit": "kg",
            "captured_at": "2026-09-24T10:00:00Z",
            "sharing_url": "https://1drv.ms/x/s!AnZ12345678",
            "table_name": "WeighingTable",
        }
        response = client.post("/api/v1/excel/append-row", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["record_id"] == "REC-001"
        assert data["details"] == mock_details
