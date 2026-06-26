"""Command-line interface for clip-loop."""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from clip_loop.errors import ClipLoopError
from clip_loop.options import AudioSegment, ClipLoopOptions, VideoSegment
from clip_loop.parsing import (
    format_elapsed,
    parse_crop_corner,
    parse_duration,
    parse_keep_ratio,
    parse_speed_percent,
)
from clip_loop.pipeline import run_clip_loop

# Re-export public API used by the TUI and external callers.
__all__ = [
    "ClipLoopError",
    "build_parser",
    "format_elapsed",
    "main",
    "parse_crop_corner",
    "parse_duration",
    "parse_keep_ratio",
    "parse_speed_percent",
    "run_clip_loop",
    "validate_clip_loop_options",
]

from clip_loop.validation import validate_clip_loop_options  # noqa: E402

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
class _ParsedSegments:
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


def parse_segment_argv(argv: list[str]) -> _ParsedSegments:
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
    return _ParsedSegments(
        video_segments=videos,
        audio_segments=audios,
        remaining_argv=remaining,
    )


def _add_loop_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "input",
        type=Path,
        nargs="?",
        help="Input video file (optional with --tui)",
    )
    p.add_argument(
        "-d",
        "--duration",
        type=parse_duration,
        default=parse_duration("1h"),
        help="Target length (default: 1h). Examples: 3600, 1h, 30m, 90s",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="PATH",
        help="Output file (default: <input_stem>_looped<suffix>)",
    )
    p.add_argument(
        "--alternate-reverse",
        action="store_true",
        help=(
            "With a single positional input, ping-pong that video (forward then reverse). "
            "For multiple clips use --video-alternate-reverse per --video."
        ),
    )
    p.add_argument(
        "--trim-start-ms",
        type=int,
        default=0,
        metavar="N",
        help=(
            "With a single positional input, skip the first N ms before looping. "
            "For multiple clips use --video-trim-start-ms per --video."
        ),
    )
    p.add_argument(
        "--speed",
        type=parse_speed_percent,
        default=100.0,
        metavar="PERCENT",
        help=(
            "With a single positional input, playback speed percentage. "
            "For multiple clips use --video-speed per --video."
        ),
    )
    p.add_argument(
        "--audio-crossfade-ms",
        type=int,
        default=0,
        metavar="N",
        help=(
            "With external audio, crossfade each loop seam by N milliseconds "
            "(default: 0 = disabled)."
        ),
    )
    p.add_argument(
        "--audio-gap-ms",
        type=int,
        default=0,
        metavar="N",
        help=(
            "With external audio, append N milliseconds of silence between loop "
            "iterations (default: 0 = disabled)."
        ),
    )
    p.add_argument(
        "--audio-seam-fade-ms",
        type=int,
        default=0,
        metavar="N",
        help=(
            "With external audio, fade volume near each loop seam by N milliseconds "
            "(default: 0 = disabled)."
        ),
    )
    p.add_argument(
        "--tui",
        action="store_true",
        help="Open an interactive terminal UI to configure options.",
    )
    p.add_argument(
        "--keep-ratio",
        type=parse_keep_ratio,
        metavar="RATIO",
        help=(
            "With a single positional input, crop a corner before looping. "
            "Requires --corner. For multiple clips use --video-keep-ratio."
        ),
    )
    p.add_argument(
        "--corner",
        type=parse_crop_corner,
        metavar="CORNER",
        help=(
            "With --keep-ratio on a single positional input, corner to remove."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="clip-loop",
        description="Loop a video clip until it reaches a target duration (default 1 hour).",
        epilog=(
            "Multi-clip join: repeat --video PATH with per-clip options "
            "(--video-trim-start-ms, --video-speed, --video-keep-ratio, "
            "--video-corner, --video-alternate-reverse). Repeat --audio PATH "
            "with --audio-trim-start-ms and --audio-alternate-reverse. "
            "Clips are joined, then looped to the target duration."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_loop_arguments(p)
    return p


def _namespace_to_options(args: Any, segments: _ParsedSegments) -> ClipLoopOptions:
    if segments.video_segments and args.input is not None:
        raise ClipLoopError("Cannot combine positional input with --video.")

    if segments.video_segments:
        video_segments = tuple(segments.video_segments)
    elif args.input is not None:
        video_segments = (
            VideoSegment(
                path=args.input,
                trim_start_ms=args.trim_start_ms,
                speed_percent=args.speed,
                keep_ratio=args.keep_ratio,
                crop_corner=args.corner,
                alternate_reverse=args.alternate_reverse,
            ),
        )
    else:
        raise ClipLoopError("A video input is required: positional PATH or --video PATH.")

    audio_segments = tuple(segments.audio_segments)

    return ClipLoopOptions(
        video_segments=video_segments,
        duration=args.duration,
        output_path=args.output,
        audio_segments=audio_segments,
        audio_crossfade_ms=args.audio_crossfade_ms,
        audio_gap_ms=args.audio_gap_ms,
        audio_seam_fade_ms=args.audio_seam_fade_ms,
    )


def main() -> None:
    try:
        segments = parse_segment_argv(sys.argv[1:])
    except ClipLoopError as exc:
        sys.stderr.write(f"{exc}\n")
        sys.exit(2)

    parser = build_parser()
    try:
        args = parser.parse_args(segments.remaining_argv)
    except SystemExit as exc:
        raise SystemExit(exc.code) from exc

    if args.tui:
        try:
            from clip_loop.tui import run_tui
        except ImportError as exc:
            sys.stderr.write(
                "clip-loop TUI requires the optional 'tui' dependency. "
                "Install with: uv sync --extra tui\n"
            )
            raise SystemExit(1) from exc
        initial_input = args.input
        if initial_input is None and segments.video_segments:
            initial_input = segments.video_segments[0].path
        initial_audio = segments.audio_segments[0].path if segments.audio_segments else None
        run_tui(
            initial_input=initial_input,
            initial_output=args.output,
            initial_audio=initial_audio,
        )
        return

    if args.input is None and not segments.video_segments:
        parser.error("the following arguments are required: input or --video (or use --tui)")

    started = time.perf_counter()
    try:
        options = _namespace_to_options(args, segments)
        output_path = run_clip_loop(options)
    except ClipLoopError as exc:
        sys.stderr.write(f"{exc}\n")
        sys.exit(1)
    elapsed = time.perf_counter() - started
    print(
        f"Wrote {output_path} ({args.duration:g}s) in {format_elapsed(elapsed)}"
    )
