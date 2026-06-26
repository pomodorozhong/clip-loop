"""Interactive terminal UI for configuring and running clip-loop."""

from __future__ import annotations

from pathlib import Path

from clip_loop.options import ClipLoopOptions
from clip_loop.tui.app import ClipLoopApp


def run_tui(
    *,
    initial_input: Path | None = None,
    initial_output: Path | None = None,
    initial_audio: Path | None = None,
    initial_options: ClipLoopOptions | None = None,
) -> None:
    """Launch the interactive setup UI."""
    ClipLoopApp(
        initial_input=initial_input,
        initial_output=initial_output,
        initial_audio=initial_audio,
        initial_options=initial_options,
    ).run()
