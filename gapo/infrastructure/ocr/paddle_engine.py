from paddleocr import PaddleOCR
import numpy as np
from typing import Optional
from gapo.core.logging import get_logger
from gapo.core.metrics import ocr_processed_total, ocr_latency_seconds
from gapo.models.ocr import OCRResult, UIRoi
import time

logger = get_logger("paddle_engine")


class PaddleEngine:
    def __init__(self, lang: str = "en", use_gpu: bool = False, confidence_threshold: float = 0.6):
        self.lang = lang
        self.use_gpu = use_gpu
        self.confidence_threshold = confidence_threshold
        self.ocr: Optional[PaddleOCR] = None
        self._init_ocr()

    def _init_ocr(self) -> None:
        try:
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang=self.lang,
                use_gpu=self.use_gpu,
                show_log=False,
                enable_mkldnn=not self.use_gpu,
            )
            logger.info(f"PaddleOCR initialized (lang={self.lang}, GPU={self.use_gpu})")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            raise

    def recognize(self, image: np.ndarray, roi_name: str = "unknown") -> list[OCRResult]:
        if self.ocr is None:
            return []

        start = time.monotonic()
        try:
            results = self.ocr.ocr(image, cls=True)
            ocr_results = []

            if results and results[0]:
                for line in results[0]:
                    bbox, (text, conf) = line
                    if conf >= self.confidence_threshold:
                        x_coords = [p[0] for p in bbox]
                        y_coords = [p[1] for p in bbox]
                        x1, y1 = int(min(x_coords)), int(min(y_coords))
                        x2, y2 = int(max(x_coords)), int(max(y_coords))
                        ocr_results.append(OCRResult(
                            text=text.strip(),
                            confidence=conf,
                            bbox=(x1, y1, x2, y2),
                            roi_name=roi_name,
                        ))

            latency = time.monotonic() - start
            ocr_latency_seconds.labels(roi=roi_name).observe(latency)
            ocr_processed_total.labels(roi=roi_name, status="success").inc(len(ocr_results))

            return ocr_results

        except Exception as e:
            ocr_processed_total.labels(roi=roi_name, status="error").inc()
            logger.error(f"PaddleOCR recognition failed: {e}")
            return []

    def recognize_roi(self, image: np.ndarray, roi: UIRoi) -> list[OCRResult]:
        cropped = image[roi.y:roi.y+roi.height, roi.x:roi.x+roi.width]
        if cropped.size == 0:
            return []
        return self.recognize(cropped, roi.name)