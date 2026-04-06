from __future__ import annotations

from app.models.job import JobEvent, JobRecord, JobStatus, utc_now
from app.repositories.job_store import JobStore


class InvalidStateTransitionError(Exception):
    pass


class JobStateManager:
    _allowed: dict[JobStatus, set[JobStatus]] = {
        JobStatus.UPLOADED: {JobStatus.VALIDATING, JobStatus.FAILED},
        JobStatus.VALIDATING: {JobStatus.PREPROCESSING, JobStatus.FAILED},
        JobStatus.PREPROCESSING: {JobStatus.SEPARATING, JobStatus.FAILED},
        JobStatus.SEPARATING: {JobStatus.TRANSCRIBING, JobStatus.FAILED},
        JobStatus.TRANSCRIBING: {JobStatus.CLEANING_MIDI, JobStatus.FAILED},
        JobStatus.CLEANING_MIDI: {JobStatus.RENDERING_KEYS, JobStatus.FAILED},
        JobStatus.RENDERING_KEYS: {JobStatus.MIXING_PREVIEW, JobStatus.FAILED},
        JobStatus.MIXING_PREVIEW: {JobStatus.COMPLETED, JobStatus.FAILED},
        JobStatus.COMPLETED: set(),
        JobStatus.FAILED: set(),
    }

    def __init__(self, store: JobStore):
        self.store = store

    def transition(self, job: JobRecord, status: JobStatus, message: str | None = None) -> JobRecord:
        allowed = self._allowed[job.status]
        if status not in allowed:
            raise InvalidStateTransitionError(f"{job.status} -> {status} is not allowed")

        if job.started_at is None and status != JobStatus.FAILED:
            job.started_at = utc_now()

        job.status = status
        if status in {JobStatus.COMPLETED, JobStatus.FAILED}:
            job.completed_at = utc_now()
        job.events.append(JobEvent(status=status, message=message))
        return self.store.save(job)

    def fail(self, job: JobRecord, reason: str, error_message: str | None = None) -> JobRecord:
        if job.status != JobStatus.FAILED:
            job = self.transition(job, JobStatus.FAILED, message=reason)
        job.failure_reason = reason
        job.error_message = error_message or reason
        return self.store.save(job)
