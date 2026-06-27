"""TUI widget IDs, presets, and styling constants."""

from clip_loop.tui.constants.field_mapping import widget_for_field
from clip_loop.tui.constants.presets import (
    CROP_CORNER_PRESETS,
    DURATION_PRESETS,
    FILL_MODE_PRESETS,
    KEEP_RATIO_PRESETS,
    MS_PRESETS,
    RESOLUTION_PRESETS,
    SPEED_PRESETS,
)
from clip_loop.tui.constants.styling import INVALID_CLASS
from clip_loop.tui.constants.widget_ids import (
    AUDIO_SECTION_IDS,
    FIELD_TO_WIDGET,
    HIGHLIGHTABLE_IDS,
    VIDEO_SECTION_IDS,
)

__all__ = [
    "AUDIO_SECTION_IDS",
    "CROP_CORNER_PRESETS",
    "DURATION_PRESETS",
    "FIELD_TO_WIDGET",
    "FILL_MODE_PRESETS",
    "HIGHLIGHTABLE_IDS",
    "INVALID_CLASS",
    "KEEP_RATIO_PRESETS",
    "MS_PRESETS",
    "RESOLUTION_PRESETS",
    "SPEED_PRESETS",
    "VIDEO_SECTION_IDS",
    "widget_for_field",
]
