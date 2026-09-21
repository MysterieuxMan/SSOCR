import time
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from app.schemas.ocr import OcrResponse
from app.services.ocr_engine import ocr_engine

router = APIRouter(prefix="/ocr", tags=["Seven-Segment OCR"])

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/bmp",
    "image/webp",
    "application/octet-stream",
}


@router.post(
    "/recognize",
    response_model=OcrResponse,
    status_code=status.HTTP_200_OK,
    summary="Recognize weight from a digital 7-segment display image",
    description=(
        "Upload a photograph or captured frame of a seven-segment digital scale display. "
        "The engine performs preprocessing, segment localization, and 7-segment classification "
        "to return the detected weight string and numeric value."
    ),
)
async def recognize_weight(
    file: UploadFile = File(..., description="Image file (JPEG, PNG, or BMP)")
) -> OcrResponse:
    start_time = time.perf_counter()

    # Basic content type check
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported media type '{file.content_type}'. Please upload an image file.",
        )

    try:
        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )

        result = ocr_engine.process_image(content)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        if not result.is_valid and not result.weight_text:
            return OcrResponse(
                success=False,
                weight_text="",
                numeric_value=None,
                confidence=0.0,
                raw_digits=result.raw_symbols,
                processing_time_ms=round(elapsed_ms, 2),
                message="No valid 7-segment digits could be identified in the image.",
            )

        return OcrResponse(
            success=True,
            weight_text=result.weight_text,
            numeric_value=result.numeric_value,
            confidence=round(result.confidence, 3),
            raw_digits=result.raw_symbols,
            processing_time_ms=round(elapsed_ms, 2),
            message="Recognition successful",
        )
    except HTTPException:
        raise
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return OcrResponse(
            success=False,
            weight_text="",
            numeric_value=None,
            confidence=0.0,
            raw_digits=[],
            processing_time_ms=round(elapsed_ms, 2),
            message=f"Recognition failed due to internal error: {str(exc)}",
        )
