"""Persist and restore the last clip-loop TUI run options."""

from __future__ import annotations

import json
from pathlib import Path

from clip_loop.options import ClipLoopOptions

LAST_RUN_PATH = Path.home() / ".config" / "clip-loop" / "last_run.json"


def save_last_run(options: ClipLoopOptions) -> None:
    """Write *options* to the user's config directory."""
    LAST_RUN_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAST_RUN_PATH.write_text(json.dumps(options.to_dict(), indent=2) + "\n")


def load_last_run() -> ClipLoopOptions | None:
    """Load the most recently saved run options, if any."""
    if not LAST_RUN_PATH.is_file():
        return None
    try:
        data = json.loads(LAST_RUN_PATH.read_text())
        return ClipLoopOptions.from_dict(data)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
