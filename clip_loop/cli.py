"""Command-line entry point for clip-loop."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import click

from clip_loop.click_types import CORNER, DURATION, KEEP_RATIO, SPEED
from clip_loop.exceptions import ClipLoopError, FfmpegError
from clip_loop.models import ClipLoopOptions
from clip_loop.parsing import CROP_CORNERS, format_elapsed
from clip_loop.service import ClipLoopService


def _open_tui(ctx: click.Context, param: click.Parameter, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return
    _run_trogon(ctx.find_root().command)


def _run_trogon(cli: click.Command) -> None:
    try:
        from trogon.trogon import Trogon
    except ImportError as exc:
        raise click.ClickException(
            "clip-loop TUI requires the optional 'tui' dependency. "
            "Install with: uv sync --extra tui"
        ) from exc
    Trogon(cli, app_name="clip-loop").run()


@click.command(
    name="run",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.argument(
    "input",
    required=False,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--tui",
    is_flag=True,
    expose_value=False,
    is_eager=True,
    callback=_open_tui,
    help="Open an interactive terminal UI to configure options.",
)
@click.option(
    "-d",
    "--duration",
    type=DURATION,
    default="1h",
    show_default=True,
    help="Target length. Examples: 3600, 1h, 30m, 90s",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output file (default: <input_stem>_looped<suffix>)",
)
@click.option(
    "--alternate-reverse",
    is_flag=True,
    help=(
        "After each forward play, play the clip in reverse (ping-pong), "
        "then repeat; reduces visible jumps at loop points (re-encodes)."
    ),
)
@click.option(
    "--trim-start-ms",
    type=int,
    default=0,
    show_default=True,
    help="Skip the first N milliseconds of the input before looping.",
)
@click.option(
    "--speed",
    type=SPEED,
    default="100",
    show_default=True,
    help=(
        "Playback speed as a percentage of normal. "
        "Examples: 80 for 80%%, 120 for 120%%. Re-encodes when not 100."
    ),
)
@click.option(
    "--audio",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help=(
        "Optional external audio file (e.g. mp3). "
        "Will loop/trim as needed to match the output duration."
    ),
)
@click.option(
    "--audio-alternate-reverse",
    is_flag=True,
    help=(
        "With --audio, make one audio cycle as forward then reversed, "
        "then repeat. Independent of --alternate-reverse."
    ),
)
@click.option(
    "--audio-crossfade-ms",
    type=int,
    default=0,
    show_default=True,
    help=(
        "With --audio, crossfade each stitched audio seam by N milliseconds "
        "(0 = disabled)."
    ),
)
@click.option(
    "--audio-gap-ms",
    type=int,
    default=0,
    show_default=True,
    help=(
        "With --audio, append N milliseconds of silence between stitched "
        "audio clips (0 = disabled)."
    ),
)
@click.option(
    "--audio-seam-fade-ms",
    type=int,
    default=0,
    show_default=True,
    help=(
        "With --audio, fade volume down near the end and up at the start "
        "of each stitched clip by N milliseconds (0 = disabled)."
    ),
)
@click.option(
    "--keep-ratio",
    type=KEEP_RATIO,
    help=(
        "Before looping, crop away a corner and scale back to the original "
        "frame size. Requires --corner. Examples: 80%%, 50%%, 0.8"
    ),
)
@click.option(
    "--corner",
    type=CORNER,
    help=(
        "With --keep-ratio, corner to remove "
        f"({', '.join(sorted(CROP_CORNERS))}). top_left keeps bottom-right; "
        "top_right keeps bottom-left; bottom_left keeps top-right; "
        "bottom_right keeps top-left."
    ),
)
def run(
    input: Path | None,
    duration: float,
    output: Path | None,
    alternate_reverse: bool,
    trim_start_ms: int,
    speed: float,
    audio: Path | None,
    audio_alternate_reverse: bool,
    audio_crossfade_ms: int,
    audio_gap_ms: int,
    audio_seam_fade_ms: int,
    keep_ratio: float | None,
    corner: str | None,
) -> None:
    """Loop a video clip until it reaches a target duration."""
    if input is None:
        raise click.UsageError("Missing argument 'INPUT' (or use 'clip-loop tui')")

    options = ClipLoopOptions(
        input_path=input,
        duration=duration,
        output_path=output,
        alternate_reverse=alternate_reverse,
        trim_start_ms=trim_start_ms,
        audio_path=audio,
        audio_alternate_reverse=audio_alternate_reverse,
        audio_crossfade_ms=audio_crossfade_ms,
        audio_gap_ms=audio_gap_ms,
        audio_seam_fade_ms=audio_seam_fade_ms,
        keep_ratio=keep_ratio,
        crop_corner=corner,
        speed_percent=speed,
    )

    started = time.perf_counter()
    try:
        output_path = ClipLoopService().run(options)
    except (ClipLoopError, FfmpegError) as exc:
        raise click.ClickException(str(exc)) from exc
    elapsed = time.perf_counter() - started
    click.echo(f"Wrote {output_path} ({duration:g}s) in {format_elapsed(elapsed)}")


def _make_cli() -> click.Group:
    try:
        from trogon import tui

        return tui(name="clip-loop")(run)
    except ImportError:
        group = click.Group(
            context_settings={"help_option_names": ["-h", "--help"]},
        )

        @group.command(name="tui", help="Open an interactive terminal UI.")
        def tui_command() -> None:
            _run_trogon(group)

        group.add_command(run)
        return group


cli = _make_cli()


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] not in ("run", "tui"):
        sys.argv.insert(1, "run")
    cli(prog_name="clip-loop")
