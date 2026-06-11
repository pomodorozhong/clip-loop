from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


class ClipLoopError(Exception):
    """Validation or processing error for clip-loop."""


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


def default_crop_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_cropped{input_path.suffix}")


CROP_CORNERS = frozenset({"top_left", "top_right", "bottom_left", "bottom_right"})


def parse_keep_ratio(value: str) -> float:
    """Parse keep ratio: 80%, 50%, 0.8, or 80 (percent)."""
    s = value.strip().lower()
    if not s:
        raise argparse.ArgumentTypeError("keep ratio cannot be empty")
    if s.endswith("%"):
        ratio = float(s[:-1]) / 100.0
    else:
        ratio = float(s)
        if ratio > 1.0:
            ratio /= 100.0
    if not 0.0 < ratio <= 1.0:
        raise argparse.ArgumentTypeError("keep ratio must be between 0 and 100%")
    return ratio


def parse_crop_corner(value: str) -> str:
    corner = value.strip().lower()
    if corner not in CROP_CORNERS:
        choices = ", ".join(sorted(CROP_CORNERS))
        raise argparse.ArgumentTypeError(f"corner must be one of: {choices}")
    return corner


def parse_speed_percent(value: str) -> float:
    """Parse speed: 80, 80%, 120, or 120% (percent of normal playback)."""
    s = value.strip().lower()
    if not s:
        raise argparse.ArgumentTypeError("speed cannot be empty")
    if s.endswith("%"):
        percent = float(s[:-1])
    else:
        percent = float(s)
    if percent <= 0:
        raise argparse.ArgumentTypeError("speed must be positive")
    return percent


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


def ffprobe_video_size(path: Path) -> tuple[int, int]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0:s=x",
        str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, check=True)
    value = r.stdout.strip()
    if not value or "x" not in value:
        raise ValueError(f"ffprobe could not determine video size: {path}")
    width_str, height_str = value.split("x", 1)
    return int(width_str), int(height_str)


def compute_crop_rect(
    width: int,
    height: int,
    keep_ratio: float,
    corner: str,
) -> tuple[int, int, int, int]:
    """Return crop_w, crop_h, x, y for the kept region (even dimensions)."""
    crop_w = int(width * keep_ratio)
    crop_h = int(height * keep_ratio)
    crop_w -= crop_w % 2
    crop_h -= crop_h % 2
    if crop_w <= 0 or crop_h <= 0:
        raise ValueError("keep ratio is too small for this video size")
    if crop_w > width or crop_h > height:
        raise ValueError("keep ratio must be at most 100%")

    if corner == "top_left":
        x = width - crop_w
        y = height - crop_h
    elif corner == "top_right":
        x = 0
        y = height - crop_h
    elif corner == "bottom_left":
        x = width - crop_w
        y = 0
    else:  # bottom_right
        x = 0
        y = 0
    return crop_w, crop_h, x, y


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


def ffprobe_audio_duration_sec(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, check=True)
    value = r.stdout.strip()
    if not value:
        raise ValueError(f"ffprobe could not determine audio duration: {path}")
    return float(value)


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


def apply_external_audio(
    video_path: Path, output_path: Path, audio_path: Path, duration_sec: float
) -> None:
    """Replace video audio with an external track, looping/trimming to duration."""
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-stream_loop",
        "-1",
        "-i",
        str(audio_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-t",
        str(duration_sec),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def build_forward_reverse_audio_cycle(audio_path: Path, cycle_path: Path) -> None:
    """Create one audio cycle: forward then reversed."""
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(audio_path),
        "-filter_complex",
        "[0:a]asplit[a][ar];[ar]areverse[arout];[a][arout]concat=n=2:v=0:a=1[aout]",
        "-map",
        "[aout]",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(cycle_path),
    ]
    subprocess.run(cmd, check=True)


def build_crossfaded_audio_cycle(
    audio_path: Path, cycle_path: Path, *, crossfade_sec: float
) -> None:
    """Create one cycle with a crossfaded loop seam."""
    duration_sec = ffprobe_audio_duration_sec(audio_path)
    # acrossfade requires d > 0 and works best when strictly shorter than half the cycle.
    max_crossfade_sec = duration_sec * 0.49
    effective_crossfade_sec = min(crossfade_sec, max_crossfade_sec)
    if effective_crossfade_sec <= 0:
        raise ValueError("effective crossfade duration must be positive")

    filt = (
        f"[0:a][1:a]acrossfade=d={effective_crossfade_sec}:c1=tri:c2=tri[xf];"
        f"[xf]atrim=start={effective_crossfade_sec}:end={duration_sec + effective_crossfade_sec},"
        "asetpts=PTS-STARTPTS[aout]"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(audio_path),
        "-i",
        str(audio_path),
        "-filter_complex",
        filt,
        "-map",
        "[aout]",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(cycle_path),
    ]
    subprocess.run(cmd, check=True)


def build_gapped_audio_cycle(audio_path: Path, cycle_path: Path, *, gap_sec: float) -> None:
    """Create one cycle by appending silence to the end."""
    duration_sec = ffprobe_audio_duration_sec(audio_path)
    total_sec = duration_sec + gap_sec
    filt = f"[0:a]apad=pad_dur={gap_sec},atrim=end={total_sec},asetpts=PTS-STARTPTS[aout]"
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(audio_path),
        "-filter_complex",
        filt,
        "-map",
        "[aout]",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(cycle_path),
    ]
    subprocess.run(cmd, check=True)


def build_seam_faded_audio_cycle(
    audio_path: Path, cycle_path: Path, *, fade_sec: float
) -> None:
    """Create one cycle with fade-in/out at both seam edges."""
    duration_sec = ffprobe_audio_duration_sec(audio_path)
    # Keep in/out windows from fully consuming short cycles.
    effective_fade_sec = min(fade_sec, duration_sec * 0.49)
    if effective_fade_sec <= 0:
        raise ValueError("effective seam fade duration must be positive")
    fade_out_start_sec = max(duration_sec - effective_fade_sec, 0.0)
    filt = (
        f"[0:a]afade=t=in:st=0:d={effective_fade_sec},"
        f"afade=t=out:st={fade_out_start_sec}:d={effective_fade_sec},"
        "asetpts=PTS-STARTPTS[aout]"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(audio_path),
        "-filter_complex",
        filt,
        "-map",
        "[aout]",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(cycle_path),
    ]
    subprocess.run(cmd, check=True)


def loop_video_with_optional_audio(
    input_path: Path,
    output_path: Path,
    duration_sec: float,
    *,
    trim_start_sec: float = 0.0,
    external_audio_path: Path | None = None,
    audio_alternate_reverse: bool = False,
    audio_crossfade_sec: float = 0.0,
    audio_gap_sec: float = 0.0,
    audio_seam_fade_sec: float = 0.0,
) -> None:
    """Build looped video, optionally replacing audio from an external file."""
    if external_audio_path is None:
        run_simple_loop(
            input_path, output_path, duration_sec, trim_start_sec=trim_start_sec
        )
        return
    fd, tmp_name = tempfile.mkstemp(suffix=output_path.suffix or ".mp4", prefix="clip_loop_")
    os.close(fd)
    temp_video_path = Path(tmp_name)
    temp_audio_cycle_path: Path | None = None
    temp_audio_gap_cycle_path: Path | None = None
    temp_audio_crossfade_cycle_path: Path | None = None
    temp_audio_seam_fade_cycle_path: Path | None = None
    try:
        run_simple_loop(
            input_path, temp_video_path, duration_sec, trim_start_sec=trim_start_sec
        )
        audio_source_path = external_audio_path
        if audio_alternate_reverse:
            fd2, audio_tmp_name = tempfile.mkstemp(suffix=".m4a", prefix="clip_loop_")
            os.close(fd2)
            temp_audio_cycle_path = Path(audio_tmp_name)
            build_forward_reverse_audio_cycle(external_audio_path, temp_audio_cycle_path)
            audio_source_path = temp_audio_cycle_path
        if audio_gap_sec > 0:
            fd4, audio_gap_tmp_name = tempfile.mkstemp(suffix=".m4a", prefix="clip_loop_")
            os.close(fd4)
            temp_audio_gap_cycle_path = Path(audio_gap_tmp_name)
            build_gapped_audio_cycle(
                audio_source_path,
                temp_audio_gap_cycle_path,
                gap_sec=audio_gap_sec,
            )
            audio_source_path = temp_audio_gap_cycle_path
        if audio_crossfade_sec > 0:
            fd3, audio_xf_tmp_name = tempfile.mkstemp(suffix=".m4a", prefix="clip_loop_")
            os.close(fd3)
            temp_audio_crossfade_cycle_path = Path(audio_xf_tmp_name)
            build_crossfaded_audio_cycle(
                audio_source_path,
                temp_audio_crossfade_cycle_path,
                crossfade_sec=audio_crossfade_sec,
            )
            audio_source_path = temp_audio_crossfade_cycle_path
        if audio_seam_fade_sec > 0:
            fd5, audio_seam_tmp_name = tempfile.mkstemp(
                suffix=".m4a", prefix="clip_loop_"
            )
            os.close(fd5)
            temp_audio_seam_fade_cycle_path = Path(audio_seam_tmp_name)
            build_seam_faded_audio_cycle(
                audio_source_path,
                temp_audio_seam_fade_cycle_path,
                fade_sec=audio_seam_fade_sec,
            )
            audio_source_path = temp_audio_seam_fade_cycle_path
        apply_external_audio(temp_video_path, output_path, audio_source_path, duration_sec)
    except (subprocess.CalledProcessError, ValueError):
        sys.stderr.write(
            "ffmpeg failed while applying external audio. "
            "Check that the audio file is a supported format.\n"
        )
        sys.exit(1)
    finally:
        temp_video_path.unlink(missing_ok=True)
        if temp_audio_cycle_path is not None:
            temp_audio_cycle_path.unlink(missing_ok=True)
        if temp_audio_gap_cycle_path is not None:
            temp_audio_gap_cycle_path.unlink(missing_ok=True)
        if temp_audio_crossfade_cycle_path is not None:
            temp_audio_crossfade_cycle_path.unlink(missing_ok=True)
        if temp_audio_seam_fade_cycle_path is not None:
            temp_audio_seam_fade_cycle_path.unlink(missing_ok=True)


def run_alternate_reverse_loop(
    input_path: Path,
    output_path: Path,
    duration_sec: float,
    *,
    trim_start_sec: float = 0.0,
    external_audio_path: Path | None = None,
    audio_alternate_reverse: bool = False,
    audio_crossfade_sec: float = 0.0,
    audio_gap_sec: float = 0.0,
    audio_seam_fade_sec: float = 0.0,
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
        if external_audio_path is None:
            try:
                run_stream_loop_copy(cycle_path, output_path, duration_sec)
            except subprocess.CalledProcessError:
                sys.stderr.write(
                    "ffmpeg failed while looping the cycle to the target duration.\n"
                )
                sys.exit(1)
        else:
            fd2, tmp_name2 = tempfile.mkstemp(
                suffix=output_path.suffix or ".mp4", prefix="clip_loop_"
            )
            os.close(fd2)
            temp_video_path = Path(tmp_name2)
            temp_audio_cycle_path: Path | None = None
            temp_audio_gap_cycle_path: Path | None = None
            temp_audio_crossfade_cycle_path: Path | None = None
            temp_audio_seam_fade_cycle_path: Path | None = None
            try:
                run_stream_loop_copy(cycle_path, temp_video_path, duration_sec)
                audio_source_path = external_audio_path
                if audio_alternate_reverse:
                    fd3, audio_tmp_name = tempfile.mkstemp(
                        suffix=".m4a", prefix="clip_loop_"
                    )
                    os.close(fd3)
                    temp_audio_cycle_path = Path(audio_tmp_name)
                    build_forward_reverse_audio_cycle(
                        external_audio_path, temp_audio_cycle_path
                    )
                    audio_source_path = temp_audio_cycle_path
                if audio_gap_sec > 0:
                    fd5, audio_gap_tmp_name = tempfile.mkstemp(
                        suffix=".m4a", prefix="clip_loop_"
                    )
                    os.close(fd5)
                    temp_audio_gap_cycle_path = Path(audio_gap_tmp_name)
                    build_gapped_audio_cycle(
                        audio_source_path,
                        temp_audio_gap_cycle_path,
                        gap_sec=audio_gap_sec,
                    )
                    audio_source_path = temp_audio_gap_cycle_path
                if audio_crossfade_sec > 0:
                    fd4, audio_xf_tmp_name = tempfile.mkstemp(
                        suffix=".m4a", prefix="clip_loop_"
                    )
                    os.close(fd4)
                    temp_audio_crossfade_cycle_path = Path(audio_xf_tmp_name)
                    build_crossfaded_audio_cycle(
                        audio_source_path,
                        temp_audio_crossfade_cycle_path,
                        crossfade_sec=audio_crossfade_sec,
                    )
                    audio_source_path = temp_audio_crossfade_cycle_path
                if audio_seam_fade_sec > 0:
                    fd6, audio_seam_tmp_name = tempfile.mkstemp(
                        suffix=".m4a", prefix="clip_loop_"
                    )
                    os.close(fd6)
                    temp_audio_seam_fade_cycle_path = Path(audio_seam_tmp_name)
                    build_seam_faded_audio_cycle(
                        audio_source_path,
                        temp_audio_seam_fade_cycle_path,
                        fade_sec=audio_seam_fade_sec,
                    )
                    audio_source_path = temp_audio_seam_fade_cycle_path
                apply_external_audio(
                    temp_video_path, output_path, audio_source_path, duration_sec
                )
            except (subprocess.CalledProcessError, ValueError):
                sys.stderr.write(
                    "ffmpeg failed while looping with external audio.\n"
                )
                sys.exit(1)
            finally:
                temp_video_path.unlink(missing_ok=True)
                if temp_audio_cycle_path is not None:
                    temp_audio_cycle_path.unlink(missing_ok=True)
                if temp_audio_gap_cycle_path is not None:
                    temp_audio_gap_cycle_path.unlink(missing_ok=True)
                if temp_audio_crossfade_cycle_path is not None:
                    temp_audio_crossfade_cycle_path.unlink(missing_ok=True)
                if temp_audio_seam_fade_cycle_path is not None:
                    temp_audio_seam_fade_cycle_path.unlink(missing_ok=True)
    finally:
        cycle_path.unlink(missing_ok=True)


def _add_loop_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "input",
        type=Path,
        nargs="?",
        help="Input video file (optional with --tui)",
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
    p.add_argument(
        "--speed",
        type=parse_speed_percent,
        default=100.0,
        metavar="PERCENT",
        help=(
            "Playback speed as a percentage of normal (default: 100). "
            "Examples: 80 for 80%%, 120 for 120%%. Re-encodes when not 100."
        ),
    )
    p.add_argument(
        "--audio",
        type=Path,
        metavar="PATH",
        help=(
            "Optional external audio file (e.g. mp3). "
            "Will loop/trim as needed to match the output duration."
        ),
    )
    p.add_argument(
        "--audio-alternate-reverse",
        action="store_true",
        help=(
            "With --audio, make one audio cycle as forward then reversed, "
            "then repeat. Independent of --alternate-reverse."
        ),
    )
    p.add_argument(
        "--audio-crossfade-ms",
        type=int,
        default=0,
        metavar="N",
        help=(
            "With --audio, crossfade each stitched audio seam by N milliseconds "
            "(default: 0 = disabled)."
        ),
    )
    p.add_argument(
        "--audio-gap-ms",
        type=int,
        default=0,
        metavar="N",
        help=(
            "With --audio, append N milliseconds of silence between stitched "
            "audio clips (default: 0 = disabled)."
        ),
    )
    p.add_argument(
        "--audio-seam-fade-ms",
        type=int,
        default=0,
        metavar="N",
        help=(
            "With --audio, fade volume down near the end and up at the start "
            "of each stitched clip by N milliseconds (default: 0 = disabled)."
        ),
    )
    p.add_argument(
        "--tui",
        action="store_true",
        help="Open an interactive terminal UI to configure options.",
    )
    p.add_argument(
        "--keep-ratio",
        type=parse_keep_ratio,
        metavar="RATIO",
        help=(
            "Before looping, crop away a corner and scale back to the original "
            "frame size. Requires --corner. Examples: 80%%, 50%%, 0.8"
        ),
    )
    p.add_argument(
        "--corner",
        type=parse_crop_corner,
        metavar="CORNER",
        help=(
            "With --keep-ratio, corner to remove. top_left keeps bottom-right; "
            "top_right keeps bottom-left; bottom_left keeps top-right; "
            "bottom_right keeps top-left."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="clip-loop",
        description="Loop a video clip until it reaches a target duration (default 1 hour).",
    )
    _add_loop_arguments(p)
    return p


def validate_clip_loop_options(
    *,
    input_path: Path,
    duration: float,
    trim_start_ms: int,
    audio_path: Path | None,
    audio_alternate_reverse: bool,
    audio_crossfade_ms: int,
    audio_gap_ms: int,
    audio_seam_fade_ms: int,
    keep_ratio: float | None = None,
    crop_corner: str | None = None,
    speed_percent: float = 100.0,
) -> None:
    if not input_path.is_file():
        raise ClipLoopError(f"Input not found: {input_path}")
    if duration <= 0:
        raise ClipLoopError("Duration must be positive.")
    if trim_start_ms < 0:
        raise ClipLoopError("--trim-start-ms must be non-negative.")
    if speed_percent <= 0:
        raise ClipLoopError("--speed must be positive.")
    if audio_path is not None and not audio_path.is_file():
        raise ClipLoopError(f"Audio input not found: {audio_path}")
    if audio_alternate_reverse and audio_path is None:
        raise ClipLoopError("--audio-alternate-reverse requires --audio PATH.")
    if audio_crossfade_ms < 0:
        raise ClipLoopError("--audio-crossfade-ms must be non-negative.")
    if audio_crossfade_ms > 0 and audio_path is None:
        raise ClipLoopError("--audio-crossfade-ms requires --audio PATH.")
    if audio_gap_ms < 0:
        raise ClipLoopError("--audio-gap-ms must be non-negative.")
    if audio_gap_ms > 0 and audio_path is None:
        raise ClipLoopError("--audio-gap-ms requires --audio PATH.")
    if audio_seam_fade_ms < 0:
        raise ClipLoopError("--audio-seam-fade-ms must be non-negative.")
    if audio_seam_fade_ms > 0 and audio_path is None:
        raise ClipLoopError("--audio-seam-fade-ms requires --audio PATH.")
    if (keep_ratio is None) != (crop_corner is None):
        raise ClipLoopError("--keep-ratio and --corner must be used together.")
    if keep_ratio is not None and crop_corner is not None:
        validate_crop_options(
            input_path=input_path,
            keep_ratio=keep_ratio,
            corner=crop_corner,
        )


def validate_crop_options(
    *,
    input_path: Path,
    keep_ratio: float,
    corner: str,
) -> None:
    if not input_path.is_file():
        raise ClipLoopError(f"Input not found: {input_path}")
    if corner not in CROP_CORNERS:
        choices = ", ".join(sorted(CROP_CORNERS))
        raise ClipLoopError(f"--corner must be one of: {choices}")
    try:
        width, height = ffprobe_video_size(input_path)
        compute_crop_rect(width, height, keep_ratio, corner)
    except (subprocess.CalledProcessError, ValueError) as exc:
        raise ClipLoopError(f"Invalid crop for {input_path}: {exc}") from exc


def run_crop_video(
    *,
    input_path: Path,
    keep_ratio: float,
    corner: str,
    output_path: Path | None = None,
) -> Path:
    """Crop away a corner, scale back to original size, and return the output path."""
    validate_crop_options(
        input_path=input_path,
        keep_ratio=keep_ratio,
        corner=corner,
    )
    ensure_ffmpeg()
    width, height = ffprobe_video_size(input_path)
    crop_w, crop_h, x, y = compute_crop_rect(width, height, keep_ratio, corner)
    resolved_output = output_path if output_path else default_crop_output_path(input_path)
    has_audio = ffprobe_has_audio(input_path)
    filt = f"crop={crop_w}:{crop_h}:{x}:{y},scale={width}:{height}"
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-vf",
        filt,
        "-map",
        "0:v:0",
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
    ]
    if has_audio:
        cmd.extend(["-map", "0:a:0", "-c:a", "copy"])
    else:
        cmd.append("-an")
    cmd.append(str(resolved_output))
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        sys.stderr.write(
            "ffmpeg failed while cropping video. "
            "Check that the file is a supported video format.\n"
        )
        sys.exit(1)
    return resolved_output


def build_atempo_chain(speed_factor: float) -> str:
    """Build an atempo filter chain; each stage must stay within 0.5–2.0."""
    filters: list[str] = []
    remaining = speed_factor
    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    filters.append(f"atempo={remaining:g}")
    return ",".join(filters)


def run_speed_adjust(
    input_path: Path,
    output_path: Path,
    speed_percent: float,
    *,
    trim_start_sec: float = 0.0,
) -> None:
    """Re-encode video (and embedded audio) at the given speed percentage."""
    speed_factor = speed_percent / 100.0
    setpts_factor = 1.0 / speed_factor
    has_audio = ffprobe_has_audio(input_path)
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
        atempo = build_atempo_chain(speed_factor)
        filt = (
            f"[0:v]setpts={setpts_factor:g}*PTS[vout];"
            f"[0:a]{atempo}[aout]"
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
            str(output_path),
        ]
    else:
        cmd = [
            *head,
            "-i",
            str(input_path),
            "-vf",
            f"setpts={setpts_factor:g}*PTS",
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
            str(output_path),
        ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        sys.stderr.write(
            "ffmpeg failed while adjusting playback speed. "
            "Check that the file is a supported video format.\n"
        )
        sys.exit(1)


def run_clip_loop(
    *,
    input_path: Path,
    duration: float,
    output_path: Path | None = None,
    alternate_reverse: bool = False,
    trim_start_ms: int = 0,
    audio_path: Path | None = None,
    audio_alternate_reverse: bool = False,
    audio_crossfade_ms: int = 0,
    audio_gap_ms: int = 0,
    audio_seam_fade_ms: int = 0,
    keep_ratio: float | None = None,
    crop_corner: str | None = None,
    speed_percent: float = 100.0,
) -> Path:
    """Validate options, run ffmpeg, and return the output path."""
    validate_clip_loop_options(
        input_path=input_path,
        duration=duration,
        trim_start_ms=trim_start_ms,
        audio_path=audio_path,
        audio_alternate_reverse=audio_alternate_reverse,
        audio_crossfade_ms=audio_crossfade_ms,
        audio_gap_ms=audio_gap_ms,
        audio_seam_fade_ms=audio_seam_fade_ms,
        keep_ratio=keep_ratio,
        crop_corner=crop_corner,
        speed_percent=speed_percent,
    )
    trim_start_sec = trim_start_ms / 1000.0
    audio_crossfade_sec = audio_crossfade_ms / 1000.0
    audio_gap_sec = audio_gap_ms / 1000.0
    audio_seam_fade_sec = audio_seam_fade_ms / 1000.0
    resolved_output = output_path if output_path else default_output_path(input_path)
    source_path = input_path
    temp_crop_path: Path | None = None
    temp_speed_path: Path | None = None
    loop_trim_start_sec = trim_start_sec
    try:
        if keep_ratio is not None and crop_corner is not None:
            fd, tmp_name = tempfile.mkstemp(
                suffix=input_path.suffix or ".mp4", prefix="clip_loop_crop_"
            )
            os.close(fd)
            temp_crop_path = Path(tmp_name)
            run_crop_video(
                input_path=input_path,
                keep_ratio=keep_ratio,
                corner=crop_corner,
                output_path=temp_crop_path,
            )
            source_path = temp_crop_path
        if speed_percent != 100.0:
            fd, tmp_name = tempfile.mkstemp(
                suffix=source_path.suffix or ".mp4", prefix="clip_loop_speed_"
            )
            os.close(fd)
            temp_speed_path = Path(tmp_name)
            run_speed_adjust(
                source_path,
                temp_speed_path,
                speed_percent,
                trim_start_sec=loop_trim_start_sec,
            )
            source_path = temp_speed_path
            loop_trim_start_sec = 0.0
        if alternate_reverse:
            run_alternate_reverse_loop(
                source_path,
                resolved_output,
                duration,
                trim_start_sec=loop_trim_start_sec,
                external_audio_path=audio_path,
                audio_alternate_reverse=audio_alternate_reverse,
                audio_crossfade_sec=audio_crossfade_sec,
                audio_gap_sec=audio_gap_sec,
                audio_seam_fade_sec=audio_seam_fade_sec,
            )
        else:
            loop_video_with_optional_audio(
                source_path,
                resolved_output,
                duration,
                trim_start_sec=loop_trim_start_sec,
                external_audio_path=audio_path,
                audio_alternate_reverse=audio_alternate_reverse,
                audio_crossfade_sec=audio_crossfade_sec,
                audio_gap_sec=audio_gap_sec,
                audio_seam_fade_sec=audio_seam_fade_sec,
            )
    finally:
        if temp_speed_path is not None:
            temp_speed_path.unlink(missing_ok=True)
        if temp_crop_path is not None:
            temp_crop_path.unlink(missing_ok=True)
    return resolved_output


def _namespace_to_kwargs(args: Any) -> dict[str, Any]:
    return {
        "input_path": args.input,
        "duration": args.duration,
        "output_path": args.output,
        "alternate_reverse": args.alternate_reverse,
        "trim_start_ms": args.trim_start_ms,
        "audio_path": args.audio,
        "audio_alternate_reverse": args.audio_alternate_reverse,
        "audio_crossfade_ms": args.audio_crossfade_ms,
        "audio_gap_ms": args.audio_gap_ms,
        "audio_seam_fade_ms": args.audio_seam_fade_ms,
        "keep_ratio": args.keep_ratio,
        "crop_corner": args.corner,
        "speed_percent": args.speed,
    }


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.tui:
        try:
            from clip_loop.tui import run_tui
        except ImportError as exc:
            sys.stderr.write(
                "clip-loop TUI requires the optional 'tui' dependency. "
                "Install with: uv sync --extra tui\n"
            )
            raise SystemExit(1) from exc
        run_tui(
            initial_input=args.input,
            initial_output=args.output,
            initial_audio=args.audio,
        )
        return
    if args.input is None:
        parser.error("the following arguments are required: input (or use --tui)")
    started = time.perf_counter()
    try:
        output_path = run_clip_loop(**_namespace_to_kwargs(args))
    except ClipLoopError as exc:
        sys.stderr.write(f"{exc}\n")
        sys.exit(1)
    elapsed = time.perf_counter() - started
    print(
        f"Wrote {output_path} ({args.duration:g}s) in {format_elapsed(elapsed)}"
    )

