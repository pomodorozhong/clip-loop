"""Audio loop seam option fields."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical

from clip_loop.tui.widgets.ms_preset_field import MsPresetField


class AudioOptionsFields(Vertical):
    """Crossfade, gap, and seam fade controls."""

    DEFAULT_CSS = """
    AudioOptionsFields {
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield MsPresetField(
            "Crossfade at loop seams",
            "crossfade-preset",
            "crossfade-custom",
            disabled=True,
        )
        yield MsPresetField(
            "Silence gap between loops",
            "gap-preset",
            "gap-custom",
            disabled=True,
        )
        yield MsPresetField(
            "Seam fade in/out",
            "seam-fade-preset",
            "seam-fade-custom",
            disabled=True,
        )
