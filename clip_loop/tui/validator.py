"""Form validation for the clip-loop TUI."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from textual.widgets import Input, Select

from clip_loop.errors import ClipLoopError
from clip_loop.validation import validate_clip_loop_options

from clip_loop.tui.constants import widget_for_field
from clip_loop.tui.fields import (
    is_crop_enabled,
    ms_from_select,
    try_parse_duration,
    try_parse_keep_ratio,
    try_parse_speed,
)
from clip_loop.tui.form import ClipLoopForm


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
        highlights: list[str] = []
        errors: list[str] = []
        app = self._form._app
        duration_is_custom = self._form.duration_is_custom()
        video_multiple = self._form.video_mode_is_multiple()
        audio_multiple = self._form.audio_mode_is_multiple()

        duration_select = app.query_one("#duration-preset", Select)
        duration_custom = app.query_one("#duration-custom", Input)
        _, duration_widget = try_parse_duration(duration_select, duration_custom)
        if duration_widget:
            highlights.append(duration_widget)
            errors.append("Invalid duration.")

        for select_id, custom_id, label in (
            ("crossfade-preset", "crossfade-custom", "crossfade"),
            ("gap-preset", "gap-custom", "gap"),
            ("seam-fade-preset", "seam-fade-custom", "seam fade"),
        ):
            select = app.query_one(f"#{select_id}", Select)
            custom = app.query_one(f"#{custom_id}", Input)
            try:
                ms_from_select(select, custom)
            except ValueError:
                widget_id = (
                    f"#{custom_id}" if select.value == "custom" else f"#{select_id}"
                )
                highlights.append(widget_id)
                errors.append(f"Invalid {label} value.")

        if video_multiple:
            if not self._form.video_rows.read_segments():
                highlights.append("#video-segments-list")
                errors.append("At least one video path is required in Multiple mode.")
            else:
                self._validate_video_rows(highlights, errors)
        else:
            self._validate_single_video(highlights, errors)

        if not audio_multiple:
            self._validate_single_audio(highlights, errors)
        else:
            self._validate_audio_rows(highlights, errors)

        if not errors:
            try:
                options = self._form.collect()
                validate_clip_loop_options(options)
            except ClipLoopError as exc:
                highlights.append(
                    widget_for_field(
                        exc.field,
                        video_multiple=video_multiple,
                        audio_multiple=audio_multiple,
                        segment_index=exc.segment_index,
                        duration_is_custom=duration_is_custom,
                    )
                )
                errors.append(str(exc))
            except ValueError as exc:
                errors.append(str(exc))

        if not errors:
            return ValidationResult()

        return ValidationResult(
            error_message="; ".join(errors),
            highlight_widget_ids=list(dict.fromkeys(highlights)),
        )

    def _validate_single_video(self, highlights: list[str], errors: list[str]) -> None:
        app = self._form._app
        input_text = app.query_one("#input-path", Input).value.strip()
        if not input_text:
            highlights.append("#input-path")
            errors.append("Input video path is required.")
            return

        trim_select = app.query_one("#trim-preset", Select)
        trim_custom = app.query_one("#trim-custom", Input)
        try:
            ms_from_select(trim_select, trim_custom)
        except ValueError:
            highlights.append(
                "#trim-custom" if trim_select.value == "custom" else "#trim-preset"
            )
            errors.append("Invalid trim start value.")

        speed_select = app.query_one("#speed-preset", Select)
        speed_custom = app.query_one("#speed-custom", Input)
        _, speed_widget = try_parse_speed(speed_select, speed_custom)
        if speed_widget:
            highlights.append(speed_widget)
            errors.append("Invalid playback speed.")

        keep_ratio_select = app.query_one("#keep-ratio-preset", Select)
        keep_ratio_custom = app.query_one("#keep-ratio-custom", Input)
        if is_crop_enabled(keep_ratio_select):
            _, keep_ratio_widget = try_parse_keep_ratio(
                keep_ratio_select, keep_ratio_custom
            )
            if keep_ratio_widget:
                highlights.append(keep_ratio_widget)
                errors.append("Invalid keep ratio.")
            corner_select = app.query_one("#crop-corner", Select)
            if corner_select.value is Select.BLANK:
                highlights.append("#crop-corner")
                errors.append("Crop corner is required.")

    def _validate_single_audio(self, highlights: list[str], errors: list[str]) -> None:
        app = self._form._app
        audio_text = app.query_one("#audio-path", Input).value.strip()
        if not audio_text:
            return
        trim_select = app.query_one("#audio-trim-preset", Select)
        trim_custom = app.query_one("#audio-trim-custom", Input)
        try:
            ms_from_select(trim_select, trim_custom)
        except ValueError:
            highlights.append(
                "#audio-trim-custom"
                if trim_select.value == "custom"
                else "#audio-trim-preset"
            )
            errors.append("Invalid audio trim start value.")

    def _validate_video_rows(self, highlights: list[str], errors: list[str]) -> None:
        for row in self._form.video_rows._rows():
            prefix = f"#video-seg-{row.index}"
            path_text = row.query_one(f"{prefix}-path", Input).value.strip()
            if not path_text:
                continue
            speed_select = row.query_one(f"{prefix}-speed-preset", Select)
            speed_custom = row.query_one(f"{prefix}-speed-custom", Input)
            _, speed_widget = try_parse_speed(
                speed_select, speed_custom, id_prefix=f"video-seg-{row.index}"
            )
            if speed_widget:
                highlights.append(speed_widget)
                errors.append("Invalid playback speed.")
            keep_ratio_select = row.query_one(f"{prefix}-keep-ratio-preset", Select)
            keep_ratio_custom = row.query_one(f"{prefix}-keep-ratio-custom", Input)
            if is_crop_enabled(keep_ratio_select):
                _, keep_ratio_widget = try_parse_keep_ratio(
                    keep_ratio_select, keep_ratio_custom, id_prefix=f"video-seg-{row.index}"
                )
                if keep_ratio_widget:
                    highlights.append(keep_ratio_widget)
                    errors.append("Invalid keep ratio.")
                corner_select = row.query_one(f"{prefix}-crop-corner", Select)
                if corner_select.value is Select.BLANK:
                    highlights.append(f"{prefix}-crop-corner")
                    errors.append("Crop corner is required.")
            trim_select = row.query_one(f"{prefix}-trim-preset", Select)
            trim_custom = row.query_one(f"{prefix}-trim-custom", Input)
            try:
                ms_from_select(trim_select, trim_custom)
            except ValueError:
                highlights.append(
                    f"{prefix}-trim-custom"
                    if trim_select.value == "custom"
                    else f"{prefix}-trim-preset"
                )
                errors.append("Invalid trim start value.")

    def _validate_audio_rows(self, highlights: list[str], errors: list[str]) -> None:
        for row in self._form.audio_rows._rows():
            prefix = f"#audio-seg-{row.index}"
            path_text = row.query_one(f"{prefix}-path", Input).value.strip()
            if not path_text:
                continue
            trim_select = row.query_one(f"{prefix}-trim-preset", Select)
            trim_custom = row.query_one(f"{prefix}-trim-custom", Input)
            try:
                ms_from_select(trim_select, trim_custom)
            except ValueError:
                highlights.append(
                    f"{prefix}-trim-custom"
                    if trim_select.value == "custom"
                    else f"{prefix}-trim-preset"
                )
                errors.append("Invalid audio trim start value.")
