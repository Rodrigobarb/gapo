from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional
from gapo.models.ocr import UIRoi
from gapo.models.coach import CoachMode


class ROIConfig(BaseModel):
    preset: str = "1920x1080"
    custom_rois: dict[str, UIRoi] = Field(default_factory=dict)
    calibrated: bool = False


class ModelConfig(BaseModel):
    llm_name: str = "qwen2.5:7b-instruct-q4_K_M"
    llm_ctx_size: int = 2048
    llm_temperature: float = 0.3
    tts_model: str = "pt_BR-faber-medium"
    yolo_model: str = "yolov8n.onnx"


class AppConfig(BaseModel):
    roi: ROIConfig = ROIConfig()
    models: ModelConfig = ModelConfig()
    capture_fps: int = 3
    event_cooldown: float = 5.0
    gapo_cooldown: float = 10.0
    data_dir: Path = Path("data")
    log_level: str = "INFO"