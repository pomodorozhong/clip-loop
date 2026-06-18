"""External-audio cycle builders."""

from __future__ import annotations

from pathlib import Path

from clip_loop.ffmpeg.executor import FfmpegExecutor
from clip_loop.ffmpeg.probe import MediaProbe


class AudioCycleBuilder:
    """Build single-cycle audio files for seamless looping."""

    def __init__(self, executor: FfmpegExecutor, probe: MediaProbe) -> None:
        self._executor = executor
        self._probe = probe

    def build_forward_reverse_cycle(self, audio_path: Path, cycle_path: Path) -> None:
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
        self._executor.run(
            cmd,
            error_message=(
                "ffmpeg failed while building forward/reverse audio cycle. "
                "Check that the audio file is a supported format."
            ),
        )

    def build_crossfaded_cycle(
        self, audio_path: Path, cycle_path: Path, *, crossfade_sec: float
    ) -> None:
        """Create one cycle with a crossfaded loop seam."""
        duration_sec = self._probe.audio_duration_sec(audio_path)
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
        self._executor.run(
            cmd,
            error_message=(
                "ffmpeg failed while building crossfaded audio cycle. "
                "Check that the audio file is a supported format."
            ),
        )

    def build_gapped_cycle(
        self, audio_path: Path, cycle_path: Path, *, gap_sec: float
    ) -> None:
        """Create one cycle by appending silence to the end."""
        duration_sec = self._probe.audio_duration_sec(audio_path)
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
        self._executor.run(
            cmd,
            error_message=(
                "ffmpeg failed while building gapped audio cycle. "
                "Check that the audio file is a supported format."
            ),
        )

    def build_seam_faded_cycle(
        self, audio_path: Path, cycle_path: Path, *, fade_sec: float
    ) -> None:
        """Create one cycle with fade-in/out at both seam edges."""
        duration_sec = self._probe.audio_duration_sec(audio_path)
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
        self._executor.run(
            cmd,
            error_message=(
                "ffmpeg failed while building seam-faded audio cycle. "
                "Check that the audio file is a supported format."
            ),
        )

    def apply_external_audio(
        self,
        video_path: Path,
        output_path: Path,
        audio_path: Path,
        duration_sec: float,
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
        self._executor.run(
            cmd,
            error_message=(
                "ffmpeg failed while applying external audio. "
                "Check that the audio file is a supported format."
            ),
        )
