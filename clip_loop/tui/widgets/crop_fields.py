"""Crop before loop field group."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Select

from clip_loop.tui.constants import CROP_CORNER_PRESETS, KEEP_RATIO_PRESETS
from clip_loop.tui.widgets.field_label import FieldLabel
from clip_loop.tui.widgets.preset_select_field import PresetSelectField


class CropFields(Vertical):
    """Keep-ratio preset and crop corner selects."""

    DEFAULT_CSS = """
    CropFields {
        height: auto;
    }
    """

    def __init__(
        self,
        *,
        keep_ratio_preset_id: str,
        keep_ratio_custom_id: str,
        crop_corner_id: str,
        custom_disabled: bool = True,
        corner_disabled: bool = True,
    ) -> None:
        super().__init__()
        self._keep_ratio_preset_id = keep_ratio_preset_id
        self._keep_ratio_custom_id = keep_ratio_custom_id
        self._crop_corner_id = crop_corner_id
        self._custom_disabled = custom_disabled
        self._corner_disabled = corner_disabled

    def compose(self) -> ComposeResult:
        yield PresetSelectField(
            "Crop before loop",
            KEEP_RATIO_PRESETS,
            self._keep_ratio_preset_id,
            self._keep_ratio_custom_id,
            value="off",
            custom_placeholder="e.g. 75% or 0.75",
            custom_disabled=self._custom_disabled,
        )
        yield FieldLabel("Crop corner")
        yield Select(
            CROP_CORNER_PRESETS,
            id=self._crop_corner_id,
            value="top_left",
            disabled=self._corner_disabled,
        )
