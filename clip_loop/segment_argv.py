"""Segment argv parsing for the clip-loop CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from clip_loop.errors import ClipLoopError
from clip_loop.options import AudioSegment, VideoSegment
from clip_loop.parsing import parse_crop_corner, parse_keep_ratio, parse_speed_percent

_SEGMENT_FLAGS = frozenset(
    {
        "--video",
        "--video-trim-start-ms",
        "--video-speed",
        "--video-keep-ratio",
        "--video-corner",
        "--video-alternate-reverse",
        "--audio",
        "--audio-trim-start-ms",
        "--audio-alternate-reverse",
    }
)


@dataclass
class _VideoDraft:
    path: Path | None = None
    trim_start_ms: int = 0
    speed_percent: float = 100.0
    keep_ratio: float | None = None
    crop_corner: str | None = None
    alternate_reverse: bool = False


@dataclass
class _AudioDraft:
    path: Path | None = None
    trim_start_ms: int = 0
    alternate_reverse: bool = False


@dataclass
class ParsedSegments:
    video_segments: list[VideoSegment] = field(default_factory=list)
    audio_segments: list[AudioSegment] = field(default_factory=list)
    remaining_argv: list[str] = field(default_factory=list)


def _finalize_video(draft: _VideoDraft) -> VideoSegment:
    if draft.path is None:
        raise ClipLoopError("--video PATH is required before per-video options.")
    return VideoSegment(
        path=draft.path,
        trim_start_ms=draft.trim_start_ms,
        speed_percent=draft.speed_percent,
        keep_ratio=draft.keep_ratio,
        crop_corner=draft.crop_corner,
        alternate_reverse=draft.alternate_reverse,
    )


def _finalize_audio(draft: _AudioDraft) -> AudioSegment:
    if draft.path is None:
        raise ClipLoopError("--audio PATH is required before per-audio options.")
    return AudioSegment(
        path=draft.path,
        trim_start_ms=draft.trim_start_ms,
        alternate_reverse=draft.alternate_reverse,
    )


def parse_segment_argv(argv: list[str]) -> ParsedSegments:
    """Extract multi-clip segment flags; return remaining argv for argparse."""
    videos: list[VideoSegment] = []
    audios: list[AudioSegment] = []
    current_video: _VideoDraft | None = None
    current_audio: _AudioDraft | None = None
    remaining: list[str] = []
    index = 0

    def flush_video() -> None:
        nonlocal current_video
        if current_video is not None:
            videos.append(_finalize_video(current_video))
            current_video = None

    def flush_audio() -> None:
        nonlocal current_audio
        if current_audio is not None:
            audios.append(_finalize_audio(current_audio))
            current_audio = None

    while index < len(argv):
        arg = argv[index]
        if arg == "--video":
            flush_video()
            if index + 1 >= len(argv):
                raise ClipLoopError("--video requires a PATH argument.")
            current_video = _VideoDraft(path=Path(argv[index + 1]))
            index += 2
            continue
        if arg == "--video-trim-start-ms":
            if current_video is None:
                raise ClipLoopError("--video-trim-start-ms must follow --video PATH.")
            if index + 1 >= len(argv):
                raise ClipLoopError("--video-trim-start-ms requires a value.")
            current_video.trim_start_ms = int(argv[index + 1])
            index += 2
            continue
        if arg == "--video-speed":
            if current_video is None:
                raise ClipLoopError("--video-speed must follow --video PATH.")
            if index + 1 >= len(argv):
                raise ClipLoopError("--video-speed requires a value.")
            current_video.speed_percent = parse_speed_percent(argv[index + 1])
            index += 2
            continue
        if arg == "--video-keep-ratio":
            if current_video is None:
                raise ClipLoopError("--video-keep-ratio must follow --video PATH.")
            if index + 1 >= len(argv):
                raise ClipLoopError("--video-keep-ratio requires a value.")
            current_video.keep_ratio = parse_keep_ratio(argv[index + 1])
            index += 2
            continue
        if arg == "--video-corner":
            if current_video is None:
                raise ClipLoopError("--video-corner must follow --video PATH.")
            if index + 1 >= len(argv):
                raise ClipLoopError("--video-corner requires a value.")
            current_video.crop_corner = parse_crop_corner(argv[index + 1])
            index += 2
            continue
        if arg == "--video-alternate-reverse":
            if current_video is None:
                raise ClipLoopError("--video-alternate-reverse must follow --video PATH.")
            current_video.alternate_reverse = True
            index += 1
            continue
        if arg == "--audio":
            flush_audio()
            if index + 1 >= len(argv):
                raise ClipLoopError("--audio requires a PATH argument.")
            current_audio = _AudioDraft(path=Path(argv[index + 1]))
            index += 2
            continue
        if arg == "--audio-trim-start-ms":
            if current_audio is None:
                raise ClipLoopError("--audio-trim-start-ms must follow --audio PATH.")
            if index + 1 >= len(argv):
                raise ClipLoopError("--audio-trim-start-ms requires a value.")
            current_audio.trim_start_ms = int(argv[index + 1])
            index += 2
            continue
        if arg == "--audio-alternate-reverse":
            if current_audio is None:
                raise ClipLoopError("--audio-alternate-reverse must follow --audio PATH.")
            current_audio.alternate_reverse = True
            index += 1
            continue
        if arg in _SEGMENT_FLAGS:
            raise ClipLoopError(f"unrecognized segment flag: {arg}")
        remaining.append(arg)
        index += 1

    flush_video()
    flush_audio()
    return ParsedSegments(
        video_segments=videos,
        audio_segments=audios,
        remaining_argv=remaining,
    )
