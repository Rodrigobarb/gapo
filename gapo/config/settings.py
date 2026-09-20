from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _settings_config(env_prefix: str) -> SettingsConfigDict:
    """Config comum: cada sub-config lê o .env com seu proprio prefixo."""
    return SettingsConfigDict(
        env_prefix=env_prefix,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class ModelConfig(BaseSettings):
    llm_name: str = "qwen2.5:7b-instruct-q4_K_M"
    llm_ctx_size: int = 2048
    llm_temperature: float = 0.3
    llm_num_gpu_layers: int = -1
    tts_model: str = "pt_BR-faber-medium"
    tts_sample_rate: int = 22050
    yolo_model: str = "yolov8n.onnx"
    paddle_lang: str = "en"

    model_config = _settings_config("GAPO_MODEL_")


class CaptureConfig(BaseSettings):
    fps: int = 3
    monitor_index: int = 0
    resolution_width: int = 1920
    resolution_height: int = 1080
    use_dxcam: bool = True

    model_config = _settings_config("GAPO_CAPTURE_")


class OCRConfig(BaseSettings):
    confidence_threshold: float = 0.6
    use_gpu: bool = False
    roi_padding: int = 5
    preprocess_scale: float = 2.0

    model_config = _settings_config("GAPO_OCR_")


class DiscordConfig(BaseSettings):
    token: str = Field(default="", validation_alias="DISCORD_TOKEN")
    application_id: Optional[int] = Field(
        default=None, validation_alias="DISCORD_APPLICATION_ID"
    )
    voice_channel_id: Optional[int] = Field(
        default=None, validation_alias="DISCORD_VOICE_CHANNEL_ID"
    )
    guild_id: Optional[int] = Field(default=None, validation_alias="DISCORD_GUILD_ID")
    command_prefix: str = "Gapo"

    model_config = _settings_config("GAPO_DISCORD_")


class STTConfig(BaseSettings):
    """Escuta por voz. Default na CPU: a GPU ja carrega o LLM."""

    enabled: bool = True
    model: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "pt"
    silence_seconds: float = 0.8
    max_utterance_seconds: float = 15.0

    model_config = _settings_config("GAPO_STT_")


class CoachConfig(BaseSettings):
    event_cooldown_seconds: float = 5.0
    gapo_cooldown_seconds: float = 10.0
    max_response_sentences: int = 3
    enable_event_coach: bool = True
    enable_gapo_chat: bool = True
    knowledge_base_path: Path = Path("data/champions")

    model_config = _settings_config("GAPO_COACH_")


class AppConfig(BaseSettings):
    model: ModelConfig = Field(default_factory=ModelConfig)
    capture: CaptureConfig = Field(default_factory=CaptureConfig)
    ocr: OCRConfig = Field(default_factory=OCRConfig)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)
    coach: CoachConfig = Field(default_factory=CoachConfig)
    stt: STTConfig = Field(default_factory=STTConfig)
    log_level: str = "INFO"
    data_dir: Path = Path("data")
    config_dir: Path = Path("config")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


_settings: Optional[AppConfig] = None


def get_settings() -> AppConfig:
    global _settings
    if _settings is None:
        _settings = AppConfig()
    return _settings


def reload_settings() -> AppConfig:
    global _settings
    _settings = AppConfig()
    return _settings