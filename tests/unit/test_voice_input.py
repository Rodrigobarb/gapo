"""Testes da escuta por voz que nao dependem do Discord nem do Whisper."""

import numpy as np
import pytest

from gapo.models.audio import Utterance
from gapo.services.voice_input_service import extract_question
from gapo.utils.audio import discord_pcm_to_whisper


def pcm_48k_estereo(segundos: float, freq: float = 440.0) -> bytes:
    """Senoide 48kHz estereo s16le, no formato que o Discord entrega."""
    n = int(48000 * segundos)
    t = np.arange(n) / 48000
    mono = (np.sin(2 * np.pi * freq * t) * 16000).astype(np.int16)
    estereo = np.repeat(mono, 2)
    return estereo.tobytes()


class TestConversaoDeAudio:
    def test_reduz_para_16k_mono(self):
        audio = discord_pcm_to_whisper(pcm_48k_estereo(1.0))
        assert audio.dtype == np.float32
        assert abs(audio.size - 16000) <= 1

    def test_normaliza_entre_menos_um_e_um(self):
        audio = discord_pcm_to_whisper(pcm_48k_estereo(0.2))
        assert np.all(np.abs(audio) <= 1.0)
        assert np.abs(audio).max() > 0.1

    def test_pcm_vazio_nao_quebra(self):
        assert discord_pcm_to_whisper(b"").size == 0

    def test_pcm_curto_demais_nao_quebra(self):
        assert discord_pcm_to_whisper(b"\x00\x01").size == 0


class TestGatilho:
    @pytest.mark.parametrize(
        "texto",
        [
            "Gapo qual a melhor jogada agora?",
            "gapo, qual a melhor jogada agora?",
            "Gapô qual a melhor jogada agora?",
            "Capo qual a melhor jogada agora?",  # erro comum do reconhecimento
            "  GAPO   qual a melhor jogada agora?  ",
        ],
    )
    def test_reconhece_variacoes(self, texto):
        assert extract_question(texto) == "qual a melhor jogada agora?"

    @pytest.mark.parametrize(
        "texto",
        [
            "qual a melhor jogada agora?",  # sem gatilho
            "vamos pegar o dragao",
            "",
            "   ",
            "Gapo",  # gatilho sem pergunta
            "Gapo   ",
        ],
    )
    def test_ignora_sem_gatilho_ou_sem_pergunta(self, texto):
        assert extract_question(texto) is None

    def test_gatilho_no_meio_nao_conta(self):
        # Evita responder quando alguem so menciona o bot numa conversa.
        assert extract_question("acho que o Gapo ta quieto hoje") is None

    def test_gatilho_customizado(self):
        assert extract_question("Treinador me ajuda", trigger="Treinador") == "me ajuda"


class TestUtterance:
    def test_duracao_bate_com_os_bytes(self):
        pcm = pcm_48k_estereo(2.0)
        fala = Utterance(user_id=1, username="eu", pcm=pcm, duration_seconds=len(pcm) / (48000 * 4))
        assert abs(fala.duration_seconds - 2.0) < 0.01
