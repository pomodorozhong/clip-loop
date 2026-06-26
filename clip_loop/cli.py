"""Command-line interface for clip-loop."""

from __future__ import annotations

import argparse
import sys
import time
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

from clip_loop.segment_argv import ParsedSegments, parse_segment_argv
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


def _namespace_to_options(args: Any, segments: ParsedSegments) -> ClipLoopOptions:
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
        initial_options: ClipLoopOptions | None = None
        try:
            if segments.video_segments or args.input is not None:
                initial_options = _namespace_to_options(args, segments)
        except ClipLoopError:
            initial_options = None
        run_tui(
            initial_input=args.input,
            initial_output=args.output,
            initial_audio=segments.audio_segments[0].path if segments.audio_segments else None,
            initial_options=initial_options,
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
