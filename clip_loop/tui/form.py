"""Read and parse clip-loop options from TUI widgets."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Protocol

from textual.widgets import Checkbox, Input, Select

from clip_loop.options import ClipLoopOptions
from clip_loop.parsing import parse_crop_corner, parse_duration, parse_keep_ratio, parse_speed_percent
from clip_loop.tui.constants import (
    DURATION_PRESETS,
    KEEP_RATIO_PRESETS,
    MS_PRESETS,
    SPEED_PRESETS,
)


class FormWidgets(Protocol):
    """Minimal widget query surface used by :class:`ClipLoopForm`."""

    def query_one(self, selector: str, expect_type: type): ...


def ms_from_select(select: Select[str], custom: Input) -> int:
    value = select.value
    if value is Select.BLANK:
        return 0
    if value == "custom":
        text = custom.value.strip()
        if not text:
            return 0
        return int(text)
    return int(value)


def duration_from_form(select: Select[str], custom: Input) -> float:
    value = select.value
    if value is Select.BLANK or value == "custom":
        text = custom.value.strip() or "1h"
        return parse_duration(text)
    return parse_duration(value)


def is_crop_enabled(select: Select[str]) -> bool:
    value = select.value
    return value is not Select.BLANK and value != "off"


def keep_ratio_from_form(select: Select[str], custom: Input) -> float:
    value = select.value
    if value is Select.BLANK or value == "off":
        raise ValueError("crop is disabled")
    if value == "custom":
        text = custom.value.strip() or "80%"
        return parse_keep_ratio(text)
    return parse_keep_ratio(value)


def speed_from_form(select: Select[str], custom: Input) -> float:
    value = select.value
    if value is Select.BLANK or value == "100":
        return 100.0
    if value == "custom":
        text = custom.value.strip() or "100"
        return parse_speed_percent(text)
    return parse_speed_percent(value)


class ClipLoopForm:
    """Reads :class:`~clip_loop.options.ClipLoopOptions` from the TUI form."""

    def __init__(self, app: FormWidgets) -> None:
        self._app = app

    def collect(self) -> ClipLoopOptions:
        input_text = self._app.query_one("#input-path", Input).value.strip()
        output_text = self._app.query_one("#output-path", Input).value.strip()
        output_path = Path(output_text) if output_text else None

        keep_ratio_select = self._app.query_one("#keep-ratio-preset", Select)
        keep_ratio: float | None = None
        crop_corner: str | None = None
        if is_crop_enabled(keep_ratio_select):
            keep_ratio = keep_ratio_from_form(
                keep_ratio_select,
                self._app.query_one("#keep-ratio-custom", Input),
            )
            crop_corner = parse_crop_corner(
                self._app.query_one("#crop-corner", Select).value
            )

        audio_text = self._app.query_one("#audio-path", Input).value.strip()
        return ClipLoopOptions(
            input_path=Path(input_text),
            duration=duration_from_form(
                self._app.query_one("#duration-preset", Select),
                self._app.query_one("#duration-custom", Input),
            ),
            output_path=output_path,
            alternate_reverse=self._app.query_one("#alternate-reverse", Checkbox).value,
            trim_start_ms=ms_from_select(
                self._app.query_one("#trim-preset", Select),
                self._app.query_one("#trim-custom", Input),
            ),
            audio_path=Path(audio_text) if audio_text else None,
            audio_alternate_reverse=self._app.query_one(
                "#audio-alternate-reverse", Checkbox
            ).value,
            audio_crossfade_ms=ms_from_select(
                self._app.query_one("#crossfade-preset", Select),
                self._app.query_one("#crossfade-custom", Input),
            ),
            audio_gap_ms=ms_from_select(
                self._app.query_one("#gap-preset", Select),
                self._app.query_one("#gap-custom", Input),
            ),
            audio_seam_fade_ms=ms_from_select(
                self._app.query_one("#seam-fade-preset", Select),
                self._app.query_one("#seam-fade-custom", Input),
            ),
            keep_ratio=keep_ratio,
            crop_corner=crop_corner,
            speed_percent=speed_from_form(
                self._app.query_one("#speed-preset", Select),
                self._app.query_one("#speed-custom", Input),
            ),
        )

    def duration_is_custom(self) -> bool:
        return self._app.query_one("#duration-preset", Select).value == "custom"

    def has_audio_path(self) -> bool:
        return bool(self._app.query_one("#audio-path", Input).value.strip())

    def browse_start_dir(self, input_id: str) -> Path:
        text = self._app.query_one(input_id, Input).value.strip() or "."
        start = Path(text)
        return start.parent if start.suffix else start

    def browse_save_defaults(self, input_id: str) -> tuple[Path, str]:
        text = self._app.query_one(input_id, Input).value.strip()
        if text:
            path = Path(text)
            if path.suffix:
                return path.parent, path.name
            return path, "output.mp4"
        input_text = self._app.query_one("#input-path", Input).value.strip()
        if input_text:
            source = Path(input_text)
            return source.parent, f"{source.stem}_looped{source.suffix or '.mp4'}"
        return Path.home(), "output.mp4"

    def sync_custom_visibility(self, preset_id: str, custom_id: str) -> None:
        select = self._app.query_one(f"#{preset_id}", Select)
        custom = self._app.query_one(f"#{custom_id}", Input)
        show = select.value == "custom"
        custom.display = show
        if not show:
            custom.value = ""

    def sync_crop_options(self) -> None:
        enabled = is_crop_enabled(self._app.query_one("#keep-ratio-preset", Select))
        custom = self._app.query_one("#keep-ratio-custom")
        corner = self._app.query_one("#crop-corner")
        custom.disabled = not enabled
        corner.disabled = not enabled
        if enabled:
            self.sync_custom_visibility("keep-ratio-preset", "keep-ratio-custom")
        else:
            custom.display = False

    def sync_audio_options(self) -> None:
        has_audio = self.has_audio_path()
        for selector in (
            "#audio-alternate-reverse",
            "#crossfade-preset",
            "#crossfade-custom",
            "#gap-preset",
            "#gap-custom",
            "#seam-fade-preset",
            "#seam-fade-custom",
        ):
            self._app.query_one(selector).disabled = not has_audio
        if has_audio:
            self._app.query_one("#audio-collapsible").collapsed = False

    def apply(self, options: ClipLoopOptions) -> None:
        """Populate the form from a :class:`ClipLoopOptions` instance."""
        self._app.query_one("#input-path", Input).value = str(options.input_path)
        self._app.query_one("#output-path", Input).value = (
            str(options.output_path) if options.output_path else ""
        )
        self._set_duration(options.duration)
        self._app.query_one("#alternate-reverse", Checkbox).value = options.alternate_reverse
        self._set_ms_field("trim-preset", "trim-custom", options.trim_start_ms)
        self._set_speed(options.speed_percent)
        self._set_keep_ratio(options.keep_ratio, options.crop_corner)
        self._app.query_one("#audio-path", Input).value = (
            str(options.audio_path) if options.audio_path else ""
        )
        self._app.query_one("#audio-alternate-reverse", Checkbox).value = (
            options.audio_alternate_reverse
        )
        self._set_ms_field("crossfade-preset", "crossfade-custom", options.audio_crossfade_ms)
        self._set_ms_field("gap-preset", "gap-custom", options.audio_gap_ms)
        self._set_ms_field("seam-fade-preset", "seam-fade-custom", options.audio_seam_fade_ms)

    def _set_ms_field(self, preset_id: str, custom_id: str, ms: int) -> None:
        select = self._app.query_one(f"#{preset_id}", Select)
        custom = self._app.query_one(f"#{custom_id}", Input)
        preset_values = {value for _, value in MS_PRESETS if value != "custom"}
        if str(ms) in preset_values:
            select.value = str(ms)
            custom.value = ""
            return
        select.value = "custom"
        custom.value = str(ms)

    def _set_duration(self, duration: float) -> None:
        select = self._app.query_one("#duration-preset", Select)
        custom = self._app.query_one("#duration-custom", Input)
        for _, value in DURATION_PRESETS:
            if value == "custom":
                continue
            if parse_duration(value) == duration:
                select.value = value
                custom.value = ""
                return
        select.value = "custom"
        custom.value = _format_duration(duration)

    def _set_speed(self, speed_percent: float) -> None:
        select = self._app.query_one("#speed-preset", Select)
        custom = self._app.query_one("#speed-custom", Input)
        if speed_percent == int(speed_percent):
            speed_text = str(int(speed_percent))
        else:
            speed_text = str(speed_percent)
        preset_values = {value for _, value in SPEED_PRESETS if value != "custom"}
        if speed_text in preset_values:
            select.value = speed_text
            custom.value = ""
            return
        select.value = "custom"
        custom.value = speed_text

    def _set_keep_ratio(
        self, keep_ratio: float | None, crop_corner: str | None
    ) -> None:
        select = self._app.query_one("#keep-ratio-preset", Select)
        custom = self._app.query_one("#keep-ratio-custom", Input)
        corner = self._app.query_one("#crop-corner", Select)
        if keep_ratio is None:
            select.value = "off"
            custom.value = ""
            corner.value = "top_left"
            return
        for _, value in KEEP_RATIO_PRESETS:
            if value in ("off", "custom"):
                continue
            if abs(parse_keep_ratio(value) - keep_ratio) < 1e-9:
                select.value = value
                custom.value = ""
                corner.value = crop_corner or "top_left"
                return
        select.value = "custom"
        custom.value = f"{keep_ratio * 100:g}%"
        corner.value = crop_corner or "top_left"


def _format_duration(duration: float) -> str:
    if duration >= 3600 and duration % 3600 == 0:
        return f"{int(duration // 3600)}h"
    if duration >= 60 and duration % 60 == 0:
        return f"{int(duration // 60)}m"
    if duration == int(duration):
        return str(int(duration))
    return str(duration)


def widget_for_clip_loop_error(message: str, *, duration_is_custom: bool) -> str:
    if "Input not found" in message:
        return "#input-path"
    if "Audio input not found" in message:
        return "#audio-path"
    if "requires --audio" in message:
        return "#audio-path"
    if "Duration must be positive" in message or "duration cannot be empty" in message:
        return "#duration-custom" if duration_is_custom else "#duration-preset"
    if "keep ratio" in message.lower():
        return "#keep-ratio-custom" if "custom" in message else "#keep-ratio-preset"
    if "speed" in message.lower():
        return "#speed-custom" if "custom" in message else "#speed-preset"
    if "--corner" in message or "corner must be" in message.lower():
        return "#crop-corner"
    if "Invalid crop" in message:
        return "#keep-ratio-preset"
    return "#input-path"


def try_parse_duration(
    select: Select[str], custom: Input
) -> tuple[float | None, str | None]:
    duration_is_custom = select.value == "custom"
    try:
        duration = duration_from_form(select, custom)
    except (ValueError, argparse.ArgumentTypeError):
        widget_id = "#duration-custom" if duration_is_custom else "#duration-preset"
        return None, widget_id
    if duration <= 0:
        return None, "#duration-custom" if duration_is_custom else "#duration-preset"
    return duration, None


def try_parse_speed(
    select: Select[str], custom: Input
) -> tuple[float | None, str | None]:
    speed_is_custom = select.value == "custom"
    try:
        return speed_from_form(select, custom), None
    except (ValueError, argparse.ArgumentTypeError):
        return None, "#speed-custom" if speed_is_custom else "#speed-preset"


def try_parse_keep_ratio(
    select: Select[str], custom: Input
) -> tuple[float | None, str | None]:
    keep_ratio_is_custom = select.value == "custom"
    try:
        return keep_ratio_from_form(select, custom), None
    except (ValueError, argparse.ArgumentTypeError):
        widget_id = (
            "#keep-ratio-custom" if keep_ratio_is_custom else "#keep-ratio-preset"
        )
        return None, widget_id
