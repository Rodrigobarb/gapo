import asyncio
from gapo.infrastructure.ocr import PaddleEngine, Preprocessor, OCRParser, YOLODetector
from gapo.models.ocr import UIRoi, OCRResult, ParsedHUD, ParsedMinimap, ParsedChat
from gapo.config.settings import get_settings
from gapo.core.logging import get_logger
from gapo.repositories.roi_repo import ROIRepository

logger = get_logger("ocr_service")


class OCRService:
    def __init__(self, roi_repo: ROIRepository):
        self.settings = get_settings()
        self.roi_repo = roi_repo
        self.paddle = PaddleEngine(
            lang=self.settings.model.paddle_lang,
            use_gpu=self.settings.ocr.use_gpu,
            confidence_threshold=self.settings.ocr.confidence_threshold,
        )
        self.preprocessor = Preprocessor(
            scale=self.settings.ocr.preprocess_scale,
            padding=self.settings.ocr.roi_padding,
        )
        self.parser = OCRParser()
        self.yolo: YOLODetector | None = None
        self._current_rois: dict[str, UIRoi] = {}

    def set_yolo(self, yolo: YOLODetector) -> None:
        self.yolo = yolo

    def set_resolution(self, width: int, height: int) -> None:
        resolution = f"{width}x{height}"
        self._current_rois = self.roi_repo.get_effective_rois(resolution)
        logger.info(f"OCR ROIs updated for resolution: {resolution}")

    async def process_frame(self, frame) -> dict:
        results = {}

        if self.yolo:
            try:
                detected_rois = self.yolo.detect(frame)
                for roi in detected_rois:
                    if roi.name in self._current_rois:
                        self._current_rois[roi.name] = roi
            except Exception as e:
                logger.error(f"YOLO detection failed: {e}")

        for name, roi in self._current_rois.items():
            try:
                processed = self.preprocessor.process(frame, roi, method=roi.preprocess)
                ocr_results = self.paddle.recognize_roi(processed, roi)
                results[name] = ocr_results
            except Exception as e:
                logger.error(f"OCR failed for {name}: {e}")
                results[name] = []

        return results

    def parse_hud(self, results: list[OCRResult]) -> ParsedHUD:
        return self.parser.parse_hud(results)

    def parse_minimap(self, results: list[OCRResult]) -> ParsedMinimap:
        return self.parser.parse_minimap(results)

    def parse_chat(self, results: list[OCRResult]) -> ParsedChat:
        return self.parser.parse_chat(results)