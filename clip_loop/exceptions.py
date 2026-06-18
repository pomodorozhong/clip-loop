"""Domain exceptions for clip-loop."""


class ClipLoopError(Exception):
    """Validation or processing error for clip-loop."""


class FfmpegError(ClipLoopError):
    """ffmpeg or ffprobe subprocess failure."""


class ParseError(ValueError):
    """Invalid user-supplied option value."""
