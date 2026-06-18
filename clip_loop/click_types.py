"""Click parameter types bridging parsing to the CLI."""

from __future__ import annotations

import click

from clip_loop.exceptions import ParseError
from clip_loop.parsing import (
    parse_crop_corner,
    parse_duration,
    parse_keep_ratio,
    parse_speed_percent,
)


class DurationParam(click.ParamType):
    name = "duration"

    def convert(
        self, value: object, param: click.Parameter | None, ctx: click.Context | None
    ) -> float:
        if isinstance(value, float):
            return value
        try:
            return parse_duration(str(value))
        except ParseError as exc:
            self.fail(str(exc), param, ctx)


class KeepRatioParam(click.ParamType):
    name = "ratio"

    def convert(
        self, value: object, param: click.Parameter | None, ctx: click.Context | None
    ) -> float:
        if isinstance(value, float):
            return value
        try:
            return parse_keep_ratio(str(value))
        except ParseError as exc:
            self.fail(str(exc), param, ctx)


class SpeedParam(click.ParamType):
    name = "percent"

    def convert(
        self, value: object, param: click.Parameter | None, ctx: click.Context | None
    ) -> float:
        if isinstance(value, float):
            return value
        try:
            return parse_speed_percent(str(value))
        except ParseError as exc:
            self.fail(str(exc), param, ctx)


class CornerParam(click.ParamType):
    name = "corner"

    def convert(
        self, value: object, param: click.Parameter | None, ctx: click.Context | None
    ) -> str:
        try:
            return parse_crop_corner(str(value))
        except ParseError as exc:
            self.fail(str(exc), param, ctx)


DURATION = DurationParam()
KEEP_RATIO = KeepRatioParam()
SPEED = SpeedParam()
CORNER = CornerParam()
