"""
Seven-Segment Display Optical Character Recognition (SSOCR) Engine.

Processes images of 7-segment digital scale indicators to recognize digits,
negative signs, and decimal points using OpenCV computer vision techniques.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np


# Segment order:
# 0: Top-Right
# 1: Bottom-Right
# 2: Bottom
# 3: Bottom-Left
# 4: Top-Left
# 5: Top
# 6: Center
CANONICAL_LOOKUP: Dict[Tuple[int, ...], str] = {
    (1, 1, 1, 1, 1, 1, 0): "0",
    (1, 1, 0, 0, 0, 0, 0): "1",
    (0, 0, 0, 0, 1, 1, 0): "1",  # Left-aligned 1
    (1, 0, 1, 1, 0, 1, 1): "2",
    (1, 1, 1, 0, 0, 1, 1): "3",
    (1, 1, 0, 0, 1, 0, 1): "4",
    (0, 1, 1, 0, 1, 1, 1): "5",
    (0, 1, 1, 1, 1, 1, 1): "6",
    (1, 0, 1, 1, 1, 1, 1): "6",  # Alternative 6
    (1, 1, 0, 0, 0, 1, 0): "7",
    (1, 1, 1, 0, 0, 0, 0): "7",  # Alternative 7
    (1, 1, 1, 1, 1, 1, 1): "8",
    (1, 1, 1, 0, 1, 1, 1): "9",
    (1, 1, 1, 1, 0, 1, 1): "9",  # Alternative 9
    (0, 0, 0, 0, 0, 1, 1): "-",
    (0, 0, 0, 0, 0, 0, 1): "-",
}


@dataclass
class OcrEngineResult:
    weight_text: str
    numeric_value: Optional[float]
    confidence: float
    raw_symbols: List[str]
    is_valid: bool


class SevenSegmentOcrEngine:
    """
    Robust 7-Segment OCR engine adapted from classical SSOCR pipeline
    with polarity detection, slant tolerance, and decimal point extraction.
    """

    def __init__(
        self,
        adaptive_threshold: int = 35,
        h_w_ratio: float = 1.9,
        slant_cot_theta: float = 6.0,
        clahe_clip_limit: float = 2.0,
        clahe_tile_grid: int = 6,
    ):
        self.adaptive_threshold = adaptive_threshold
        self.h_w_ratio = h_w_ratio
        self.slant_cot_theta = slant_cot_theta
        self.clahe_clip_limit = clahe_clip_limit
        self.clahe_tile_grid = clahe_tile_grid

    def decode_image_bytes(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """Decodes raw byte array into OpenCV BGR numpy array."""
        if not image_bytes or len(image_bytes) == 0:
            return None
        nparr = np.frombuffer(image_bytes, np.uint8)
        if nparr.size == 0:
            return None
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img

    def detect_dark_background(self, gray: np.ndarray) -> bool:
        """Determines whether image has a dark background (LED) or light background (LCD)."""
        h, w = gray.shape
        border_samples = []
        step_x = max(1, w // 20)
        step_y = max(1, h // 20)

        for x in range(0, w, step_x):
            border_samples.append(int(gray[0, x]))
            border_samples.append(int(gray[h - 1, x]))
        for y in range(0, h, step_y):
            border_samples.append(int(gray[y, 0]))
            border_samples.append(int(gray[y, w - 1]))

        avg_border = float(np.mean(border_samples)) if border_samples else 128.0
        return avg_border < 120.0

    def preprocess(self, gray: np.ndarray, is_dark_bg: bool) -> np.ndarray:
        """
        Enhances contrast and binarizes image so that active digits are white (255)
        and inactive background is black (0).
        """
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        clahe = cv2.createCLAHE(
            clipLimit=self.clahe_clip_limit,
            tileGridSize=(self.clahe_tile_grid, self.clahe_tile_grid),
        )
        equalized = clahe.apply(blurred)

        # For light LCD, invert so dark digits become white.
        # For dark LED, direct binary so bright digits become white.
        thresh_flag = cv2.THRESH_BINARY if is_dark_bg else cv2.THRESH_BINARY_INV
        dst = cv2.adaptiveThreshold(
            equalized,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            thresh_flag,
            127,
            self.adaptive_threshold,
        )

        kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (5, 5))
        dst = cv2.morphologyEx(dst, cv2.MORPH_CLOSE, kernel)
        dst = cv2.morphologyEx(dst, cv2.MORPH_OPEN, kernel)
        return dst

    def _helper_extract(
        self, one_d_array: np.ndarray, threshold: int = 20
    ) -> List[Tuple[int, int]]:
        """Extracts continuous active ranges along 1D projection array."""
        res: List[Tuple[int, int]] = []
        flag = 0
        temp = 0
        for i in range(len(one_d_array)):
            if one_d_array[i] < 12 * 255:
                if flag > threshold:
                    start = i - flag
                    end = i
                    temp = end
                    if end - start > 20:
                        res.append((start, end))
                flag = 0
            else:
                flag += 1
        if flag > threshold:
            start = temp
            end = len(one_d_array)
            if end - start > 50:
                res.append((start, end))
        return res

    def find_digits_positions(
        self, img: np.ndarray, reserved_threshold: int = 20
    ) -> List[List[Tuple[int, int]]]:
        """
        Finds bounding boxes for candidate digits using horizontal and vertical projection profiles.
        """
        digits_positions: List[List[Tuple[int, int]]] = []
        img_array_x = np.sum(img, axis=0)
        horizon_position = self._helper_extract(
            img_array_x, threshold=reserved_threshold
        )

        img_array_y = np.sum(img, axis=1)
        vertical_position = self._helper_extract(
            img_array_y, threshold=reserved_threshold * 4
        )

        if not vertical_position or not horizon_position:
            # Fallback: attempt connected components bounding boxes if projection is sparse
            return self._find_positions_contours(img)

        if len(vertical_position) > 1:
            vertical_position = [
                (vertical_position[0][0], vertical_position[-1][1])
            ]

        for h in horizon_position:
            for v in vertical_position:
                digits_positions.append(list(zip(h, v)))

        return digits_positions

    def _find_positions_contours(
        self, img: np.ndarray
    ) -> List[List[Tuple[int, int]]]:
        """Fallback bounding box locator using OpenCV contours."""
        h, w = img.shape
        contours, _ = cv2.findContours(
            img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        boxes = []
        min_h = int(h * 0.25)
        for c in contours:
            bx, by, bw, bh = cv2.boundingRect(c)
            if bh >= min_h and bw >= 8:
                boxes.append([(bx, by), (bx + bw, by + bh)])
        boxes.sort(key=lambda b: b[0][0])
        return boxes

    def _match_digit_pattern(self, on: List[int]) -> Tuple[str, float]:
        """Matches segment on/off vector to CANONICAL_LOOKUP with exact lookup."""
        key = tuple(on)
        if key in CANONICAL_LOOKUP:
            return CANONICAL_LOOKUP[key], 1.0
        return "*", 0.0

    def recognize_positions(
        self, digits_positions: List[List[Tuple[int, int]]], thresh_img: np.ndarray
    ) -> Tuple[List[str], float]:
        """
        Samples the 7 segments of each candidate bounding box, classifies digits,
        and detects potential decimal points.
        """
        digits: List[str] = []
        confidences: List[float] = []

        for c in digits_positions:
            x0, y0 = c[0]
            x1, y1 = c[1]
            roi = thresh_img[y0:y1, x0:x1]
            h, w = roi.shape
            if h <= 0 or w <= 0:
                continue

            # Determine actual content vertical bounds within the ROI
            pts = cv2.findNonZero(roi)
            if pts is None:
                continue
            _, actual_by, _, actual_bh = cv2.boundingRect(pts)
            eff_h = actual_by + actual_bh

            suppose_w = max(1, int(h / self.h_w_ratio))
            orig_w = w

            # Filter out tiny noise contours
            roi_area = float((y1 - y0) * (x1 - x0))
            if x1 - x0 < 25 and (cv2.countNonZero(roi) / max(1.0, roi_area)) < 0.20:
                continue

            # Filter small isolated dirt/dust specks inside digit cavity (keeps decimal dots in bottom-right)
            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(roi)
            clean_roi = np.zeros_like(roi)
            for li in range(1, num_labels):
                area = stats[li, cv2.CC_STAT_AREA]
                cw = stats[li, cv2.CC_STAT_WIDTH]
                ch = stats[li, cv2.CC_STAT_HEIGHT]
                cx = stats[li, cv2.CC_STAT_LEFT]
                cy = stats[li, cv2.CC_STAT_TOP]
                if area < 500 and cw < 30 and ch < 30 and not (cy > 0.60 * h and cx > 0.45 * w):
                    continue
                clean_roi[labels == li] = 255

            # Handle narrow digit '1' width adjustment
            if w < suppose_w / 2:
                x0_adj = max(x0 + w - suppose_w, 0)
                clean_roi_adj = np.zeros((h, x1 - x0_adj), dtype=np.uint8)
                clean_roi_adj[:, (x1 - x0_adj) - w:] = clean_roi
                clean_roi = clean_roi_adj
                w = clean_roi.shape[1]

            center_y = h // 2
            quater_y_1 = h // 4
            quater_y_3 = quater_y_1 * 3
            center_x = w // 2
            line_width = 5
            width = (max(int(w * 0.15), 1) + max(int(h * 0.15), 1)) // 2
            small_delta = int(h / self.slant_cot_theta) // 4

            segments = [
                ((w - 2 * width, quater_y_1 - line_width), (w, quater_y_1 + line_width)),  # 0: Top-Right
                ((w - 2 * width, quater_y_3 - line_width), (w, quater_y_3 + line_width)),  # 1: Bottom-Right
                ((center_x - line_width - small_delta, h - 2 * width), (center_x - small_delta + line_width, h)),  # 2: Bottom
                ((0, quater_y_3 - line_width), (2 * width, quater_y_3 + line_width)),  # 3: Bottom-Left
                ((0, quater_y_1 - line_width), (2 * width, quater_y_1 + line_width)),  # 4: Top-Left
                ((center_x - line_width, 0), (center_x + line_width, 2 * width)),  # 5: Top
                ((center_x - line_width, center_y - line_width), (center_x + line_width, center_y + line_width)),  # 6: Center
            ]

            on = [0] * len(segments)
            for i, ((xa, ya), (xb, yb)) in enumerate(segments):
                xa_c = max(0, min(w, xa))
                xb_c = max(0, min(w, xb))
                ya_c = max(0, min(h, ya))
                yb_c = max(0, min(h, yb))

                if xb_c <= xa_c or yb_c <= ya_c:
                    continue

                seg_roi = clean_roi[ya_c:yb_c, xa_c:xb_c]
                total = cv2.countNonZero(seg_roi)
                area = (xb_c - xa_c) * (yb_c - ya_c) * 0.90
                # Balanced cutoff for vertical vs horizontal segments
                cutoff = 0.20 if i in (0, 1, 2, 3, 4) else (0.23 if i == 5 else 0.25)
                if area > 0 and (total / float(area)) > cutoff:
                    on[i] = 1

            digit, conf = self._match_digit_pattern(on)
            digits.append(digit)
            confidences.append(conf)

            # Decimal point detection at the bottom right corner of the digit ROI using effective content height
            if digit in "0123456789":
                dot_roi_y0 = max(0, eff_h - int(3 * width / 4))
                dot_roi_x0 = max(0, w - int(3 * width / 4))
                dot_roi = roi[dot_roi_y0:eff_h, dot_roi_x0:w]
                dot_area = (9.0 / 16.0) * width * width
                if dot_area > 0 and dot_roi.size > 0:
                    dot_density = cv2.countNonZero(dot_roi) / float(dot_area)
                    if dot_density > 0.55:
                        digits.append(".")
                        confidences.append(1.0)

        avg_conf = float(np.mean(confidences)) if confidences else 0.0
        return digits, avg_conf

    def format_recognized_symbols(
        self, symbols: List[str]
    ) -> Tuple[str, Optional[float]]:
        """
        Cleans up raw symbol list by stripping edge noise, formatting numeric string,
        and computing floating-point value.
        """
        # Remove noise indicators (e.g. '*' boundary symbols) from leading/trailing edges
        filtered = [s for s in symbols if s in "0123456789.-"]
        if not filtered:
            return "", None

        # Consolidate duplicate decimal points
        cleaned: List[str] = []
        has_dot = False
        for s in filtered:
            if s == ".":
                if not has_dot and cleaned:
                    cleaned.append(s)
                    has_dot = True
            elif s == "-":
                if not cleaned:
                    cleaned.append(s)
            else:
                cleaned.append(s)

        text = "".join(cleaned).strip()
        try:
            val = float(text) if any(c.isdigit() for c in text) else None
        except ValueError:
            val = None

        return text, val

    def process_image(self, image_bytes: bytes) -> OcrEngineResult:
        """
        Executes complete OCR pipeline from byte stream to structured result.
        """
        bgr = self.decode_image_bytes(image_bytes)
        if bgr is None:
            return OcrEngineResult(
                weight_text="",
                numeric_value=None,
                confidence=0.0,
                raw_symbols=[],
                is_valid=False,
            )

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        is_dark_bg = self.detect_dark_background(gray)
        thresh = self.preprocess(gray, is_dark_bg)

        positions = self.find_digits_positions(thresh)
        if not positions:
            return OcrEngineResult(
                weight_text="",
                numeric_value=None,
                confidence=0.0,
                raw_symbols=[],
                is_valid=False,
            )

        symbols, conf = self.recognize_positions(positions, thresh)
        text, num_val = self.format_recognized_symbols(symbols)

        return OcrEngineResult(
            weight_text=text,
            numeric_value=num_val,
            confidence=conf if num_val is not None else 0.0,
            raw_symbols=symbols,
            is_valid=(num_val is not None),
        )


ocr_engine = SevenSegmentOcrEngine()
