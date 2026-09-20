class GapoError(Exception):
    pass


class ConfigurationError(GapoError):
    pass


class ModelNotFoundError(GapoError):
    pass


class CaptureError(GapoError):
    pass


class OCRError(GapoError):
    pass


class LLMError(GapoError):
    pass


class TTSError(GapoError):
    pass


class DiscordError(GapoError):
    pass


class CalibrationError(GapoError):
    pass