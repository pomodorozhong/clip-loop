"""Generate ffmpeg test media under tests/fixtures/ (not committed to git)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from clip_loop.ffmpeg import ensure_ffmpeg

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

FIXTURE_SPECS: dict[str, list[str]] = {
    "sample.mp4": [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=2:size=320x240:rate=30",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=2",
        "-shortest",
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
    ],
    "sample.m4a": [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=2",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
    ],
    "sample_noaudio.mp4": [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=2:size=320x240:rate=30",
        "-pix_fmt",
        "yuv420p",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
    ],
}


def generate_fixtures(*, force: bool = False) -> list[Path]:
    """Create missing fixture files; return paths written or skipped."""
    ensure_ffmpeg()
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, cmd_prefix in FIXTURE_SPECS.items():
        dest = FIXTURES_DIR / name
        if dest.is_file() and not force:
            continue
        cmd = [*cmd_prefix, str(dest)]
        subprocess.run(cmd, check=True)
        written.append(dest)
    return written


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate ffmpeg test fixtures under tests/fixtures/"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate fixtures even if they already exist",
    )
    args = parser.parse_args(argv)
    try:
        written = generate_fixtures(force=args.force)
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(f"ffmpeg failed while generating fixtures: {exc}\n")
        raise SystemExit(1) from exc
    except Exception as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc
    if written:
        for path in written:
            print(f"Wrote {path}")
    else:
        print("All fixtures already present (use --force to regenerate)")


if __name__ == "__main__":
    main()
