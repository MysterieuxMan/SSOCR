import base64
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import httpx
import msal

from app.core.config import settings

logger = logging.getLogger("OneDriveService")


class OneDriveService:
    """Service to interact with Microsoft Graph API using Client Credentials Flow (Option 1).
    Allows appending rows to OneDrive / SharePoint Excel workbooks without interactive user login.
    """

    def __init__(self):
        self._msal_app: Optional[msal.ConfidentialClientApplication] = None
        self._sharing_cache: Dict[str, Tuple[str, str]] = {}

    def _get_msal_app(self) -> msal.ConfidentialClientApplication:
        if not settings.AZURE_TENANT_ID or not settings.AZURE_CLIENT_ID or not settings.AZURE_CLIENT_SECRET:
            raise ValueError(
                "Azure Entra ID credentials (AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET) "
                "are not configured in backend settings or .env file."
            )

        if self._msal_app is None:
            authority = f"{settings.AZURE_AUTHORITY_HOST.rstrip('/')}/{settings.AZURE_TENANT_ID}"
            self._msal_app = msal.ConfidentialClientApplication(
                client_id=settings.AZURE_CLIENT_ID,
                client_credential=settings.AZURE_CLIENT_SECRET,
                authority=authority,
            )
        return self._msal_app

    def get_access_token(self) -> str:
        """Acquires a valid Microsoft Graph application token via Client Credentials."""
        app = self._get_msal_app()
        scopes = ["https://graph.microsoft.com/.default"]

        # 1. Try silent / cached token
        result = app.acquire_token_silent(scopes=scopes, account=None)
        if result and "access_token" in result:
            return result["access_token"]

        # 2. Acquire new token via Client Credentials
        result = app.acquire_token_for_client(scopes=scopes)
        if "access_token" in result:
            logger.info("Successfully acquired Microsoft Graph application access token.")
            return result["access_token"]

        error_desc = result.get("error_description", result.get("error", "Unknown token acquisition error"))
        logger.error(f"Failed to acquire Microsoft Graph token: {error_desc}")
        raise RuntimeError(f"Microsoft Entra ID authentication failed: {error_desc}")

    @staticmethod
    def encode_sharing_url(sharing_url: str) -> str:
        """Encodes a OneDrive/SharePoint sharing URL according to Microsoft Graph specs:
        base64url encoding without padding, prepended with 'u!'.
        """
        trimmed = sharing_url.strip()
        encoded = base64.urlsafe_b64encode(trimmed.encode("utf-8")).decode("utf-8")
        unpadded = encoded.rstrip("=")
        return f"u!{unpadded}"

    async def resolve_sharing_url(self, client: httpx.AsyncClient, token: str, sharing_url: str) -> Tuple[str, str]:
        """Resolves a sharing link to (drive_id, item_id)."""
        share_token = self.encode_sharing_url(sharing_url)
        if share_token in self._sharing_cache:
            return self._sharing_cache[share_token]

        headers = {"Authorization": f"Bearer {token}"}
        url = f"{settings.GRAPH_API_BASE_URL}/shares/{share_token}/driveItem"
        
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to resolve share link: {response.status_code} - {response.text}")
            raise RuntimeError(
                f"Gagal mengakses link sharing OneDrive ({response.status_code}): "
                f"Pastikan link dibagikan dengan hak akses edit dan izin Files.ReadWrite.All telah disetujui admin."
            )

        data = response.json()
        drive_id = data.get("parentReference", {}).get("driveId")
        item_id = data.get("id")

        if not drive_id or not item_id:
            raise RuntimeError("Metadata driveId atau itemId tidak ditemukan dari response sharing link.")

        self._sharing_cache[share_token] = (drive_id, item_id)
        return drive_id, item_id

    async def append_row_to_excel(
        self,
        row_values: List[Any],
        table_name: Optional[str] = None,
        drive_id: Optional[str] = None,
        item_id: Optional[str] = None,
        sharing_url: Optional[str] = None,
        file_path: Optional[str] = None,
        user_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Appends a row to an Excel table in OneDrive/SharePoint via Microsoft Graph API."""
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        tbl_name = table_name or settings.EXCEL_DEFAULT_TABLE_NAME or "WeighingTable"
        target_drive_id = drive_id or settings.EXCEL_DEFAULT_DRIVE_ID
        target_item_id = item_id or settings.EXCEL_DEFAULT_ITEM_ID
        target_user_email = user_email or settings.EXCEL_DEFAULT_USER_EMAIL

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Determine API URL endpoint
            if sharing_url:
                resolved_drive_id, resolved_item_id = await self.resolve_sharing_url(client, token, sharing_url)
                api_url = (
                    f"{settings.GRAPH_API_BASE_URL}/drives/{resolved_drive_id}/items/"
                    f"{resolved_item_id}/workbook/tables/{tbl_name}/rows/add"
                )
            elif target_drive_id and target_item_id:
                api_url = (
                    f"{settings.GRAPH_API_BASE_URL}/drives/{target_drive_id}/items/"
                    f"{target_item_id}/workbook/tables/{tbl_name}/rows/add"
                )
            elif target_user_email and file_path:
                cleaned_path = file_path.strip().lstrip("/")
                api_url = (
                    f"{settings.GRAPH_API_BASE_URL}/users/{target_user_email}/drive/root:/{cleaned_path}:"
                    f"/workbook/tables/{tbl_name}/rows/add"
                )
            elif target_user_email and target_item_id:
                api_url = (
                    f"{settings.GRAPH_API_BASE_URL}/users/{target_user_email}/drive/items/"
                    f"{target_item_id}/workbook/tables/{tbl_name}/rows/add"
                )
            else:
                raise ValueError(
                    "Target Excel tidak lengkap. Harap sertakan `sharing_url`, atau kombinasi "
                    "(`drive_id` + `item_id`), atau (`user_email` + `file_path`)."
                )

            body = {"values": [row_values]}
            logger.info(f"Sending POST to Microsoft Graph: {api_url}")
            response = await client.post(api_url, headers=headers, json=body)

            if response.status_code in (200, 201):
                logger.info(f"Successfully added row to Excel table '{tbl_name}'.")
                return response.json()

            error_text = response.text
            logger.error(f"Error from Microsoft Graph ({response.status_code}): {error_text}")
            raise RuntimeError(f"Microsoft Graph API Error ({response.status_code}): {error_text}")


onedrive_service = OneDriveService()
