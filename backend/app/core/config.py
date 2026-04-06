from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Vocal2Keys + Minus API"
    app_env: str = "development"
    api_prefix: str = "/api"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ]
    )

    storage_root: Path = Path(__file__).resolve().parents[3] / "storage"
    max_duration_seconds: int = 600
    max_upload_size_bytes: int = 80 * 1024 * 1024
    worker_poll_interval_ms: int = 300
    job_timeout_seconds: int = 1800

    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    demucs_command: str = "demucs"
    demucs_model: str = "htdemucs"
    some_enabled: bool = False
    some_repo_path: Path | None = None
    some_model_path: Path | None = None
    some_python_bin: str = "python"
    basic_pitch_enabled: bool = True
    soundfont_path: Path | None = None
    fluidsynth_bin: str = "fluidsynth"

    normalized_sample_rate: int = 44100
    midi_min_note_ms: int = 45
    midi_merge_gap_ms: int = 20
    midi_quantize_ms: int = 5
    midi_octave_snap_enabled: bool = True
    midi_octave_snap_jump_semitones: int = 8
    midi_target_pitch_min: int = 48
    midi_target_pitch_max: int = 76
    preview_mix_accompaniment_gain: float = 0.72
    preview_mix_keys_gain: float = 1.35

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
