from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import os
from pathlib import Path

from app.core.config import Settings
from app.services.command_runner import CommandExecutionError, CommandRunner


class TranscriptionError(Exception):
    pass


@dataclass
class TranscriptionResult:
    engine: str
    midi_path: Path
    note_count: int


class TranscriptionAdapter(ABC):
    name: str

    @abstractmethod
    def transcribe(self, input_path: Path, output_path: Path) -> TranscriptionResult:
        raise NotImplementedError


class MidiQualityEvaluator:
    def inspect(self, midi_path: Path) -> int:
        try:
            import pretty_midi
        except ImportError as exc:
            raise TranscriptionError(
                "pretty_midi is required to inspect transcription quality."
            ) from exc

        midi = pretty_midi.PrettyMIDI(str(midi_path))
        notes = [note for instrument in midi.instruments for note in instrument.notes]
        return len(notes)

    def is_usable(self, note_count: int) -> bool:
        return note_count >= 4


class SomeTranscriber(TranscriptionAdapter):
    name = "some"

    def __init__(self, settings: Settings, runner: CommandRunner, quality: MidiQualityEvaluator):
        self.settings = settings
        self.runner = runner
        self.quality = quality

    def transcribe(self, input_path: Path, output_path: Path) -> TranscriptionResult:
        repo_path = self.settings.some_repo_path
        model_path = self.settings.some_model_path
        python_bin = self.settings.some_python_bin
        if not self.settings.some_enabled:
            raise TranscriptionError("SOME is disabled.")
        if repo_path is None:
            raise TranscriptionError("SOME_REPO_PATH is not configured.")
        if model_path is None:
            raise TranscriptionError("SOME_MODEL_PATH is not configured.")
        repo_path = repo_path.expanduser().resolve()
        model_path = model_path.expanduser().resolve()
        input_path = input_path.expanduser().resolve()
        output_path = output_path.expanduser().resolve()
        python_bin = os.path.abspath(os.path.expanduser(python_bin))
        infer_path = repo_path / "infer.py"
        config_path = model_path.with_name("config.yaml")
        if not repo_path.exists():
            raise TranscriptionError(f"SOME repo path does not exist: {repo_path}")
        if not infer_path.exists():
            raise TranscriptionError(f"SOME infer.py was not found at: {infer_path}")
        if not model_path.exists():
            raise TranscriptionError(f"SOME checkpoint does not exist: {model_path}")
        if not config_path.exists():
            raise TranscriptionError(
                "SOME requires config.yaml next to the checkpoint file."
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            output_path.unlink()
        command = [
            python_bin,
            str(infer_path),
            "--model",
            str(model_path),
            "--wav",
            str(input_path),
            "--midi",
            str(output_path),
        ]
        try:
            self.runner.run(command, cwd=repo_path)
        except CommandExecutionError as exc:
            raise TranscriptionError(f"SOME transcription failed: {exc}") from exc

        if not output_path.exists():
            raise TranscriptionError("SOME completed without producing a MIDI file.")

        note_count = self.quality.inspect(output_path)
        if not self.quality.is_usable(note_count):
            raise TranscriptionError("SOME output quality was too low, falling back.")
        return TranscriptionResult(engine=self.name, midi_path=output_path, note_count=note_count)


class BasicPitchTranscriptionAdapter(TranscriptionAdapter):
    name = "basic_pitch"

    def __init__(self, quality: MidiQualityEvaluator):
        self.quality = quality

    def transcribe(self, input_path: Path, output_path: Path) -> TranscriptionResult:
        try:
            from basic_pitch.inference import predict
        except ImportError as exc:
            raise TranscriptionError(
                "Basic Pitch is not installed. Install backend ML dependencies."
            ) from exc

        output_path.parent.mkdir(parents=True, exist_ok=True)
        _, midi_data, note_events = predict(str(input_path))
        if not note_events:
            raise TranscriptionError("Basic Pitch produced no note events.")
        midi_data.write(str(output_path))
        note_count = self.quality.inspect(output_path)
        if not self.quality.is_usable(note_count):
            raise TranscriptionError("Basic Pitch output quality was too low.")
        return TranscriptionResult(engine=self.name, midi_path=output_path, note_count=note_count)


class TranscriptionService:
    def __init__(self, settings: Settings, adapters: list[TranscriptionAdapter]):
        self.settings = settings
        self.adapters = adapters

    def transcribe(self, input_path: Path, output_path: Path) -> TranscriptionResult:
        errors: list[str] = []
        for adapter in self.adapters:
            if adapter.name == "some" and not self.settings.some_enabled:
                continue
            if adapter.name == "basic_pitch" and not self.settings.basic_pitch_enabled:
                continue
            try:
                if output_path.exists():
                    output_path.unlink()
                return adapter.transcribe(input_path, output_path)
            except TranscriptionError as exc:
                if output_path.exists():
                    output_path.unlink()
                errors.append(str(exc))

        joined = " | ".join(errors) if errors else "No transcription adapters configured."
        raise RuntimeError(f"All transcription adapters failed. {joined}")
