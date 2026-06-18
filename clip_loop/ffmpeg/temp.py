"""Temporary media file helpers."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def temp_media_file(*, suffix: str, prefix: str = "clip_loop_") -> Iterator[Path]:
    fd, tmp_name = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    os.close(fd)
    path = Path(tmp_name)
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)
