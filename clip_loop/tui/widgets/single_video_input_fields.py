"""Single-video input tab fields."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Checkbox

from clip_loop.tui.widgets.crop_fields import CropFields
from clip_loop.tui.widgets.ms_preset_field import MsPresetField
from clip_loop.tui.widgets.path_browse_row import PathBrowseRow
from clip_loop.tui.widgets.speed_fields import SpeedFields


class SingleVideoInputFields(Vertical):
    """Fields for one video file in the Single tab."""

    DEFAULT_CSS = """
    SingleVideoInputFields {
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield PathBrowseRow(
            input_id="input-path",
            browse_id="browse-input",
            placeholder="path/to/clip.mp4",
        )
        yield MsPresetField("Trim start", "trim-preset", "trim-custom")
        yield SpeedFields(preset_id="speed-preset", custom_id="speed-custom")
        yield CropFields(
            keep_ratio_preset_id="keep-ratio-preset",
            keep_ratio_custom_id="keep-ratio-custom",
            crop_corner_id="crop-corner",
        )
        yield Checkbox(
            "Ping-pong video (--alternate-reverse)",
            id="alternate-reverse",
        )
