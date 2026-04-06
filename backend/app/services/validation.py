from __future__ import annotations

import json
from pathlib import Path

from app.core.config import Settings
from app.services.command_runner import CommandExecutionError, CommandRunner


class ValidationError(Exception):
    pass


class ValidationService:
    allowed_extensions = {"mp3", "wav", "m4a"}

    def __init__(self, settings: Settings, runner: CommandRunner):
        self.settings = settings
        self.runner = runner

    def validate_upload(self, input_path: Path, extension: str, file_size_bytes: int) -> float:
        if extension not in self.allowed_extensions:
            raise ValidationError("Unsupported file format. Use mp3, wav, or m4a.")
        if file_size_bytes > self.settings.max_upload_size_bytes:
            raise ValidationError("File is too large for the MVP upload limit.")

        try:
            result = self.runner.run(
                [
                    self.settings.ffprobe_bin,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "json",
                    str(input_path),
                ]
            )
        except CommandExecutionError as exc:
            raise ValidationError(f"Unable to inspect audio file: {exc}") from exc

        payload = json.loads(result.stdout or "{}")
        duration = float(payload.get("format", {}).get("duration") or 0)
        if duration <= 0:
            raise ValidationError("Could not determine audio duration.")
        if duration > self.settings.max_duration_seconds:
            raise ValidationError("File is too long. Maximum supported duration is 10 minutes.")
        return duration
