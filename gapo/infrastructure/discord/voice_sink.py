"""Recebe o audio da call e recorta cada fala.

O discord.py sozinho nao recebe voz - quem adiciona isso e a extensao
discord-ext-voice-recv. Se ela nao estiver instalada, este modulo continua
importavel e `HAS_VOICE_RECV` fica False: a saida de voz (TTS) segue
funcionando normalmente, so a escuta e desligada.

O `write()` roda na thread de recepcao do discord.py, nao no event loop.
Por isso ele so acumula bytes sob lock, e quem varre as falas prontas e um
task asyncio chamando `pop_finished()`.
"""

from __future__ import annotations

import threading
import time

from gapo.core.logging import get_logger
from gapo.models.audio import Utterance

logger = get_logger("voice_sink")

try:  # pragma: no cover - depende do ambiente
    from discord.ext import voice_recv

    HAS_VOICE_RECV = True
    _SinkBase = voice_recv.AudioSink
except ImportError:  # pragma: no cover - ambiente sem a extensao
    voice_recv = None
    HAS_VOICE_RECV = False
    _SinkBase = object

# 48kHz estereo s16le = 192000 bytes por segundo.
BYTES_POR_SEGUNDO = 48000 * 2 * 2


class UtteranceSink(_SinkBase):
    """Acumula o PCM de cada usuario e fecha a fala quando ele para de falar."""

    def __init__(self, silence_seconds: float = 0.8, max_seconds: float = 15.0) -> None:
        super().__init__()
        self.silence_seconds = silence_seconds
        self.max_bytes = int(max_seconds * BYTES_POR_SEGUNDO)
        self._lock = threading.Lock()
        self._buffers: dict[int, bytearray] = {}
        self._nomes: dict[int, str] = {}
        self._ultimo_pacote: dict[int, float] = {}
        self._prontas: list[Utterance] = []

    def wants_opus(self) -> bool:
        return False

    def write(self, user, data) -> None:  # roda na thread do discord
        if user is None or not getattr(data, "pcm", None):
            return

        agora = time.monotonic()
        with self._lock:
            buffer = self._buffers.setdefault(user.id, bytearray())
            buffer.extend(data.pcm)
            self._nomes[user.id] = getattr(user, "display_name", str(user))
            self._ultimo_pacote[user.id] = agora

            # Fala longa demais: fecha na marra para nao segurar a resposta.
            if len(buffer) >= self.max_bytes:
                self._fechar(user.id)

    def pop_finished(self) -> list[Utterance]:
        """Falas fechadas desde a ultima chamada. Roda no event loop."""
        agora = time.monotonic()
        with self._lock:
            for user_id, ultimo in list(self._ultimo_pacote.items()):
                if agora - ultimo >= self.silence_seconds and self._buffers.get(user_id):
                    self._fechar(user_id)

            prontas, self._prontas = self._prontas, []
        return prontas

    def _fechar(self, user_id: int) -> None:
        """Move o buffer do usuario para a fila de prontas. Exige o lock."""
        buffer = self._buffers.get(user_id)
        if not buffer:
            return
        pcm = bytes(buffer)
        buffer.clear()
        self._prontas.append(
            Utterance(
                user_id=user_id,
                username=self._nomes.get(user_id, str(user_id)),
                pcm=pcm,
                duration_seconds=len(pcm) / BYTES_POR_SEGUNDO,
            )
        )

    def cleanup(self) -> None:
        with self._lock:
            self._buffers.clear()
            self._ultimo_pacote.clear()
            self._prontas.clear()


def create_sink(silence_seconds: float = 0.8, max_seconds: float = 15.0):
    """Sink pronto para `voice_client.listen()`, ou None sem a extensao."""
    if not HAS_VOICE_RECV:
        logger.warning(
            "discord-ext-voice-recv nao instalado - escuta por voz desligada "
            "(rode `gapo init`). A fala do bot continua funcionando."
        )
        return None
    return UtteranceSink(silence_seconds=silence_seconds, max_seconds=max_seconds)


def voice_client_cls():
    """Classe de VoiceClient que sabe receber audio, ou None sem a extensao."""
    return voice_recv.VoiceRecvClient if HAS_VOICE_RECV else None
