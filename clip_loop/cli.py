"""Command-line interface for clip-loop."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

from clip_loop.errors import ClipLoopError
from clip_loop.options import ClipLoopOptions
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
            "After each forward play, play the clip in reverse (ping-pong), "
            "then repeat; reduces visible jumps at loop points (re-encodes)."
        ),
    )
    p.add_argument(
        "--trim-start-ms",
        type=int,
        default=0,
        metavar="N",
        help="Skip the first N milliseconds of the input before looping (default: 0).",
    )
    p.add_argument(
        "--speed",
        type=parse_speed_percent,
        default=100.0,
        metavar="PERCENT",
        help=(
            "Playback speed as a percentage of normal (default: 100). "
            "Examples: 80 for 80%%, 120 for 120%%. Re-encodes when not 100."
        ),
    )
    p.add_argument(
        "--audio",
        type=Path,
        metavar="PATH",
        help=(
            "Optional external audio file (e.g. mp3). "
            "Will loop/trim as needed to match the output duration."
        ),
    )
    p.add_argument(
        "--audio-alternate-reverse",
        action="store_true",
        help=(
            "With --audio, make one audio cycle as forward then reversed, "
            "then repeat. Independent of --alternate-reverse."
        ),
    )
    p.add_argument(
        "--audio-crossfade-ms",
        type=int,
        default=0,
        metavar="N",
        help=(
            "With --audio, crossfade each stitched audio seam by N milliseconds "
            "(default: 0 = disabled)."
        ),
    )
    p.add_argument(
        "--audio-gap-ms",
        type=int,
        default=0,
        metavar="N",
        help=(
            "With --audio, append N milliseconds of silence between stitched "
            "audio clips (default: 0 = disabled)."
        ),
    )
    p.add_argument(
        "--audio-seam-fade-ms",
        type=int,
        default=0,
        metavar="N",
        help=(
            "With --audio, fade volume down near the end and up at the start "
            "of each stitched clip by N milliseconds (default: 0 = disabled)."
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
            "Before looping, crop away a corner and scale back to the original "
            "frame size. Requires --corner. Examples: 80%%, 50%%, 0.8"
        ),
    )
    p.add_argument(
        "--corner",
        type=parse_crop_corner,
        metavar="CORNER",
        help=(
            "With --keep-ratio, corner to remove. top_left keeps bottom-right; "
            "top_right keeps bottom-left; bottom_left keeps top-right; "
            "bottom_right keeps top-left."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="clip-loop",
        description="Loop a video clip until it reaches a target duration (default 1 hour).",
    )
    _add_loop_arguments(p)
    return p


def _namespace_to_options(args: Any) -> ClipLoopOptions:
    return ClipLoopOptions(
        input_path=args.input,
        duration=args.duration,
        output_path=args.output,
        alternate_reverse=args.alternate_reverse,
        trim_start_ms=args.trim_start_ms,
        audio_path=args.audio,
        audio_alternate_reverse=args.audio_alternate_reverse,
        audio_crossfade_ms=args.audio_crossfade_ms,
        audio_gap_ms=args.audio_gap_ms,
        audio_seam_fade_ms=args.audio_seam_fade_ms,
        keep_ratio=args.keep_ratio,
        crop_corner=args.corner,
        speed_percent=args.speed,
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.tui:
        try:
            from clip_loop.tui import run_tui
        except ImportError as exc:
            sys.stderr.write(
                "clip-loop TUI requires the optional 'tui' dependency. "
                "Install with: uv sync --extra tui\n"
            )
            raise SystemExit(1) from exc
        run_tui(
            initial_input=args.input,
            initial_output=args.output,
            initial_audio=args.audio,
        )
        return
    if args.input is None:
        parser.error("the following arguments are required: input (or use --tui)")
    started = time.perf_counter()
    try:
        output_path = run_clip_loop(_namespace_to_options(args))
    except ClipLoopError as exc:
        sys.stderr.write(f"{exc}\n")
        sys.exit(1)
    elapsed = time.perf_counter() - started
    print(
        f"Wrote {output_path} ({args.duration:g}s) in {format_elapsed(elapsed)}"
    )
