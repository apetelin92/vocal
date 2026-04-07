from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.services.render_presets import DEFAULT_RENDER_PRESET_ID, RENDER_PRESETS


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus(StrEnum):
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    PREPROCESSING = "preprocessing"
    SEPARATING = "separating"
    TRANSCRIBING = "transcribing"
    CLEANING_MIDI = "cleaning_midi"
    RENDERING_KEYS = "rendering_keys"
    MIXING_PREVIEW = "mixing_preview"
    COMPLETED = "completed"
    FAILED = "failed"


TERMINAL_STATUSES = {JobStatus.COMPLETED, JobStatus.FAILED}


class JobEvent(BaseModel):
    status: JobStatus
    timestamp: datetime = Field(default_factory=utc_now)
    message: str | None = None


class JobPaths(BaseModel):
    input_relative: str
    normalized_relative: str | None = None
    outputs: dict[str, str] = Field(default_factory=dict)

    def resolve(self, storage_root: Path) -> dict[str, Path]:
        resolved = {"input": storage_root / self.input_relative}
        if self.normalized_relative:
            resolved["normalized"] = storage_root / self.normalized_relative
        for name, relative in self.outputs.items():
            resolved[name] = storage_root / relative
        return resolved


class JobRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    status: JobStatus = JobStatus.UPLOADED
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    original_filename: str
    input_extension: str
    content_type: str
    file_size_bytes: int
    duration_seconds: float | None = None
    error_message: str | None = None
    failure_reason: str | None = None
    transcription_engine: str | None = None
    render_preset: str = DEFAULT_RENDER_PRESET_ID
    events: list[JobEvent] = Field(default_factory=lambda: [JobEvent(status=JobStatus.UPLOADED, message="Upload received")])
    paths: JobPaths


class RenderPresetResponse(BaseModel):
    id: str
    label: str
    description: str

    @classmethod
    def all(cls) -> list["RenderPresetResponse"]:
        return [cls(id=preset.id, label=preset.label, description=preset.description) for preset in RENDER_PRESETS]


class DownloadFile(BaseModel):
    filename: str
    kind: Literal["audio", "midi"]
    content_type: str
    download_url: str
    preview_url: str | None = None
    exists: bool


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    original_filename: str
    duration_seconds: float | None
    transcription_engine: str | None
    render_preset: str
    error_message: str | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    events: list[JobEvent]

    @classmethod
    def from_record(cls, record: JobRecord) -> "JobResponse":
        return cls(
            job_id=record.id,
            status=record.status,
            original_filename=record.original_filename,
            duration_seconds=record.duration_seconds,
            transcription_engine=record.transcription_engine,
            render_preset=record.render_preset,
            error_message=record.error_message,
            failure_reason=record.failure_reason,
            created_at=record.created_at,
            updated_at=record.updated_at,
            started_at=record.started_at,
            completed_at=record.completed_at,
            events=record.events,
        )
