from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.services.command_runner import CommandExecutionError, CommandRunner


class AudioPreprocessService:
    def __init__(self, settings: Settings, runner: CommandRunner):
        self.settings = settings
        self.runner = runner

    def normalize_to_wav(self, input_path: Path, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.runner.run(
                [
                    self.settings.ffmpeg_bin,
                    "-y",
                    "-i",
                    str(input_path),
                    "-vn",
                    "-ac",
                    "2",
                    "-ar",
                    str(self.settings.normalized_sample_rate),
                    "-c:a",
                    "pcm_s16le",
                    "-af",
                    "loudnorm=I=-16:TP=-1.5:LRA=11",
                    str(output_path),
                ]
            )
        except CommandExecutionError as exc:
            raise RuntimeError(f"Audio preprocessing failed: {exc}") from exc
        return output_path
