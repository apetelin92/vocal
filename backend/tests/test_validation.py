import json
from pathlib import Path

import pytest

from app.core.config import Settings
from app.services.command_runner import CommandRunner
from app.services.validation import ValidationError, ValidationService


class StubRunner(CommandRunner):
    def __init__(self, duration: float):
        self.duration = duration

    def run(self, command, cwd=None, timeout=None):
        duration = self.duration

        class Result:
            stdout = json.dumps({"format": {"duration": duration}})

        return Result()


def test_validation_accepts_supported_short_file(tmp_path: Path):
    settings = Settings(storage_root=tmp_path)
    service = ValidationService(settings, StubRunner(duration=120))
    duration = service.validate_upload(tmp_path / "song.mp3", "mp3", 1024)
    assert duration == 120


def test_validation_rejects_long_file(tmp_path: Path):
    settings = Settings(storage_root=tmp_path)
    service = ValidationService(settings, StubRunner(duration=601))
    with pytest.raises(ValidationError, match="Maximum supported duration is 10 minutes"):
        service.validate_upload(tmp_path / "song.wav", "wav", 1024)


def test_validation_rejects_bad_extension(tmp_path: Path):
    settings = Settings(storage_root=tmp_path)
    service = ValidationService(settings, StubRunner(duration=10))
    with pytest.raises(ValidationError, match="Unsupported file format"):
        service.validate_upload(tmp_path / "song.flac", "flac", 1024)


def test_settings_defaults_favor_vocal_like_cleanup_and_forward_mix(tmp_path: Path):
    settings = Settings(storage_root=tmp_path)
    assert settings.midi_min_note_ms == 45
    assert settings.midi_merge_gap_ms == 20
    assert settings.midi_quantize_ms == 5
    assert settings.midi_octave_snap_enabled is True
    assert settings.midi_octave_snap_jump_semitones == 8
    assert settings.midi_target_pitch_min == 48
    assert settings.midi_target_pitch_max == 76
    assert settings.preview_mix_accompaniment_gain == 0.72
    assert settings.preview_mix_keys_gain == 1.35
