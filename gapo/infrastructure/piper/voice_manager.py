from pathlib import Path
from gapo.infrastructure.piper.engine import PiperEngine
from gapo.models.audio import VoiceConfig, VoiceProvider
from gapo.core.logging import get_logger

logger = get_logger("voice_manager")


class VoiceManager:
    def __init__(self, model_dir: Path = Path.home() / ".local/share/piper"):
        self.engine = PiperEngine(model_dir)
        self.default_config = VoiceConfig()
        self._available_voices: dict[str, VoiceConfig] = {}

    def ensure_default_model(self) -> bool:
        return self.engine.ensure_model(self.default_config.model)

    def get_voice(self, name: str) -> VoiceConfig:
        if name in self._available_voices:
            return self._available_voices[name]
        return self.default_config

    def list_available_voices(self) -> list[str]:
        return list(self._available_voices.keys()) + [self.default_config.model]

    def set_voice(self, model: str, speaker: str = "") -> VoiceConfig:
        config = VoiceConfig(
            provider=VoiceProvider.PIPER,
            model=model,
            speaker=speaker or model.split("-")[-1],
        )
        self._available_voices[model] = config
        return config