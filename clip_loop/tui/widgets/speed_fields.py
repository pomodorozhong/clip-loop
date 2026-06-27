"""Playback speed field group."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical

from clip_loop.tui.constants import SPEED_PRESETS
from clip_loop.tui.widgets.preset_select_field import PresetSelectField


class SpeedFields(Vertical):
    """Speed preset and custom value inputs."""

    DEFAULT_CSS = """
    SpeedFields {
        height: auto;
    }
    """

    def __init__(
        self,
        *,
        preset_id: str,
        custom_id: str,
        value: str = "100",
        disabled: bool = False,
    ) -> None:
        super().__init__()
        self._preset_id = preset_id
        self._custom_id = custom_id
        self._value = value
        self._disabled = disabled

    def compose(self) -> ComposeResult:
        yield PresetSelectField(
            "Playback speed",
            SPEED_PRESETS,
            self._preset_id,
            self._custom_id,
            value=self._value,
            custom_placeholder="e.g. 80 or 120",
            disabled=self._disabled,
        )
