"""Shared TUI field parsing helpers."""

from __future__ import annotations

import argparse

from textual.widgets import Input, Select

from clip_loop.parsing import parse_duration, parse_keep_ratio, parse_speed_percent


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
    select: Select[str], custom: Input
) -> tuple[float | None, str | None]:
    speed_is_custom = select.value == "custom"
    try:
        value = select.value
        if value is Select.BLANK or value == "100":
            return 100.0, None
        if value == "custom":
            text = custom.value.strip() or "100"
            return parse_speed_percent(text), None
        return parse_speed_percent(value), None
    except (ValueError, argparse.ArgumentTypeError):
        return None, "#speed-custom" if speed_is_custom else "#speed-preset"


def try_parse_keep_ratio(
    select: Select[str], custom: Input
) -> tuple[float | None, str | None]:
    keep_ratio_is_custom = select.value == "custom"
    try:
        value = select.value
        if value is Select.BLANK or value == "off":
            raise ValueError("crop is disabled")
        if value == "custom":
            text = custom.value.strip() or "80%"
            return parse_keep_ratio(text), None
        return parse_keep_ratio(value), None
    except (ValueError, argparse.ArgumentTypeError):
        widget_id = (
            "#keep-ratio-custom" if keep_ratio_is_custom else "#keep-ratio-preset"
        )
        return None, widget_id


def try_parse_duration(
    select: Select[str], custom: Input
) -> tuple[float | None, str | None]:
    duration_is_custom = select.value == "custom"
    try:
        value = select.value
        if value is Select.BLANK or value == "custom":
            text = custom.value.strip() or "1h"
            duration = parse_duration(text)
        else:
            duration = parse_duration(value)
    except (ValueError, argparse.ArgumentTypeError):
        widget_id = "#duration-custom" if duration_is_custom else "#duration-preset"
        return None, widget_id
    if duration <= 0:
        return None, "#duration-custom" if duration_is_custom else "#duration-preset"
    return duration, None
