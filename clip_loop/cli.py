from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def parse_duration(value: str) -> float:
    """Parse duration: plain number = seconds, or suffix h/m/s (e.g. 1h, 30m, 90s)."""
    s = value.strip().lower()
    if not s:
        raise argparse.ArgumentTypeError("duration cannot be empty")
    if s.endswith("h"):
        return float(s[:-1]) * 3600
    if s.endswith("m"):
        return float(s[:-1]) * 60
    if s.endswith("s"):
        return float(s[:-1])
    return float(s)


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_looped{input_path.suffix}")


def format_elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.2f}s"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    if h:
        return f"{h}h {m}m {s:.1f}s"
    return f"{m}m {s:.1f}s"


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        sys.stderr.write(
            "clip-loop requires ffmpeg in PATH. Install it from https://ffmpeg.org/\n"
        )
        sys.exit(1)


def ffprobe_has_audio(path: Path) -> bool:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=index",
        "-of",
        "csv=p=0",
        str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return bool(r.stdout.strip())


def build_forward_reverse_cycle(
    input_path: Path,
    cycle_path: Path,
    *,
    has_audio: bool,
    trim_start_sec: float = 0.0,
) -> None:
    """One play forward + one play backward; output length is 2× the source clip."""
    head = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
    ]
    if trim_start_sec > 0:
        head.extend(["-ss", str(trim_start_sec)])
    if has_audio:
        filt = (
            "[0:v]split[v][vr];[vr]reverse[r];[v][r]concat=n=2:v=1:a=0[vout];"
            "[0:a]asplit[a][ar];[ar]areverse[arout];[a][arout]concat=n=2:v=0:a=1[aout]"
        )
        cmd = [
            *head,
            "-i",
            str(input_path),
            "-filter_complex",
            filt,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(cycle_path),
        ]
    else:
        filt = (
            "[0:v]split[v][vr];[vr]reverse[r];[v][r]concat=n=2:v=1:a=0[vout]"
        )
        cmd = [
            *head,
            "-i",
            str(input_path),
            "-filter_complex",
            filt,
            "-map",
            "[vout]",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(cycle_path),
        ]
    subprocess.run(cmd, check=True)


def run_stream_loop_copy(
    input_path: Path,
    output_path: Path,
    duration_sec: float,
    *,
    trim_start_sec: float = 0.0,
) -> None:
    """Loop input with stream copy until duration_sec."""
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
    ]
    if trim_start_sec > 0:
        cmd.extend(["-ss", str(trim_start_sec)])
    cmd.extend(
        [
            "-stream_loop",
            "-1",
            "-i",
            str(input_path),
            "-t",
            str(duration_sec),
            "-c",
            "copy",
            str(output_path),
        ]
    )
    subprocess.run(cmd, check=True)


def run_simple_loop(
    input_path: Path,
    output_path: Path,
    duration_sec: float,
    *,
    trim_start_sec: float = 0.0,
) -> None:
    ensure_ffmpeg()
    try:
        run_stream_loop_copy(
            input_path, output_path, duration_sec, trim_start_sec=trim_start_sec
        )
    except subprocess.CalledProcessError:
        sys.stderr.write(
            "ffmpeg failed. Try re-encoding: some inputs need `-c` other than copy.\n"
        )
        sys.exit(1)


def run_alternate_reverse_loop(
    input_path: Path,
    output_path: Path,
    duration_sec: float,
    *,
    trim_start_sec: float = 0.0,
) -> None:
    ensure_ffmpeg()
    has_audio = ffprobe_has_audio(input_path)
    fd, tmp_name = tempfile.mkstemp(suffix=".mp4", prefix="clip_loop_")
    os.close(fd)
    cycle_path = Path(tmp_name)
    try:
        try:
            build_forward_reverse_cycle(
                input_path,
                cycle_path,
                has_audio=has_audio,
                trim_start_sec=trim_start_sec,
            )
        except subprocess.CalledProcessError:
            sys.stderr.write(
                "ffmpeg failed while building forward/reverse cycle. "
                "Check that the file is a supported video (and audio) format.\n"
            )
            sys.exit(1)
        try:
            run_stream_loop_copy(cycle_path, output_path, duration_sec)
        except subprocess.CalledProcessError:
            sys.stderr.write(
                "ffmpeg failed while looping the cycle to the target duration.\n"
            )
            sys.exit(1)
    finally:
        cycle_path.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="clip-loop",
        description="Loop a video clip until it reaches a target duration (default 1 hour).",
    )
    p.add_argument(
        "input",
        type=Path,
        help="Input video file",
    )
    p.add_argument(
        "-d",
        "--duration",
        type=parse_duration,
        default=parse_duration("1h"),
        help="Target length (default: 1h). Examples: 3600, 1h, 30m, 90s",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="PATH",
        help="Output file (default: <input_stem>_looped<suffix>)",
    )
    p.add_argument(
        "--alternate-reverse",
        action="store_true",
        help=(
            "After each forward play, play the clip in reverse (ping-pong), "
            "then repeat; reduces visible jumps at loop points (re-encodes)."
        ),
    )
    p.add_argument(
        "--trim-start-ms",
        type=int,
        default=0,
        metavar="N",
        help="Skip the first N milliseconds of the input before looping (default: 0).",
    )
    return p


def main() -> None:
    args = build_parser().parse_args()
    input_path: Path = args.input
    if not input_path.is_file():
        sys.stderr.write(f"Input not found: {input_path}\n")
        sys.exit(1)
    if args.duration <= 0:
        sys.stderr.write("Duration must be positive.\n")
        sys.exit(1)
    if args.trim_start_ms < 0:
        sys.stderr.write("--trim-start-ms must be non-negative.\n")
        sys.exit(1)
    trim_start_sec = args.trim_start_ms / 1000.0
    output_path = args.output if args.output else default_output_path(input_path)
    started = time.perf_counter()
    if args.alternate_reverse:
        run_alternate_reverse_loop(
            input_path, output_path, args.duration, trim_start_sec=trim_start_sec
        )
    else:
        run_simple_loop(
            input_path, output_path, args.duration, trim_start_sec=trim_start_sec
        )
    elapsed = time.perf_counter() - started
    print(
        f"Wrote {output_path} ({args.duration:g}s) in {format_elapsed(elapsed)}"
    )

