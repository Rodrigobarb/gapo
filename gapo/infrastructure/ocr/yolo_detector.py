import onnxruntime as ort
import numpy as np
import cv2
from pathlib import Path
from typing import Optional
from gapo.core.logging import get_logger
from gapo.models.ocr import UIRoi

logger = get_logger("yolo_detector")


class YOLODetector:
    def __init__(self, model_path: Path, conf_threshold: float = 0.5, use_gpu: bool = True):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.session: Optional[ort.InferenceSession] = None
        self.input_name = ""
        self.output_names = []
        self.class_names = ["hud", "minimap", "chat", "tab", "shop", "player", "enemy", "ward", "objective"]
        self._init_session(use_gpu)

    def _init_session(self, use_gpu: bool) -> None:
        try:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if use_gpu else ["CPUExecutionProvider"]
            self.session = ort.InferenceSession(str(self.model_path), providers=providers)
            self.input_name = self.session.get_inputs()[0].name
            self.output_names = [o.name for o in self.session.get_outputs()]
            logger.info(f"YOLO detector loaded: {self.model_path} (GPU: {use_gpu})")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise

    def detect(self, image: np.ndarray) -> list[UIRoi]:
        if self.session is None:
            return []

        h, w = image.shape[:2]
        input_tensor = self._preprocess(image)

        try:
            outputs = self.session.run(self.output_names, {self.input_name: input_tensor})
            detections = self._postprocess(outputs[0], w, h)
            return detections
        except Exception as e:
            logger.error(f"YOLO inference failed: {e}")
            return []

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        input_h, input_w = 640, 640
        resized = cv2.resize(image, (input_w, input_h))
        normalized = resized.astype(np.float32) / 255.0
        transposed = np.transpose(normalized, (2, 0, 1))
        return np.expand_dims(transposed, axis=0)

    def _postprocess(self, output: np.ndarray, orig_w: int, orig_h: int) -> list[UIRoi]:
        detections = []
        predictions = output[0].T

        for pred in predictions:
            conf = pred[4]
            if conf < self.conf_threshold:
                continue

            class_scores = pred[5:]
            class_id = np.argmax(class_scores)
            class_conf = class_scores[class_id]

            if class_conf < self.conf_threshold:
                continue

            cx, cy, w, h = pred[:4]
            x1 = int((cx - w / 2) * orig_w / 640)
            y1 = int((cy - h / 2) * orig_h / 640)
            x2 = int((cx + w / 2) * orig_w / 640)
            y2 = int((cy + h / 2) * orig_h / 640)

            x1 = max(0, min(x1, orig_w - 1))
            y1 = max(0, min(y1, orig_h - 1))
            x2 = max(0, min(x2, orig_w))
            y2 = max(0, min(y2, orig_h))

            if x2 > x1 and y2 > y1:
                class_name = self.class_names[class_id] if class_id < len(self.class_names) else f"class_{class_id}"
                detections.append(UIRoi(
                    name=class_name,
                    x=x1,
                    y=y1,
                    width=x2 - x1,
                    height=y2 - y1,
                ))

        return detections