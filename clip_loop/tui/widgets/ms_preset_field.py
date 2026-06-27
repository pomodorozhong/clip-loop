"""Millisecond preset field group."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical

from clip_loop.tui.constants import MS_PRESETS
from clip_loop.tui.widgets.preset_select_field import PresetSelectField


class MsPresetField(Vertical):
    """Millisecond preset and custom value inputs."""

    DEFAULT_CSS = """
    MsPresetField {
        height: auto;
    }
    """

    def __init__(
        self,
        label: str,
        preset_id: str,
        custom_id: str,
        *,
        value: str = "0",
        disabled: bool = False,
    ) -> None:
        super().__init__()
        self._label = label
        self._preset_id = preset_id
        self._custom_id = custom_id
        self._value = value
        self._disabled = disabled

    def compose(self) -> ComposeResult:
        yield PresetSelectField(
            self._label,
            MS_PRESETS,
            self._preset_id,
            self._custom_id,
            value=self._value,
            custom_placeholder="milliseconds",
            disabled=self._disabled,
        )
