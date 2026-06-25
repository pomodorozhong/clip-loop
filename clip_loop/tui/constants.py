"""TUI widget IDs, presets, and styling constants."""

from __future__ import annotations

import re

INVALID_CLASS = "-invalid"

_FIELD_PATTERN = re.compile(
    r"^(video_segments|audio_segments)\[(\d+)\]\.(\w+)$"
)

FIELD_TO_WIDGET: dict[str, str] = {
    "video_segments": "#video-segments-list",
    "duration": "#duration-preset",
    "target_resolution": "#resolution-preset",
    "fill_mode": "#fill-mode",
    "audio_crossfade_ms": "#crossfade-preset",
    "audio_gap_ms": "#gap-preset",
    "audio_seam_fade_ms": "#seam-fade-preset",
    "video_segments[0].path": "#input-path",
    "video_segments[0].trim_start_ms": "#trim-preset",
    "video_segments[0].speed_percent": "#speed-preset",
    "video_segments[0].keep_ratio": "#keep-ratio-preset",
    "video_segments[0].crop_corner": "#crop-corner",
    "audio_segments[0].path": "#audio-path",
    "audio_segments[0].trim_start_ms": "#audio-trim-preset",
}

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

HIGHLIGHTABLE_IDS = (
    "#input-path",
    "#duration-preset",
    "#duration-custom",
    "#output-path",
    "#resolution-preset",
    "#resolution-custom",
    "#fill-mode",
    "#audio-path",
    "#trim-preset",
    "#trim-custom",
    "#speed-preset",
    "#speed-custom",
    "#keep-ratio-preset",
    "#keep-ratio-custom",
    "#crop-corner",
    "#alternate-reverse",
    "#audio-trim-preset",
    "#audio-trim-custom",
    "#audio-alternate-reverse",
    "#crossfade-preset",
    "#crossfade-custom",
    "#gap-preset",
    "#gap-custom",
    "#seam-fade-preset",
    "#seam-fade-custom",
    "#video-segments-list",
    "#audio-segments-list",
)

AUDIO_SECTION_IDS = frozenset(
    {
        "#audio-path",
        "#audio-alternate-reverse",
        "#audio-trim-preset",
        "#audio-trim-custom",
        "#crossfade-preset",
        "#crossfade-custom",
        "#gap-preset",
        "#gap-custom",
        "#seam-fade-preset",
        "#seam-fade-custom",
        "#audio-segments-list",
    }
)
VIDEO_SECTION_IDS = frozenset(
    {
        "#resolution-preset",
        "#resolution-custom",
        "#fill-mode",
        "#input-path",
        "#trim-preset",
        "#trim-custom",
        "#speed-preset",
        "#speed-custom",
        "#keep-ratio-preset",
        "#keep-ratio-custom",
        "#crop-corner",
        "#alternate-reverse",
        "#video-segments-list",
    }
)

KEEP_RATIO_PRESETS: tuple[tuple[str, str], ...] = (
    ("Off", "off"),
    ("90%", "90%"),
    ("80%", "80%"),
    ("50%", "50%"),
    ("Custom…", "custom"),
)

CROP_CORNER_PRESETS: tuple[tuple[str, str], ...] = (
    ("Top left (keep bottom-right)", "top_left"),
    ("Top right (keep bottom-left)", "top_right"),
    ("Bottom left (keep top-right)", "bottom_left"),
    ("Bottom right (keep top-left)", "bottom_right"),
)

DURATION_PRESETS: tuple[tuple[str, str], ...] = (
    ("90 seconds", "90s"),
    ("10 minutes", "10m"),
    ("1 hour", "1h"),
    ("6 hours", "6h"),
    ("8 hours", "8h"),
    ("Custom…", "custom"),
)

MS_PRESETS: tuple[tuple[str, str], ...] = (
    ("Off (0)", "0"),
    ("50 ms", "50"),
    ("120 ms", "120"),
    ("250 ms", "250"),
    ("500 ms", "500"),
    ("1000 ms", "1000"),
    ("Custom…", "custom"),
)

SPEED_PRESETS: tuple[tuple[str, str], ...] = (
    ("50%", "50"),
    ("80%", "80"),
    ("100% (normal)", "100"),
    ("120%", "120"),
    ("150%", "150"),
    ("Custom…", "custom"),
)

RESOLUTION_PRESETS: tuple[tuple[str, str], ...] = (
    ("Source (no scaling)", "source"),
    ("720p (1280x720)", "1280x720"),
    ("1080p (1920x1080)", "1920x1080"),
    ("4K (3840x2160)", "3840x2160"),
    ("Custom…", "custom"),
)

FILL_MODE_PRESETS: tuple[tuple[str, str], ...] = (
    ("Fit (--fit, letterbox)", "fit"),
    ("Fill (--fill, crop)", "fill"),
)
