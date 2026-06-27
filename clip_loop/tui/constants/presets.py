"""Select preset option tuples for the clip-loop TUI."""

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
