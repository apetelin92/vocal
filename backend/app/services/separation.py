from __future__ import annotations

import shutil
from pathlib import Path

from app.core.config import Settings
from app.services.command_runner import CommandExecutionError, CommandRunner


class SeparationService:
    def __init__(self, settings: Settings, runner: CommandRunner):
        self.settings = settings
        self.runner = runner

    def separate(self, input_path: Path, work_dir: Path, vocals_output: Path, accompaniment_output: Path) -> tuple[Path, Path]:
        work_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.runner.run(
                [
                    self.settings.demucs_command,
                    "--two-stems=vocals",
                    "-n",
                    self.settings.demucs_model,
                    "-o",
                    str(work_dir),
                    str(input_path),
                ]
            )
        except CommandExecutionError as exc:
            raise RuntimeError(f"Source separation failed: {exc}") from exc

        stem_root = work_dir / self.settings.demucs_model / input_path.stem
        generated_vocals = stem_root / "vocals.wav"
        generated_accompaniment = stem_root / "no_vocals.wav"
        if not generated_vocals.exists() or not generated_accompaniment.exists():
            raise RuntimeError("Demucs finished without producing both stem files.")

        vocals_output.parent.mkdir(parents=True, exist_ok=True)
        accompaniment_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(generated_vocals, vocals_output)
        shutil.copy2(generated_accompaniment, accompaniment_output)
        return vocals_output, accompaniment_output
