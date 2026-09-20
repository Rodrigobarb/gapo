import subprocess
import asyncio
import tempfile
import os
from pathlib import Path
from typing import AsyncGenerator
from gapo.core.logging import get_logger
from gapo.models.audio import VoiceConfig, TTSRequest, AudioChunk, AudioFormat
from gapo.core.metrics import tts_requests_total, tts_latency_seconds
import time

logger = get_logger("piper_engine")


class PiperEngine:
    def __init__(self, model_dir: Path = Path.home() / ".local/share/piper"):
        self.model_dir = model_dir
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self._model_cache: dict[str, Path] = {}

    def _get_model_path(self, model_name: str) -> Path:
        if model_name in self._model_cache:
            return self._model_cache[model_name]

        model_path = self.model_dir / f"{model_name}.onnx"
        if model_path.exists():
            self._model_cache[model_name] = model_path
            return model_path

        config_path = self.model_dir / f"{model_name}.onnx.json"
        if config_path.exists():
            self._model_cache[model_name] = model_path
            return model_path

        return model_path

    def ensure_model(self, model_name: str) -> bool:
        model_path = self._get_model_path(model_name)
        if model_path.exists():
            return True

        logger.info(f"Downloading Piper model: {model_name}")
        try:
            result = subprocess.run(
                ["piper", "--download-model", model_name, "--output-dir", str(self.model_dir)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                logger.info(f"Model {model_name} downloaded successfully")
                return True
            else:
                logger.error(f"Failed to download model: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error downloading model: {e}")
            return False

    async def synthesize(self, request: TTSRequest) -> AsyncGenerator[AudioChunk, None]:
        start = time.monotonic()
        text = request.clean_text()
        if not text:
            return

        voice = request.voice_config
        model_path = self._get_model_path(voice.model)

        if not model_path.exists():
            logger.error(f"Model not found: {voice.model}")
            tts_requests_total.labels(status="error").inc()
            return

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                output_path = tmp.name

            cmd = [
                "piper",
                "--model", str(model_path),
                "--output_file", output_path,
                "--length_scale", str(voice.length_scale),
                "--noise_scale", str(voice.noise_scale),
                "--noise_w", str(voice.noise_w),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate(input=text.encode())

            if process.returncode != 0:
                logger.error(f"Piper synthesis failed: {stderr.decode()}")
                tts_requests_total.labels(status="error").inc()
                return

            tts_requests_total.labels(status="success").inc()
            tts_latency_seconds.observe(time.monotonic() - start)

            with open(output_path, "rb") as f:
                wav_data = f.read()

            os.unlink(output_path)

            yield AudioChunk(
                data=wav_data,
                format=AudioFormat.WAV,
                sample_rate=voice.sample_rate,
                channels=1,
                frame_count=len(wav_data) // 2,
                is_final=True,
                request_id=request.request_id,
            )

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            tts_requests_total.labels(status="error").inc()

    async def synthesize_streaming(self, request: TTSRequest) -> AsyncGenerator[AudioChunk, None]:
        for chunk in self.synthesize(request):
            yield chunk