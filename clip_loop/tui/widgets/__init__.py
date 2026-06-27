"""Reusable TUI widget components."""

from clip_loop.tui.widgets.audio_input_section import AudioInputSection
from clip_loop.tui.widgets.audio_options_fields import AudioOptionsFields
from clip_loop.tui.widgets.audio_segment_row import AudioSegmentRow
from clip_loop.tui.widgets.collapsible_segment_row import CollapsibleSegmentRow
from clip_loop.tui.widgets.crop_fields import CropFields
from clip_loop.tui.widgets.duration_fields import DurationFields
from clip_loop.tui.widgets.field_label import FieldLabel
from clip_loop.tui.widgets.field_row import FieldRow
from clip_loop.tui.widgets.file_pick_screen import FilePickScreen
from clip_loop.tui.widgets.form_group_box import FormGroupBody, FormGroupBox, FormGroupTitle
from clip_loop.tui.widgets.ms_preset_field import MsPresetField
from clip_loop.tui.widgets.multiple_audio_input_panel import MultipleAudioInputPanel
from clip_loop.tui.widgets.multiple_video_input_panel import MultipleVideoInputPanel
from clip_loop.tui.widgets.output_path_fields import OutputPathFields
from clip_loop.tui.widgets.path_browse_row import PathBrowseRow
from clip_loop.tui.widgets.preset_input import PresetInput
from clip_loop.tui.widgets.preset_select_field import PresetSelectField
from clip_loop.tui.widgets.resolution_fields import ResolutionFields
from clip_loop.tui.widgets.run_progress_panel import RunProgressPanel
from clip_loop.tui.widgets.segment_add_row import SegmentAddRow
from clip_loop.tui.widgets.single_audio_input_fields import SingleAudioInputFields
from clip_loop.tui.widgets.single_video_input_fields import SingleVideoInputFields
from clip_loop.tui.widgets.speed_fields import SpeedFields
from clip_loop.tui.widgets.video_input_section import VideoInputSection
from clip_loop.tui.widgets.video_segment_row import VideoSegmentRow

__all__ = [
    "AudioInputSection",
    "AudioOptionsFields",
    "AudioSegmentRow",
    "CollapsibleSegmentRow",
    "CropFields",
    "DurationFields",
    "FieldLabel",
    "FieldRow",
    "FilePickScreen",
    "FormGroupBody",
    "FormGroupBox",
    "FormGroupTitle",
    "MsPresetField",
    "MultipleAudioInputPanel",
    "MultipleVideoInputPanel",
    "OutputPathFields",
    "PathBrowseRow",
    "PresetInput",
    "PresetSelectField",
    "ResolutionFields",
    "RunProgressPanel",
    "SegmentAddRow",
    "SingleAudioInputFields",
    "SingleVideoInputFields",
    "SpeedFields",
    "VideoInputSection",
    "VideoSegmentRow",
]
