"""Tests for clip_loop.parsing."""

from __future__ import annotations

import argparse

import pytest

from clip_loop.parsing import (
    format_elapsed,
    parse_crop_corner,
    parse_duration,
    parse_fill_mode,
    parse_keep_ratio,
    parse_resolution,
    parse_speed_percent,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("3600", 3600.0),
        ("1h", 3600.0),
        ("30m", 1800.0),
        ("90s", 90.0),
        (" 1H ", 3600.0),
    ],
)
def test_parse_duration_valid(value: str, expected: float) -> None:
    assert parse_duration(value) == expected


@pytest.mark.parametrize("value", ["", "  "])
def test_parse_duration_empty(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="cannot be empty"):
        parse_duration(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("80%", 0.8),
        ("0.8", 0.8),
        ("80", 0.8),
        ("100%", 1.0),
        ("1", 1.0),
    ],
)
def test_parse_keep_ratio_valid(value: str, expected: float) -> None:
    assert parse_keep_ratio(value) == expected


@pytest.mark.parametrize("value", ["", "0", "0%", "101%"])
def test_parse_keep_ratio_invalid(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        parse_keep_ratio(value)


@pytest.mark.parametrize(
    "corner",
    ["top_left", "top_right", "bottom_left", "bottom_right"],
)
def test_parse_crop_corner_valid(corner: str) -> None:
    assert parse_crop_corner(corner) == corner
    assert parse_crop_corner(corner.upper()) == corner


def test_parse_crop_corner_invalid() -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="corner must be one of"):
        parse_crop_corner("center")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("100", 100.0),
        ("80%", 80.0),
        ("120", 120.0),
    ],
)
def test_parse_speed_percent_valid(value: str, expected: float) -> None:
    assert parse_speed_percent(value) == expected


@pytest.mark.parametrize("value", ["", "0", "-10"])
def test_parse_speed_percent_invalid(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        parse_speed_percent(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1920x1080", (1920, 1080)),
        ("1921x1081", (1920, 1080)),
        (" 640 x 480 ", (640, 480)),
    ],
)
def test_parse_resolution_valid(value: str, expected: tuple[int, int]) -> None:
    assert parse_resolution(value) == expected


@pytest.mark.parametrize("value", ["", "1920", "axb", "0x1080"])
def test_parse_resolution_invalid(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        parse_resolution(value)


@pytest.mark.parametrize("mode", ["fit", "fill"])
def test_parse_fill_mode_valid(mode: str) -> None:
    assert parse_fill_mode(mode) == mode


def test_parse_fill_mode_invalid() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        parse_fill_mode("stretch")


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (12.34, "12.34s"),
        (90.0, "1m 30.0s"),
        (3661.0, "1h 1m 1.0s"),
    ],
)
def test_format_elapsed(seconds: float, expected: str) -> None:
    assert format_elapsed(seconds) == expected
