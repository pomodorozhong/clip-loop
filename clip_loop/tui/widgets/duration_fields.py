"""Target duration field group."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical

from clip_loop.tui.constants import DURATION_PRESETS
from clip_loop.tui.widgets.preset_select_field import PresetSelectField


class DurationFields(Vertical):
    """Duration preset and custom value inputs."""

    DEFAULT_CSS = """
    DurationFields {
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield PresetSelectField(
            "Target duration",
            DURATION_PRESETS,
            "duration-preset",
            "duration-custom",
            value="1h",
            custom_placeholder="e.g. 45m or 3600",
        )
