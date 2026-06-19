"""TUI widget IDs, presets, and styling constants."""

INVALID_CLASS = "-invalid"

HIGHLIGHTABLE_IDS = (
    "#input-path",
    "#duration-preset",
    "#duration-custom",
    "#output-path",
    "#audio-path",
    "#trim-preset",
    "#trim-custom",
    "#speed-preset",
    "#speed-custom",
    "#keep-ratio-preset",
    "#keep-ratio-custom",
    "#crop-corner",
    "#crossfade-preset",
    "#crossfade-custom",
    "#gap-preset",
    "#gap-custom",
    "#seam-fade-preset",
    "#seam-fade-custom",
)

AUDIO_SECTION_IDS = frozenset(
    {
        "#audio-path",
        "#audio-alternate-reverse",
        "#crossfade-preset",
        "#crossfade-custom",
        "#gap-preset",
        "#gap-custom",
        "#seam-fade-preset",
        "#seam-fade-custom",
    }
)
VIDEO_SECTION_IDS = frozenset(
    {
        "#trim-preset",
        "#trim-custom",
        "#speed-preset",
        "#speed-custom",
        "#keep-ratio-preset",
        "#keep-ratio-custom",
        "#crop-corner",
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

APP_CSS = """
Screen {
    layout: vertical;
}
VerticalScroll {
    height: 1fr;
    padding: 0 1;
}
.field-label {
    margin-top: 1;
    text-style: bold;
}
.field-row {
    height: auto;
    margin-bottom: 1;
}
.field-row Input {
    width: 1fr;
}
Input.-invalid {
    border: tall $error;
}
Select.-invalid {
    border: tall $error;
}
Collapsible {
    margin: 1 0;
    border: solid $primary;
    padding: 0 1 1 1;
}
#run-progress {
    display: none;
    height: auto;
    margin: 0 1;
    padding: 1;
    border: solid $primary;
    background: $surface;
}
#run-progress.visible {
    display: block;
}
.run-progress-row {
    height: auto;
    align: left middle;
}
#run-spinner {
    width: auto;
    height: 3;
    min-height: 3;
    margin-right: 1;
}
.run-progress-text {
    height: auto;
    width: 1fr;
}
#run-message {
    text-style: bold;
}
#run-timer {
    color: $accent;
    margin-top: 1;
}
#status {
    height: auto;
    padding: 0 1;
    color: $warning;
}
#action-row {
    height: auto;
    padding: 0 1 1 1;
    align: center middle;
}
#action-row Button {
    margin-right: 1;
}
FilePickScreen DirectoryTree {
    height: 1fr;
}
.pick-actions {
    height: auto;
    padding: 1;
    align: center middle;
}
"""
