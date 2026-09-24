from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "SSOCR Seven-Segment OCR API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # CORS settings (allow all for mobile client connectivity during development)
    CORS_ORIGINS: List[str] = ["*"]
    
    # OCR Engine default parameters
    ADAPTIVE_THRESHOLD: int = 35
    CLAHE_CLIP_LIMIT: float = 2.0
    CLAHE_TILE_GRID_SIZE: int = 6
    SLANT_ANGLE_COT: float = 6.0

    # Azure Entra ID & Microsoft Graph configuration (Option 1 - Client Credentials Flow)
    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""
    AZURE_AUTHORITY_HOST: str = "https://login.microsoftonline.com"
    GRAPH_API_BASE_URL: str = "https://graph.microsoft.com/v1.0"

    # Default OneDrive Excel Workbook target
    EXCEL_DEFAULT_DRIVE_ID: str = ""
    EXCEL_DEFAULT_ITEM_ID: str = ""
    EXCEL_DEFAULT_TABLE_NAME: str = "WeighingTable"
    EXCEL_DEFAULT_USER_EMAIL: str = ""  # Used when accessing /users/{user-email}/drive

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")


settings = Settings()

