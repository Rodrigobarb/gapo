from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AudioFormat(str, Enum):
    RAW_PCM = "raw_pcm"
    WAV = "wav"
    OPUS = "opus"


class VoiceProvider(str, Enum):
    PIPER = "piper"
    XTTS = "xtts"


@dataclass
class VoiceConfig:
    provider: VoiceProvider = VoiceProvider.PIPER
    model: str = "pt_BR-faber-medium"
    speaker: str = "faber"
    sample_rate: int = 22050
    length_scale: float = 1.0
    noise_scale: float = 0.667
    noise_w: float = 0.8


@dataclass
class TTSRequest:
    text: str
    voice_config: VoiceConfig
    priority: int = 0
    request_id: str = ""

    def clean_text(self) -> str:
        text = self.text.strip()
        text = text.replace("*", "").replace("#", "").replace("`", "")
        text = text.replace("→", "->").replace("←", "<-")
        return text


@dataclass
class AudioChunk:
    data: bytes
    format: AudioFormat
    sample_rate: int
    channels: int
    frame_count: int
    is_final: bool = False
    request_id: str = ""


@dataclass
class OpusPacket:
    data: bytes
    timestamp: int
    sequence: int