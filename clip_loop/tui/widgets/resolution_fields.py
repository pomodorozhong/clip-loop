"""Target resolution and fill mode fields."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Select

from clip_loop.tui.constants import FILL_MODE_PRESETS, RESOLUTION_PRESETS
from clip_loop.tui.widgets.field_label import FieldLabel
from clip_loop.tui.widgets.preset_input import PresetInput


class ResolutionFields(Vertical):
    """Resolution preset, custom resolution, and fill mode."""

    DEFAULT_CSS = """
    ResolutionFields {
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield FieldLabel("Target resolution")
        yield Select(RESOLUTION_PRESETS, id="resolution-preset", value="source")
        yield PresetInput(
            placeholder="e.g. 1920x1080",
            id="resolution-custom",
            disabled=True,
        )
        yield FieldLabel("Fill mode")
        yield Select(
            FILL_MODE_PRESETS,
            id="fill-mode",
            value="fit",
            disabled=True,
        )
