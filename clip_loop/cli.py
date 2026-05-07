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


def loop_video_with_optional_audio(
    input_path: Path,
    output_path: Path,
    duration_sec: float,
    *,
    trim_start_sec: float = 0.0,
    external_audio_path: Path | None = None,
    audio_alternate_reverse: bool = False,
    audio_crossfade_sec: float = 0.0,
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
    temp_audio_crossfade_cycle_path: Path | None = None
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
        if temp_audio_crossfade_cycle_path is not None:
            temp_audio_crossfade_cycle_path.unlink(missing_ok=True)


def run_alternate_reverse_loop(
    input_path: Path,
    output_path: Path,
    duration_sec: float,
    *,
    trim_start_sec: float = 0.0,
    external_audio_path: Path | None = None,
    audio_alternate_reverse: bool = False,
    audio_crossfade_sec: float = 0.0,
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
            temp_audio_crossfade_cycle_path: Path | None = None
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
                if temp_audio_crossfade_cycle_path is not None:
                    temp_audio_crossfade_cycle_path.unlink(missing_ok=True)
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
    external_audio_path: Path | None = args.audio
    if external_audio_path is not None and not external_audio_path.is_file():
        sys.stderr.write(f"Audio input not found: {external_audio_path}\n")
        sys.exit(1)
    if args.audio_alternate_reverse and external_audio_path is None:
        sys.stderr.write("--audio-alternate-reverse requires --audio PATH.\n")
        sys.exit(1)
    if args.audio_crossfade_ms < 0:
        sys.stderr.write("--audio-crossfade-ms must be non-negative.\n")
        sys.exit(1)
    if args.audio_crossfade_ms > 0 and external_audio_path is None:
        sys.stderr.write("--audio-crossfade-ms requires --audio PATH.\n")
        sys.exit(1)
    trim_start_sec = args.trim_start_ms / 1000.0
    audio_crossfade_sec = args.audio_crossfade_ms / 1000.0
    output_path = args.output if args.output else default_output_path(input_path)
    started = time.perf_counter()
    if args.alternate_reverse:
        run_alternate_reverse_loop(
            input_path,
            output_path,
            args.duration,
            trim_start_sec=trim_start_sec,
            external_audio_path=external_audio_path,
            audio_alternate_reverse=args.audio_alternate_reverse,
            audio_crossfade_sec=audio_crossfade_sec,
        )
    else:
        loop_video_with_optional_audio(
            input_path,
            output_path,
            args.duration,
            trim_start_sec=trim_start_sec,
            external_audio_path=external_audio_path,
            audio_alternate_reverse=args.audio_alternate_reverse,
            audio_crossfade_sec=audio_crossfade_sec,
        )
    elapsed = time.perf_counter() - started
    print(
        f"Wrote {output_path} ({args.duration:g}s) in {format_elapsed(elapsed)}"
    )

