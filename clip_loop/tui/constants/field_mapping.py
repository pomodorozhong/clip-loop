"""Map validation field codes to TUI widget selectors."""

from __future__ import annotations

import re

from clip_loop.tui.constants.widget_ids import FIELD_TO_WIDGET

_FIELD_PATTERN = re.compile(
    r"^(video_segments|audio_segments)\[(\d+)\]\.(\w+)$"
)

_VIDEO_SEGMENT_WIDGET_SUFFIX = {
    "path": "-path",
    "trim_start_ms": "-trim-preset",
    "speed_percent": "-speed-preset",
    "keep_ratio": "-keep-ratio-preset",
    "crop_corner": "-crop-corner",
}

_AUDIO_SEGMENT_WIDGET_SUFFIX = {
    "path": "-path",
    "trim_start_ms": "-trim-preset",
}


def widget_for_field(
    field: str | None,
    *,
    video_multiple: bool,
    audio_multiple: bool,
    segment_index: int | None = None,
    duration_is_custom: bool = False,
) -> str:
    """Map a validation field code to a TUI widget selector."""
    if field is None:
        return "#input-path"
    if field == "duration" and duration_is_custom:
        return "#duration-custom"
    if not video_multiple and not audio_multiple and field in FIELD_TO_WIDGET:
        return FIELD_TO_WIDGET[field]
    if field == "video_segments":
        return "#video-segments-list"
    match = _FIELD_PATTERN.match(field)
    if match:
        group, index_str, attr = match.groups()
        index = segment_index if segment_index is not None else int(index_str)
        if group == "video_segments":
            if video_multiple:
                suffix = _VIDEO_SEGMENT_WIDGET_SUFFIX.get(attr, "-path")
                return f"#video-seg-{index}{suffix}"
            single_field = f"video_segments[0].{attr}"
            if single_field in FIELD_TO_WIDGET:
                return FIELD_TO_WIDGET[single_field]
        if group == "audio_segments":
            if audio_multiple:
                suffix = _AUDIO_SEGMENT_WIDGET_SUFFIX.get(attr, "-path")
                return f"#audio-seg-{index}{suffix}"
            single_field = f"audio_segments[0].{attr}"
            if single_field in FIELD_TO_WIDGET:
                return FIELD_TO_WIDGET[single_field]
    if field in FIELD_TO_WIDGET:
        return FIELD_TO_WIDGET[field]
    return "#input-path"
