from __future__ import annotations

import json
import threading
from pathlib import Path

from fastapi import UploadFile

from app.models.job import JobPaths, JobRecord, JobStatus, utc_now


class JobNotFoundError(Exception):
    pass


class JobStore:
    def __init__(self, storage_root: Path):
        self.storage_root = storage_root
        self.jobs_root = storage_root / "jobs"
        self.jobs_root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _job_dir(self, job_id: str) -> Path:
        return self.jobs_root / job_id

    def _job_file(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "job.json"

    def _ensure_job_dir(self, job_id: str) -> Path:
        job_dir = self._job_dir(job_id)
        (job_dir / "input").mkdir(parents=True, exist_ok=True)
        (job_dir / "work").mkdir(parents=True, exist_ok=True)
        (job_dir / "outputs").mkdir(parents=True, exist_ok=True)
        return job_dir

    async def create_from_upload(self, upload: UploadFile, file_size_bytes: int, render_preset: str) -> JobRecord:
        extension = Path(upload.filename or "upload.bin").suffix.lower().lstrip(".")
        job = JobRecord(
            original_filename=upload.filename or "upload.bin",
            input_extension=extension,
            content_type=upload.content_type or "application/octet-stream",
            file_size_bytes=file_size_bytes,
            render_preset=render_preset,
            paths=JobPaths(input_relative=""),
        )

        job_dir = self._ensure_job_dir(job.id)
        input_path = job_dir / "input" / f"source.{extension or 'bin'}"

        with input_path.open("wb") as target:
            await upload.seek(0)
            while chunk := await upload.read(1024 * 1024):
                target.write(chunk)

        job.paths.input_relative = str(input_path.relative_to(self.storage_root))
        self.save(job)
        return job

    def save(self, job: JobRecord) -> JobRecord:
        with self._lock:
            job.updated_at = utc_now()
            job_file = self._job_file(job.id)
            self._ensure_job_dir(job.id)
            job_file.write_text(job.model_dump_json(indent=2), encoding="utf-8")
            return job

    def get(self, job_id: str) -> JobRecord:
        job_file = self._job_file(job_id)
        if not job_file.exists():
            raise JobNotFoundError(job_id)
        return JobRecord.model_validate(json.loads(job_file.read_text(encoding="utf-8")))

    def list_output_files(self, job: JobRecord) -> list[Path]:
        return [self.storage_root / relative for relative in job.paths.outputs.values()]

    def mark_stale_jobs_failed(self) -> None:
        with self._lock:
            for job_file in self.jobs_root.glob("*/job.json"):
                job = JobRecord.model_validate(json.loads(job_file.read_text(encoding="utf-8")))
                if job.status in {JobStatus.UPLOADED, JobStatus.COMPLETED, JobStatus.FAILED}:
                    continue
                job.status = JobStatus.FAILED
                job.failure_reason = "Worker stopped before the job finished. Start a new job."
                job.error_message = "Server restarted during processing."
                job.completed_at = utc_now()
                job.events.append(
                    {
                        "status": JobStatus.FAILED,
                        "message": "Marked failed after restart",
                        "timestamp": utc_now(),
                    }
                )
                self.save(job)
