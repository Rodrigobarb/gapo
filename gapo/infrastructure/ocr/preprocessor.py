import cv2
import numpy as np
from gapo.models.ocr import UIRoi
from gapo.core.logging import get_logger

logger = get_logger("preprocessor")


class Preprocessor:
    def __init__(self, scale: float = 2.0, padding: int = 5):
        self.scale = scale
        self.padding = padding

    def process(self, image: np.ndarray, roi: UIRoi, method: str = "default") -> np.ndarray:
        x, y, w, h = roi.x, roi.y, roi.width, roi.height
        x = max(0, x - self.padding)
        y = max(0, y - self.padding)
        w = min(w + 2 * self.padding, image.shape[1] - x)
        h = min(h + 2 * self.padding, image.shape[0] - y)

        cropped = image[y:y+h, x:x+w]

        if self.scale != 1.0:
            cropped = cv2.resize(cropped, None, fx=self.scale, fy=self.scale, interpolation=cv2.INTER_CUBIC)

        processed = self._apply_method(cropped, method)
        return processed

    def _apply_method(self, image: np.ndarray, method: str) -> np.ndarray:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        if method == "default":
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return thresh
        elif method == "adaptive":
            return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        elif method == "invert":
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            return thresh
        elif method == "denoise":
            denoised = cv2.fastNlMeansDenoising(gray)
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return thresh
        elif method == "hud":
            return self._preprocess_hud(gray)
        elif method == "minimap":
            return self._preprocess_minimap(gray)
        elif method == "chat":
            return self._preprocess_chat(gray)
        else:
            return gray

    def _preprocess_hud(self, gray: np.ndarray) -> np.ndarray:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    def _preprocess_minimap(self, gray: np.ndarray) -> np.ndarray:
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    def _preprocess_chat(self, gray: np.ndarray) -> np.ndarray:
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        return cleaned