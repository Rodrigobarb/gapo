"""Transcricao local com faster-whisper.

Roda na CPU por padrao de proposito: a GPU ja esta ocupada com o LLM, e um
modelo `small` em int8 transcreve uma pergunta curta em ~1s sem disputar VRAM.
"""

from __future__ import annotations

import asyncio
import time

import numpy as np

from gapo.core.logging import get_logger

logger = get_logger("whisper_engine")


class WhisperEngine:
    def __init__(
        self,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "pt",
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self._model = None

    def is_available(self) -> bool:
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            return False
        return True

    def load(self) -> bool:
        """Carrega o modelo (baixa no primeiro uso). Bloqueante de proposito."""
        if self._model is not None:
            return True
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            logger.error("faster-whisper nao instalado - rode `gapo init`")
            return False

        try:
            inicio = time.monotonic()
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info(
                f"Whisper {self.model_size} carregado em {self.device}/{self.compute_type} "
                f"({time.monotonic() - inicio:.1f}s)"
            )
            return True
        except Exception as e:
            logger.error(f"Falha ao carregar o Whisper: {e}")
            return False

    async def transcribe(self, audio: np.ndarray) -> str:
        """Transcreve float32 mono 16kHz. Devolve "" quando nao entende nada."""
        if audio.size == 0:
            return ""
        return await asyncio.to_thread(self._transcribe_sync, audio)

    def _transcribe_sync(self, audio: np.ndarray) -> str:
        if not self.load():
            return ""

        try:
            inicio = time.monotonic()
            segmentos, _ = self._model.transcribe(
                audio,
                language=self.language,
                beam_size=1,  # pergunta curta: greedy basta e corta a latencia
                vad_filter=True,
                condition_on_previous_text=False,
            )
            texto = " ".join(s.text.strip() for s in segmentos).strip()
            logger.debug(f"STT ({time.monotonic() - inicio:.2f}s): {texto!r}")
            return texto
        except Exception as e:
            logger.error(f"Falha na transcricao: {e}")
            return ""

    def unload(self) -> None:
        self._model = None


def default_model_repo(model_size: str) -> str:
    """Repositorio HuggingFace que o faster-whisper usa para cada tamanho."""
    return f"Systran/faster-whisper-{model_size}"
