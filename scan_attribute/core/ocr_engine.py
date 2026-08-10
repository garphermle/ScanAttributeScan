"""
OCR Engine using RapidOCR for instant crop-snippet text extraction.
Handles color space conversions (RGBA/RGB -> BGR) and smart image sharpening for high accuracy on scan documents.
"""

from typing import Optional
import numpy as np

try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False

try:
    from rapidocr_onnxruntime import RapidOCR
    _HAS_RAPID_OCR = True
except ImportError:
    _HAS_RAPID_OCR = False


class OCREngine:
    def __init__(self):
        self._ocr = None

    def _ensure_init(self):
        if self._ocr is None and _HAS_RAPID_OCR:
            try:
                self._ocr = RapidOCR()
            except Exception as e:
                print(f"Error initializing RapidOCR: {e}")

    def ocr_crop(self, img_np: np.ndarray) -> str:
        """OCRs a cropped image snippet and returns clean single-line or multi-line text."""
        if img_np is None or img_np.size == 0:
            return ""
        self._ensure_init()
        if not self._ocr:
            return ""

        try:
            crop_bgr = img_np
            if img_np.ndim == 3:
                if img_np.shape[2] == 4:  # RGBA -> BGR
                    if _HAS_CV2:
                        crop_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
                    else:
                        crop_bgr = img_np[:, :, :3][:, :, ::-1]
                elif img_np.shape[2] == 3:  # RGB -> BGR
                    if _HAS_CV2:
                        crop_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                    else:
                        crop_bgr = img_np[:, :, ::-1]

            # Upscale small crops for higher OCR precision if height is small
            h, w = crop_bgr.shape[:2]
            if h < 40 and _HAS_CV2:
                scale_factor = 40.0 / float(h)
                crop_bgr = cv2.resize(crop_bgr, (int(w * scale_factor), 40), interpolation=cv2.INTER_CUBIC)

            result, _ = self._ocr(crop_bgr)
            if not result:
                return ""
            
            lines = [item[1].strip() for item in result if item and len(item) > 1 and item[1].strip()]
            return " ".join(lines)
        except Exception as e:
            print(f"Error running crop OCR: {e}")
            return ""
