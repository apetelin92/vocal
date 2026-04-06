from pathlib import Path

import pytest

from app.models.job import JobPaths, JobRecord, JobStatus
from app.repositories.job_store import JobStore
from app.services.state_manager import InvalidStateTransitionError, JobStateManager


def make_job(store: JobStore) -> JobRecord:
    job = JobRecord(
        original_filename="track.mp3",
        input_extension="mp3",
        content_type="audio/mpeg",
        file_size_bytes=100,
        paths=JobPaths(input_relative="jobs/job-1/input/source.mp3"),
    )
    store.save(job)
    return job


def test_state_transitions_follow_pipeline(tmp_path: Path):
    store = JobStore(tmp_path)
    manager = JobStateManager(store)
    job = make_job(store)

    job = manager.transition(job, JobStatus.VALIDATING)
    job = manager.transition(job, JobStatus.PREPROCESSING)
    job = manager.transition(job, JobStatus.SEPARATING)

    assert job.status == JobStatus.SEPARATING
    assert len(job.events) == 4


def test_invalid_transition_is_blocked(tmp_path: Path):
    store = JobStore(tmp_path)
    manager = JobStateManager(store)
    job = make_job(store)

    with pytest.raises(InvalidStateTransitionError):
        manager.transition(job, JobStatus.COMPLETED)
