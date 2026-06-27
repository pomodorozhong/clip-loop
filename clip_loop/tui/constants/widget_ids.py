"""TUI widget selectors and section groupings."""

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
