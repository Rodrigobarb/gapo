"""Escuta a call: recorta a fala, transcreve e dispara o Gapo.

Fluxo: UtteranceSink (thread do discord) -> poll aqui no event loop ->
Whisper numa thread -> deteccao da palavra-chave -> callback com a pergunta.

O reconhecimento erra a palavra-chave com frequencia ("capo", "gapô", "gap o"),
entao a comparacao e por semelhanca e nao por igualdade: exigir "Gapo" exato
faria o usuario repetir a pergunta varias vezes.
"""

from __future__ import annotations

import asyncio
import difflib
import re
import unicodedata
from typing import Awaitable, Callable, Optional

from gapo.core.logging import get_logger
from gapo.infrastructure.stt import WhisperEngine
from gapo.models.audio import Utterance
from gapo.utils.audio import discord_pcm_to_whisper

logger = get_logger("voice_input")

# Variacoes que o Whisper costuma devolver no lugar de "Gapo".
VARIANTES_GATILHO = ("gapo", "capo", "gapu", "gapao", "gaspo", "gap")

SEMELHANCA_MINIMA = 0.75
DURACAO_MINIMA_SEGUNDOS = 0.4

OnQuestion = Callable[[int, str, str], Awaitable[None]]


class VoiceInputService:
    def __init__(
        self,
        stt_engine: WhisperEngine,
        on_question: OnQuestion,
        trigger: str = "Gapo",
        poll_interval: float = 0.25,
    ) -> None:
        self.stt = stt_engine
        self.on_question = on_question
        self.trigger = trigger
        self.poll_interval = poll_interval
        self._sink = None
        self._task: Optional[asyncio.Task] = None
        self._running = False

    def is_running(self) -> bool:
        return self._running

    async def start(self, sink) -> bool:
        if sink is None:
            return False
        if self._running:
            return True

        # Carrega o modelo antes de aceitar falas: a primeira pergunta nao
        # deve pagar os segundos de carga (nem o download, na primeira vez).
        if not await asyncio.to_thread(self.stt.load):
            logger.error("Whisper indisponivel - escuta por voz nao iniciada")
            return False

        self._sink = sink
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(f"Escuta por voz ativa (gatilho: '{self.trigger}')")
        return True

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._sink = None
        logger.info("Escuta por voz parada")

    async def _loop(self) -> None:
        while self._running:
            try:
                for fala in self._sink.pop_finished():
                    # Cada fala vira uma task: transcrever nao pode travar a coleta.
                    asyncio.create_task(self._processar(fala))
            except Exception as e:
                logger.error(f"Erro ao coletar falas: {e}")
            await asyncio.sleep(self.poll_interval)

    async def _processar(self, fala: Utterance) -> None:
        if fala.duration_seconds < DURACAO_MINIMA_SEGUNDOS:
            return

        try:
            audio = discord_pcm_to_whisper(fala.pcm)
            texto = await self.stt.transcribe(audio)
        except Exception as e:
            logger.error(f"Falha ao transcrever fala de {fala.username}: {e}")
            return

        if not texto:
            return

        pergunta = extract_question(texto, self.trigger)
        if pergunta is None:
            logger.debug(f"Sem gatilho em {texto!r} ({fala.username})")
            return

        logger.info(f"Voz de {fala.username}: {texto!r} -> pergunta: {pergunta!r}")
        try:
            await self.on_question(fala.user_id, fala.username, pergunta)
        except Exception as e:
            logger.error(f"Erro ao responder pergunta por voz: {e}")


def extract_question(texto: str, trigger: str = "Gapo") -> Optional[str]:
    """Pergunta depois da palavra-chave, ou None se ela nao aparece no inicio.

    Compara sem acento e por semelhanca para tolerar o erro do reconhecimento.
    """
    limpo = texto.strip()
    if not limpo:
        return None

    partes = re.split(r"[\s,.!?;:]+", limpo, maxsplit=1)
    primeira = _normalizar(partes[0])
    if not primeira:
        return None

    alvos = set(VARIANTES_GATILHO) | {_normalizar(trigger)}
    if not any(_parecido(primeira, alvo) for alvo in alvos):
        return None

    resto = partes[1].strip() if len(partes) > 1 else ""
    return resto or None


def _normalizar(palavra: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", palavra)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return re.sub(r"[^a-z]", "", sem_acento.lower())


def _parecido(palavra: str, alvo: str) -> bool:
    if palavra == alvo:
        return True
    return difflib.SequenceMatcher(None, palavra, alvo).ratio() >= SEMELHANCA_MINIMA
