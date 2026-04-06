from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.models.job import JobResponse, JobStatus, RenderPresetResponse
from app.repositories.job_store import JobNotFoundError
from app.services.render_presets import DEFAULT_RENDER_PRESET_ID, get_render_preset_spec

router = APIRouter(tags=["jobs"])


def _container(request: Request):
    return request.app.state.container


@router.get("/render-presets", response_model=list[RenderPresetResponse])
async def get_render_presets() -> list[RenderPresetResponse]:
    return RenderPresetResponse.all()


@router.post("/jobs/upload", response_model=JobResponse)
async def upload_job(
    request: Request,
    file: UploadFile = File(...),
    render_preset: str = Form(default=DEFAULT_RENDER_PRESET_ID),
) -> JobResponse:
    container = _container(request)
    body = await file.read()
    await file.seek(0)
    try:
        get_render_preset_spec(render_preset)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail="Unknown render_preset") from exc
    job = await container.store.create_from_upload(
        file,
        file_size_bytes=len(body),
        render_preset=render_preset,
    )
    return JobResponse.from_record(job)


@router.post("/jobs/{job_id}/start", response_model=JobResponse)
async def start_job(job_id: str, request: Request) -> JobResponse:
    container = _container(request)
    try:
        job = container.store.get(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    if job.status != JobStatus.UPLOADED:
        raise HTTPException(status_code=409, detail=f"Job cannot be started from status {job.status}")

    container.queue.enqueue(job_id)
    return JobResponse.from_record(job)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, request: Request) -> JobResponse:
    container = _container(request)
    try:
        return JobResponse.from_record(container.store.get(job_id))
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc


@router.get("/jobs/{job_id}/files")
async def get_job_files(job_id: str, request: Request):
    container = _container(request)
    try:
        job = container.store.get(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    return {"job_id": job.id, "status": job.status, "files": container.file_export_service.build_listing(job)}


@router.get("/download/{job_id}/{filename}")
async def download_output(job_id: str, filename: str, request: Request):
    container = _container(request)
    try:
        job = container.store.get(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    relative = job.paths.outputs.get(filename)
    if not relative:
        raise HTTPException(status_code=404, detail="Output file not registered for this job")

    path = Path(container.settings.storage_root) / relative
    if not path.exists():
        raise HTTPException(status_code=404, detail="Output file is missing")
    return FileResponse(path, filename=filename)
