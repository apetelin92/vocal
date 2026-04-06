from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.jobs import router as jobs_router
from app.core.config import Settings, get_settings
from app.repositories.job_store import JobStore
from app.services.audio_preprocess import AudioPreprocessService
from app.services.command_runner import CommandRunner
from app.services.file_export import FileExportService
from app.services.midi_cleanup import MidiCleanupService
from app.services.preview_mix import PreviewMixService
from app.services.separation import SeparationService
from app.services.state_manager import JobStateManager
from app.services.synth_render import SynthRenderService
from app.services.transcription import (
    BasicPitchTranscriptionAdapter,
    MidiQualityEvaluator,
    SomeTranscriber,
    TranscriptionService,
)
from app.services.validation import ValidationService
from app.worker.processor import JobProcessor
from app.worker.queue import JobQueueWorker


@dataclass
class AppContainer:
    settings: Settings
    store: JobStore
    state_manager: JobStateManager
    queue: JobQueueWorker
    file_export_service: FileExportService


def build_container(settings: Settings) -> AppContainer:
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    runner = CommandRunner()
    store = JobStore(settings.storage_root)
    state_manager = JobStateManager(store)
    quality = MidiQualityEvaluator()

    transcription_service = TranscriptionService(
        settings=settings,
        adapters=[
            SomeTranscriber(settings, runner, quality),
            BasicPitchTranscriptionAdapter(quality),
        ],
    )

    processor = JobProcessor(
        store=store,
        state_manager=state_manager,
        validation_service=ValidationService(settings, runner),
        preprocess_service=AudioPreprocessService(settings, runner),
        separation_service=SeparationService(settings, runner),
        transcription_service=transcription_service,
        midi_cleanup_service=MidiCleanupService(settings),
        synth_render_service=SynthRenderService(settings, runner),
        preview_mix_service=PreviewMixService(settings, runner),
        storage_root=settings.storage_root,
    )
    queue = JobQueueWorker(processor, poll_interval_seconds=settings.worker_poll_interval_ms / 1000)
    return AppContainer(
        settings=settings,
        store=store,
        state_manager=state_manager,
        queue=queue,
        file_export_service=FileExportService(settings.storage_root),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    container = build_container(settings)
    container.store.mark_stale_jobs_failed()
    app.state.container = container
    container.queue.start()
    try:
        yield
    finally:
        container.queue.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(jobs_router, prefix=settings.api_prefix)

    @app.get("/health")
    async def healthcheck():
        return {"status": "ok"}

    return app


app = create_app()
