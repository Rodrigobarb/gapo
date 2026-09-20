import numpy as np

from gapo.bootstrap.opus import register_opus_path
from gapo.core.exceptions import TTSError


def _load_opuslib():
    """Importa opuslib sob demanda: a lib nativa do Opus so e necessaria para voz.

    Mantem OCR, calibracao, doctor e os testes rodando em maquinas sem o Opus
    instalado, em vez de quebrar no import do pacote.
    """
    register_opus_path()
    try:
        import opuslib
    except Exception as e:
        raise TTSError(
            "Biblioteca nativa Opus nao encontrada - necessaria para audio no Discord. "
            "Rode `gapo init` (Windows) ou instale a libopus0 do sistema (Linux)."
        ) from e
    return opuslib


SAMPLE_RATE = 22050
CHANNELS = 1
FRAME_SIZE = 960  # 20ms at 48kHz, but we'll resample
FRAME_DURATION_MS = 20


class OpusEncoder:
    def __init__(self, sample_rate: int = 48000, channels: int = 1):
        opuslib = _load_opuslib()
        self.encoder = opuslib.Encoder(sample_rate, channels, opuslib.APPLICATION_AUDIO)
        self.sample_rate = sample_rate
        self.channels = channels
        self.frame_size = sample_rate // 50  # 20ms frames

    def encode(self, pcm_data: bytes) -> bytes:
        return self.encoder.encode(pcm_data, self.frame_size)

    def encode_float(self, float_data: np.ndarray) -> bytes:
        pcm_data = (float_data * 32767).astype(np.int16).tobytes()
        return self.encode(pcm_data)


class OpusDecoder:
    def __init__(self, sample_rate: int = 48000, channels: int = 1):
        opuslib = _load_opuslib()
        self.decoder = opuslib.Decoder(sample_rate, channels)
        self.sample_rate = sample_rate
        self.channels = channels

    def decode(self, opus_data: bytes, frame_size: int = None) -> bytes:
        if frame_size is None:
            frame_size = self.sample_rate // 50
        return self.decoder.decode(opus_data, frame_size)


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return audio
    ratio = target_sr / orig_sr
    new_length = int(len(audio) * ratio)
    indices = np.linspace(0, len(audio) - 1, new_length)
    return np.interp(indices, np.arange(len(audio)), audio)


def pcm_to_float(pcm_data: bytes, dtype: np.dtype = np.int16) -> np.ndarray:
    arr = np.frombuffer(pcm_data, dtype=dtype)
    return arr.astype(np.float32) / 32768.0


def float_to_pcm(float_data: np.ndarray, dtype: np.dtype = np.int16) -> bytes:
    arr = np.clip(float_data, -1.0, 1.0)
    arr = (arr * 32767).astype(dtype)
    return arr.tobytes()


def chunk_audio(audio: np.ndarray, chunk_samples: int) -> list[np.ndarray]:
    chunks = []
    for i in range(0, len(audio), chunk_samples):
        chunk = audio[i:i + chunk_samples]
        if len(chunk) < chunk_samples:
            chunk = np.pad(chunk, (0, chunk_samples - len(chunk)))
        chunks.append(chunk)
    return chunks