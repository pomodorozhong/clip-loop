"""High-level loop strategies (simple and ping-pong)."""

from __future__ import annotations

from pathlib import Path

from clip_loop.ffmpeg.audio import AudioCycleBuilder
from clip_loop.ffmpeg.audio_pipeline import ExternalAudioPipeline, cleanup_temp_paths
from clip_loop.ffmpeg.temp import temp_media_file
from clip_loop.ffmpeg.video import VideoProcessor
from clip_loop.models import AudioEffectOptions


class LoopEngine:
    """Compose video looping with optional external-audio replacement."""

    def __init__(
        self,
        video: VideoProcessor,
        audio: AudioCycleBuilder,
    ) -> None:
        self._video = video
        self._audio = audio
        self._audio_pipeline = ExternalAudioPipeline(audio)

    def loop_simple(
        self,
        input_path: Path,
        output_path: Path,
        duration_sec: float,
        *,
        trim_start_sec: float = 0.0,
        external_audio_path: Path | None = None,
        audio_effects: AudioEffectOptions | None = None,
    ) -> None:
        if external_audio_path is None:
            self._video.simple_loop(
                input_path, output_path, duration_sec, trim_start_sec=trim_start_sec
            )
            return

        effects = audio_effects or AudioEffectOptions(False, 0.0, 0.0, 0.0)
        with temp_media_file(suffix=output_path.suffix or ".mp4") as temp_video_path:
            audio_temp_paths: list[Path] = []
            try:
                self._video.simple_loop(
                    input_path,
                    temp_video_path,
                    duration_sec,
                    trim_start_sec=trim_start_sec,
                )
                audio_source, audio_temp_paths = self._audio_pipeline.prepare_source(
                    external_audio_path, effects
                )
                self._audio.apply_external_audio(
                    temp_video_path, output_path, audio_source, duration_sec
                )
            except (RuntimeError, ValueError) as exc:
                raise RuntimeError(
                    "ffmpeg failed while applying external audio. "
                    "Check that the audio file is a supported format."
                ) from exc
            finally:
                cleanup_temp_paths(audio_temp_paths)

    def loop_alternate_reverse(
        self,
        input_path: Path,
        output_path: Path,
        duration_sec: float,
        *,
        trim_start_sec: float = 0.0,
        external_audio_path: Path | None = None,
        audio_effects: AudioEffectOptions | None = None,
    ) -> None:
        with temp_media_file(suffix=".mp4") as cycle_path:
            self._video.build_forward_reverse_cycle(
                input_path, cycle_path, trim_start_sec=trim_start_sec
            )
            if external_audio_path is None:
                self._video.stream_loop_copy(cycle_path, output_path, duration_sec)
                return

            effects = audio_effects or AudioEffectOptions(False, 0.0, 0.0, 0.0)
            with temp_media_file(suffix=output_path.suffix or ".mp4") as temp_video_path:
                audio_temp_paths: list[Path] = []
                try:
                    self._video.stream_loop_copy(
                        cycle_path, temp_video_path, duration_sec
                    )
                    audio_source, audio_temp_paths = self._audio_pipeline.prepare_source(
                        external_audio_path, effects
                    )
                    self._audio.apply_external_audio(
                        temp_video_path, output_path, audio_source, duration_sec
                    )
                except (RuntimeError, ValueError) as exc:
                    raise RuntimeError(
                        "ffmpeg failed while looping with external audio."
                    ) from exc
                finally:
                    cleanup_temp_paths(audio_temp_paths)
