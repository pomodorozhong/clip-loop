"""Import smoke tests for all clip_loop modules."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent / "clip_loop"


def _module_paths() -> list[str]:
    paths: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        rel = path.relative_to(ROOT.parent).with_suffix("")
        paths.append(".".join(rel.parts))
    return paths


@pytest.mark.parametrize("module_name", _module_paths())
def test_import_module(module_name: str) -> None:
    importlib.import_module(module_name)
