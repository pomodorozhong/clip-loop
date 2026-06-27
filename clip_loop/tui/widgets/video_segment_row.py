"""Video segment row widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Button, Checkbox

from clip_loop.tui.widgets.collapsible_segment_row import CollapsibleSegmentRow
from clip_loop.tui.widgets.crop_fields import CropFields
from clip_loop.tui.widgets.ms_preset_field import MsPresetField
from clip_loop.tui.widgets.path_browse_row import PathBrowseRow
from clip_loop.tui.widgets.speed_fields import SpeedFields


class VideoSegmentRow(CollapsibleSegmentRow):
    """One video segment row in the Multiple tab."""

    ROW_PREFIX = "video-seg"
    TITLE_PREFIX = "Video"

    DEFAULT_CSS = """
    VideoSegmentRow Select {
        width: 1fr;
    }
    """

    def _content(self) -> ComposeResult:
        prefix = f"{self.ROW_PREFIX}-{self.index}"
        yield PathBrowseRow(
            input_id=f"{prefix}-path",
            browse_id=f"{prefix}-browse",
            placeholder="path/to/clip.mp4",
        )
        yield MsPresetField(
            "Trim start",
            f"{prefix}-trim-preset",
            f"{prefix}-trim-custom",
        )
        yield SpeedFields(
            preset_id=f"{prefix}-speed-preset",
            custom_id=f"{prefix}-speed-custom",
        )
        yield CropFields(
            keep_ratio_preset_id=f"{prefix}-keep-ratio-preset",
            keep_ratio_custom_id=f"{prefix}-keep-ratio-custom",
            crop_corner_id=f"{prefix}-crop-corner",
        )
        yield Checkbox("Ping-pong video", id=f"{prefix}-alternate-reverse")
