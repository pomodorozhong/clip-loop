"""ffmpeg package public surface."""

from clip_loop.ffmpeg.audio import AudioCycleBuilder
from clip_loop.ffmpeg.executor import FfmpegExecutor, SubprocessFfmpegExecutor, ensure_ffmpeg_available
from clip_loop.ffmpeg.looping import LoopEngine
from clip_loop.ffmpeg.probe import FfmpegMediaProbe, MediaProbe
from clip_loop.ffmpeg.video import VideoProcessor

__all__ = [
    "AudioCycleBuilder",
    "FfmpegExecutor",
    "FfmpegMediaProbe",
    "LoopEngine",
    "MediaProbe",
    "SubprocessFfmpegExecutor",
    "VideoProcessor",
    "ensure_ffmpeg_available",
]
