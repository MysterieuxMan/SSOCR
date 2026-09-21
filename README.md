# SSOCR - Seven Segment Optical Character Recognition Backend

FastAPI-powered REST API backend for Seven Segment Optical Character Recognition (SSOCR), specifically optimized for digital weighing indicators and scale displays (LED & LCD).

---

## Architecture & Features

- **FastAPI Engine**: High-performance asynchronous REST API with Swagger/OpenAPI documentation.
- **Polarity Detection**: Automatically identifies bright digits on dark background (LED displays) vs dark digits on light background (LCD displays).
- **Adaptive Image Pipeline**: Contrast Limited Adaptive Histogram Equalization (CLAHE), Gaussian blur, adaptive thresholding, and morphological opening/closing.
- **Slant & Angle Tolerance**: Segment extraction accounting for 7-segment slant angle ($\theta$).
- **Decimal Point & Sign Detection**: Detects decimal points (`.`) and negative signs (`-`).
- **Mobile Integration Ready**: Multipart form-data image upload compatible with Android CameraX / Retrofit.

---

## Requirements & Setup

### Using Miniconda / Virtualenv

```bash
# Activate your conda environment (e.g. miniconda)
conda activate <your-env>

# Install dependencies
pip install -r requirements.txt
```

### Run Backend Server

```bash
# Start FastAPI server via Uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Swagger API Docs**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

---

## API Endpoints

### 1. Health Check
- **Endpoint**: `GET /health`
- **Response**:
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

### 2. Recognize Weight
- **Endpoint**: `POST /api/v1/ocr/recognize`
- **Content-Type**: `multipart/form-data`
- **Parameter**: `file` (Image file: JPEG, PNG, or BMP)
- **Response**:
```json
{
  "success": true,
  "weight_text": "-30.37",
  "numeric_value": -30.37,
  "confidence": 1.0,
  "raw_digits": ["-", "3", "0", ".", "3", "7"],
  "processing_time_ms": 25.4,
  "message": "Recognition successful"
}
```

---

## Automated Tests

Run the test suite:

```bash
python -m unittest discover tests
```

---

## Android Client Integration

For the Android native application in `D:\Code\weight-OCR`:
- **Android Emulator**: `http://10.0.2.2:8000/`
- **Physical Device**: `http://<YOUR_LAN_IP>:8000/` (configurable in the app's Settings screen).