"""Label + preset Select + custom PresetInput trio."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Select

from clip_loop.tui.widgets.field_label import FieldLabel
from clip_loop.tui.widgets.preset_input import PresetInput


class PresetSelectField(Vertical):
    """Reusable preset select with optional custom value input."""

    DEFAULT_CSS = """
    PresetSelectField {
        height: auto;
    }
    """

    def __init__(
        self,
        label: str,
        presets: tuple[tuple[str, str], ...],
        preset_id: str,
        custom_id: str,
        *,
        value: str,
        custom_placeholder: str,
        disabled: bool = False,
        custom_disabled: bool | None = None,
    ) -> None:
        super().__init__()
        self._label = label
        self._presets = presets
        self._preset_id = preset_id
        self._custom_id = custom_id
        self._value = value
        self._custom_placeholder = custom_placeholder
        self._disabled = disabled
        self._custom_disabled = custom_disabled

    def compose(self) -> ComposeResult:
        yield FieldLabel(self._label)
        yield Select(
            self._presets,
            id=self._preset_id,
            value=self._value,
            disabled=self._disabled,
        )
        yield PresetInput(
            placeholder=self._custom_placeholder,
            id=self._custom_id,
            disabled=self._custom_disabled
            if self._custom_disabled is not None
            else self._disabled,
        )
