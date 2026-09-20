import asyncio
from pathlib import Path
from gapo.infrastructure.ollama import OllamaClient
from gapo.infrastructure.piper import PiperEngine, VoiceManager
from gapo.infrastructure.ocr import YOLODetector
from gapo.config.settings import get_settings
from gapo.core.logging import get_logger
from gapo.core.exceptions import ModelNotFoundError

logger = get_logger("model_service")


class ModelService:
    def __init__(self):
        self.settings = get_settings()
        self.ollama_client: OllamaClient | None = None
        self.piper_engine: PiperEngine | None = None
        self.voice_manager: VoiceManager | None = None
        self.yolo_detector: YOLODetector | None = None
        self._initialized = False

    async def initialize(self) -> bool:
        if self._initialized:
            return True

        try:
            self.ollama_client = OllamaClient(
                model=self.settings.model.llm_name,
            )
            if not await self.ollama_client.ensure_model():
                logger.error("Failed to load Ollama model")
                return False

            self.piper_engine = PiperEngine()
            self.voice_manager = VoiceManager()
            if not self.voice_manager.ensure_default_model():
                logger.warning("Piper model not found, will attempt download on first use")

            yolo_path = Path(self.settings.model.yolo_model)
            if yolo_path.exists():
                self.yolo_detector = YOLODetector(
                    model_path=yolo_path,
                    conf_threshold=self.settings.ocr.confidence_threshold,
                    use_gpu=self.settings.ocr.use_gpu,
                )
            else:
                logger.warning(f"YOLO model not found at {yolo_path}")

            self._initialized = True
            logger.info("All models initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Model initialization failed: {e}")
            return False

    async def download_models(self) -> bool:
        success = True
        if self.voice_manager:
            success &= self.voice_manager.ensure_default_model()
        return success

    def get_ollama_client(self) -> OllamaClient:
        if not self.ollama_client:
            raise ModelNotFoundError("Ollama client not initialized")
        return self.ollama_client

    def get_piper_engine(self) -> PiperEngine:
        if not self.piper_engine:
            raise ModelNotFoundError("Piper engine not initialized")
        return self.piper_engine

    def get_voice_manager(self) -> VoiceManager:
        if not self.voice_manager:
            raise ModelNotFoundError("Voice manager not initialized")
        return self.voice_manager

    def get_yolo_detector(self) -> YOLODetector | None:
        return self.yolo_detector

    async def health_check(self) -> dict:
        health = {
            "ollama": False,
            "piper": False,
            "yolo": False,
        }
        if self.ollama_client:
            health["ollama"] = await self.ollama_client.health_check()
        if self.piper_engine:
            health["piper"] = True
        if self.yolo_detector:
            health["yolo"] = True
        return health