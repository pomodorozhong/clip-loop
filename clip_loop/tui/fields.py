"""Shared TUI field parsing helpers."""

from __future__ import annotations

import argparse

from textual.widgets import Input, Select

from clip_loop.parsing import (
    parse_duration as parse_duration_text,
    parse_keep_ratio as parse_keep_ratio_text,
    parse_speed_percent,
)


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


def is_crop_enabled(select: Select[str]) -> bool:
    value = select.value
    return value is not Select.BLANK and value != "off"


def try_parse_speed(
    select: Select[str], custom: Input, *, id_prefix: str = ""
) -> tuple[float | None, str | None]:
    speed_is_custom = select.value == "custom"
    preset_id = f"#{id_prefix}-speed-preset" if id_prefix else "#speed-preset"
    custom_id = f"#{id_prefix}-speed-custom" if id_prefix else "#speed-custom"
    try:
        value = select.value
        if value is Select.BLANK or value == "100":
            return 100.0, None
        if value == "custom":
            text = custom.value.strip() or "100"
            return parse_speed_percent(text), None
        return parse_speed_percent(value), None
    except (ValueError, argparse.ArgumentTypeError):
        return None, custom_id if speed_is_custom else preset_id


def try_parse_keep_ratio(
    select: Select[str], custom: Input, *, id_prefix: str = ""
) -> tuple[float | None, str | None]:
    keep_ratio_is_custom = select.value == "custom"
    preset_id = f"#{id_prefix}-keep-ratio-preset" if id_prefix else "#keep-ratio-preset"
    custom_id = f"#{id_prefix}-keep-ratio-custom" if id_prefix else "#keep-ratio-custom"
    try:
        value = select.value
        if value is Select.BLANK or value == "off":
            raise ValueError("crop is disabled")
        if value == "custom":
            text = custom.value.strip() or "80%"
            return parse_keep_ratio_text(text), None
        return parse_keep_ratio_text(value), None
    except (ValueError, argparse.ArgumentTypeError):
        return None, custom_id if keep_ratio_is_custom else preset_id


def try_parse_duration(
    select: Select[str], custom: Input
) -> tuple[float | None, str | None]:
    duration_is_custom = select.value == "custom"
    try:
        value = select.value
        if value is Select.BLANK or value == "custom":
            text = custom.value.strip() or "1h"
            duration = parse_duration_text(text)
        else:
            duration = parse_duration_text(value)
    except (ValueError, argparse.ArgumentTypeError):
        widget_id = "#duration-custom" if duration_is_custom else "#duration-preset"
        return None, widget_id
    if duration <= 0:
        return None, "#duration-custom" if duration_is_custom else "#duration-preset"
    return duration, None


def parse_speed(select: Select[str], custom: Input) -> float:
    result, widget = try_parse_speed(select, custom)
    if result is None:
        raise ValueError("invalid speed")
    return result


def parse_keep_ratio(select: Select[str], custom: Input) -> float:
    result, widget = try_parse_keep_ratio(select, custom)
    if result is None:
        raise ValueError("invalid keep ratio")
    return result


def parse_duration_field(select: Select[str], custom: Input) -> float:
    result, widget = try_parse_duration(select, custom)
    if result is None:
        raise ValueError("invalid duration")
    return result
