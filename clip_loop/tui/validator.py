"""Form validation for the clip-loop TUI."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

from textual.widgets import Input, Select

from clip_loop.errors import ClipLoopError
from clip_loop.parsing import parse_crop_corner
from clip_loop.validation import validate_clip_loop_options

from clip_loop.tui.form import (
    ClipLoopForm,
    is_crop_enabled,
    ms_from_select,
    try_parse_duration,
    try_parse_keep_ratio,
    try_parse_speed,
    widget_for_clip_loop_error,
)


@dataclass
class ValidationResult:
    """Outcome of validating the TUI form before a run."""

    error_message: str | None = None
    highlight_widget_ids: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.error_message is None


class ClipLoopFormValidator:
    """Validates form state and maps errors to widget highlights."""

    def __init__(self, form: ClipLoopForm) -> None:
        self._form = form

    def validate(self) -> ValidationResult:
        app = self._form._app
        highlights: list[str] = []
        errors: list[str] = []

        input_text = app.query_one("#input-path", Input).value.strip()
        input_path: Path | None = None
        if not input_text:
            highlights.append("#input-path")
            errors.append("Input video path is required.")
        else:
            input_path = Path(input_text)
            if not input_path.is_file():
                highlights.append("#input-path")
                errors.append(f"Input not found: {input_path}")

        duration_select = app.query_one("#duration-preset", Select)
        duration_custom = app.query_one("#duration-custom", Input)
        duration_is_custom = self._form.duration_is_custom()
        duration_ok = True
        duration = 0.0
        parsed_duration, duration_widget = try_parse_duration(duration_select, duration_custom)
        if parsed_duration is None:
            duration_ok = False
            highlights.append(duration_widget or "#duration-preset")
            errors.append("Invalid duration.")
        else:
            duration = parsed_duration

        audio_text = app.query_one("#audio-path", Input).value.strip()
        audio_path = Path(audio_text) if audio_text else None

        trim_select = app.query_one("#trim-preset", Select)
        trim_custom = app.query_one("#trim-custom", Input)
        trim_start_ms = 0
        try:
            trim_start_ms = ms_from_select(trim_select, trim_custom)
        except ValueError:
            highlights.append(
                "#trim-custom" if trim_select.value == "custom" else "#trim-preset"
            )
            errors.append("Invalid trim start value.")

        speed_select = app.query_one("#speed-preset", Select)
        speed_custom = app.query_one("#speed-custom", Input)
        speed_percent, speed_widget = try_parse_speed(speed_select, speed_custom)
        if speed_percent is None:
            highlights.append(speed_widget or "#speed-preset")
            errors.append("Invalid playback speed.")

        keep_ratio_select = app.query_one("#keep-ratio-preset", Select)
        keep_ratio_custom = app.query_one("#keep-ratio-custom", Input)
        crop_enabled = is_crop_enabled(keep_ratio_select)
        keep_ratio: float | None = None
        crop_corner: str | None = None
        if crop_enabled:
            keep_ratio, keep_ratio_widget = try_parse_keep_ratio(
                keep_ratio_select, keep_ratio_custom
            )
            if keep_ratio is None:
                highlights.append(keep_ratio_widget or "#keep-ratio-preset")
                errors.append("Invalid keep ratio.")
            corner_select = app.query_one("#crop-corner", Select)
            if corner_select.value is Select.BLANK:
                highlights.append("#crop-corner")
                errors.append("Crop corner is required.")
            else:
                try:
                    crop_corner = parse_crop_corner(corner_select.value)
                except argparse.ArgumentTypeError:
                    highlights.append("#crop-corner")
                    errors.append("Invalid crop corner.")

        crossfade_select = app.query_one("#crossfade-preset", Select)
        crossfade_custom = app.query_one("#crossfade-custom", Input)
        gap_select = app.query_one("#gap-preset", Select)
        gap_custom = app.query_one("#gap-custom", Input)
        seam_select = app.query_one("#seam-fade-preset", Select)
        seam_custom = app.query_one("#seam-fade-custom", Input)

        ms_fields: list[tuple[Select[str], Input, str, str]] = [
            (crossfade_select, crossfade_custom, "crossfade", "#crossfade-preset"),
            (gap_select, gap_custom, "gap", "#gap-preset"),
            (seam_select, seam_custom, "seam fade", "#seam-fade-preset"),
        ]
        audio_crossfade_ms = 0
        audio_gap_ms = 0
        audio_seam_fade_ms = 0
        for select, custom, label, preset_id in ms_fields:
            try:
                ms = ms_from_select(select, custom)
            except ValueError:
                widget_id = (
                    preset_id.replace("-preset", "-custom")
                    if select.value == "custom"
                    else preset_id
                )
                highlights.append(widget_id)
                errors.append(f"Invalid {label} value.")
                continue
            if preset_id == "#crossfade-preset":
                audio_crossfade_ms = ms
            elif preset_id == "#gap-preset":
                audio_gap_ms = ms
            else:
                audio_seam_fade_ms = ms

        if input_path is not None and duration_ok and not errors and speed_percent is not None:
            try:
                validate_clip_loop_options(
                    input_path=input_path,
                    duration=duration,
                    trim_start_ms=trim_start_ms,
                    audio_path=audio_path,
                    audio_alternate_reverse=app.query_one(
                        "#audio-alternate-reverse"
                    ).value,
                    audio_crossfade_ms=audio_crossfade_ms,
                    audio_gap_ms=audio_gap_ms,
                    audio_seam_fade_ms=audio_seam_fade_ms,
                    keep_ratio=keep_ratio,
                    crop_corner=crop_corner,
                    speed_percent=speed_percent,
                )
            except ClipLoopError as exc:
                widget_id = widget_for_clip_loop_error(
                    str(exc), duration_is_custom=duration_is_custom
                )
                highlights.append(widget_id)
                errors.append(str(exc))

        if not errors:
            return ValidationResult()

        unique_highlights = list(dict.fromkeys(highlights))
        return ValidationResult(
            error_message="; ".join(errors),
            highlight_widget_ids=unique_highlights,
        )
