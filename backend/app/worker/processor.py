from __future__ import annotations

from pathlib import Path

from app.models.job import JobStatus
from app.repositories.job_store import JobNotFoundError, JobStore
from app.services.state_manager import JobStateManager


class JobProcessor:
    def __init__(
        self,
        store: JobStore,
        state_manager: JobStateManager,
        validation_service,
        preprocess_service,
        separation_service,
        transcription_service,
        midi_cleanup_service,
        synth_render_service,
        preview_mix_service,
        storage_root: Path,
    ):
        self.store = store
        self.state_manager = state_manager
        self.validation_service = validation_service
        self.preprocess_service = preprocess_service
        self.separation_service = separation_service
        self.transcription_service = transcription_service
        self.midi_cleanup_service = midi_cleanup_service
        self.synth_render_service = synth_render_service
        self.preview_mix_service = preview_mix_service
        self.storage_root = storage_root

    def process(self, job_id: str) -> None:
        try:
            job = self.store.get(job_id)
        except JobNotFoundError:
            return

        if job.status != JobStatus.UPLOADED:
            return

        try:
            input_path = self.storage_root / job.paths.input_relative
            work_dir = self.storage_root / "jobs" / job.id / "work"
            outputs_dir = self.storage_root / "jobs" / job.id / "outputs"

            job = self.state_manager.transition(job, JobStatus.VALIDATING, "Inspecting file format and duration")
            duration = self.validation_service.validate_upload(
                input_path=input_path,
                extension=job.input_extension,
                file_size_bytes=job.file_size_bytes,
            )
            job.duration_seconds = duration
            job = self.store.save(job)

            job = self.state_manager.transition(job, JobStatus.PREPROCESSING, "Converting source into normalized WAV")
            normalized_path = work_dir / "normalized.wav"
            self.preprocess_service.normalize_to_wav(input_path, normalized_path)
            job.paths.normalized_relative = str(normalized_path.relative_to(self.storage_root))
            job = self.store.save(job)

            job = self.state_manager.transition(job, JobStatus.SEPARATING, "Separating vocals and accompaniment")
            vocals_path = outputs_dir / "vocals.wav"
            accompaniment_path = outputs_dir / "accompaniment.wav"
            self.separation_service.separate(normalized_path, work_dir / "demucs", vocals_path, accompaniment_path)
            job.paths.outputs["vocals.wav"] = str(vocals_path.relative_to(self.storage_root))
            job.paths.outputs["accompaniment.wav"] = str(accompaniment_path.relative_to(self.storage_root))
            job = self.store.save(job)

            job = self.state_manager.transition(job, JobStatus.TRANSCRIBING, "Extracting vocal melody to MIDI")
            raw_midi_path = work_dir / "melody_raw.mid"
            transcription = self.transcription_service.transcribe(vocals_path, raw_midi_path)
            job.transcription_engine = transcription.engine
            job = self.store.save(job)

            job = self.state_manager.transition(job, JobStatus.CLEANING_MIDI, "Cleaning MIDI notes")
            melody_path = outputs_dir / "melody.mid"
            self.midi_cleanup_service.cleanup(raw_midi_path, melody_path)
            job.paths.outputs["melody.mid"] = str(melody_path.relative_to(self.storage_root))
            job = self.store.save(job)

            job = self.state_manager.transition(job, JobStatus.RENDERING_KEYS, "Rendering piano track")
            keys_path = outputs_dir / "keys.wav"
            self.synth_render_service.render(melody_path, keys_path, job.render_preset)
            job.paths.outputs["keys.wav"] = str(keys_path.relative_to(self.storage_root))
            job = self.store.save(job)

            job = self.state_manager.transition(job, JobStatus.MIXING_PREVIEW, "Creating accompaniment + keys preview")
            preview_mix_path = outputs_dir / "preview_mix.wav"
            self.preview_mix_service.render(accompaniment_path, keys_path, preview_mix_path)
            job.paths.outputs["preview_mix.wav"] = str(preview_mix_path.relative_to(self.storage_root))
            job = self.store.save(job)

            self.state_manager.transition(job, JobStatus.COMPLETED, "Outputs are ready for download")
        except Exception as exc:
            self.state_manager.fail(
                job,
                reason="Processing failed. See error_message for details.",
                error_message=str(exc),
            )
