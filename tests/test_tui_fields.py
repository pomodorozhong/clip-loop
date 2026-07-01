"""Tests for clip_loop.tui.fields."""

from __future__ import annotations

from textual.widgets import Select

from clip_loop.tui.fields import (
    is_crop_enabled,
    is_resolution_enabled,
    ms_from_select,
    try_parse_duration,
    try_parse_keep_ratio,
    try_parse_resolution,
    try_parse_speed,
)
from tests.conftest import FakeInput, FakeSelect


def test_ms_from_select_blank() -> None:
    select = FakeSelect(value=Select.BLANK)
    custom = FakeInput()
    assert ms_from_select(select, custom) == 0  # type: ignore[arg-type]


def test_ms_from_select_preset() -> None:
    select = FakeSelect(value="500")
    custom = FakeInput()
    assert ms_from_select(select, custom) == 500  # type: ignore[arg-type]


def test_ms_from_select_custom() -> None:
    select = FakeSelect(value="custom")
    custom = FakeInput(value="750")
    assert ms_from_select(select, custom) == 750  # type: ignore[arg-type]


def test_is_crop_enabled() -> None:
    assert is_crop_enabled(FakeSelect(value=Select.BLANK)) is False  # type: ignore[arg-type]
    assert is_crop_enabled(FakeSelect(value="off")) is False  # type: ignore[arg-type]
    assert is_crop_enabled(FakeSelect(value="80%")) is True  # type: ignore[arg-type]


def test_is_resolution_enabled() -> None:
    assert is_resolution_enabled(FakeSelect(value="source")) is False  # type: ignore[arg-type]
    assert is_resolution_enabled(FakeSelect(value="1920x1080")) is True  # type: ignore[arg-type]


def test_try_parse_resolution_preset() -> None:
    select = FakeSelect(value="1920x1080")
    custom = FakeInput()
    result, widget = try_parse_resolution(select, custom)  # type: ignore[arg-type]
    assert result == (1920, 1080)
    assert widget is None


def test_try_parse_resolution_invalid() -> None:
    select = FakeSelect(value="custom")
    custom = FakeInput(value="bad")
    result, widget = try_parse_resolution(select, custom)  # type: ignore[arg-type]
    assert result is None
    assert widget == "#resolution-custom"


def test_try_parse_speed_default() -> None:
    select = FakeSelect(value="100")
    custom = FakeInput()
    result, widget = try_parse_speed(select, custom)  # type: ignore[arg-type]
    assert result == 100.0
    assert widget is None


def test_try_parse_keep_ratio_disabled() -> None:
    select = FakeSelect(value="off")
    custom = FakeInput()
    result, widget = try_parse_keep_ratio(select, custom)  # type: ignore[arg-type]
    assert result is None
    assert widget is not None


def test_try_parse_duration_custom() -> None:
    select = FakeSelect(value="custom")
    custom = FakeInput(value="30m")
    result, widget = try_parse_duration(select, custom)  # type: ignore[arg-type]
    assert result == 1800.0
    assert widget is None


def test_try_parse_duration_invalid() -> None:
    select = FakeSelect(value="custom")
    custom = FakeInput(value="")
    result, widget = try_parse_duration(select, custom)  # type: ignore[arg-type]
    assert result == 3600.0  # default 1h when custom empty
