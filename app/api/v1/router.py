from fastapi import APIRouter
from app.api.v1.endpoints import excel, ocr

api_router = APIRouter()
api_router.include_router(ocr.router)
api_router.include_router(excel.router, prefix="/excel", tags=["Excel OneDrive (Option 1)"])

