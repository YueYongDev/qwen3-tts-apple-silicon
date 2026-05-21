class QwenTTSError(Exception):
    """Base error for user-displayable Qwen TTS failures."""


class ModelNotFoundError(QwenTTSError):
    """Raised when a configured model folder cannot be resolved."""


class VoiceNotFoundError(QwenTTSError):
    """Raised when a saved voice profile is missing or incomplete."""


class AudioConversionError(QwenTTSError):
    """Raised when an input audio file cannot be converted to WAV."""


class GenerationError(QwenTTSError):
    """Raised when audio generation fails."""


class JobBusyError(QwenTTSError):
    """Raised when a generation job is already running."""

