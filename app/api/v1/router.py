from fastapi import APIRouter
from app.api.v1.endpoints import ocr

api_router = APIRouter()
api_router.include_router(ocr.router)
