from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.services.command_runner import CommandExecutionError, CommandRunner


class PreviewMixService:
    def __init__(self, settings: Settings, runner: CommandRunner):
        self.settings = settings
        self.runner = runner

    def render(self, accompaniment_path: Path, keys_path: Path, output_path: Path) -> Path:
        if not accompaniment_path.exists():
            raise RuntimeError(f"Accompaniment file not found for preview mix: {accompaniment_path}")
        if not keys_path.exists():
            raise RuntimeError(f"Keys file not found for preview mix: {keys_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.runner.run(
                [
                    self.settings.ffmpeg_bin,
                    "-y",
                    "-i",
                    str(accompaniment_path),
                    "-i",
                    str(keys_path),
                    "-filter_complex",
                    (
                        f"[0:a]aresample=async=1:first_pts=0,volume={self.settings.preview_mix_accompaniment_gain}[a0];"
                        f"[1:a]aresample=async=1:first_pts=0,volume={self.settings.preview_mix_keys_gain}[a1];"
                        "[a0][a1]amix=inputs=2:duration=longest:normalize=0,"
                        "alimiter=limit=0.95:level=disabled[mix]"
                    ),
                    "-map",
                    "[mix]",
                    "-c:a",
                    "pcm_s16le",
                    str(output_path),
                ]
            )
        except CommandExecutionError as exc:
            raise RuntimeError(f"Preview mix render failed: {exc}") from exc
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("FFmpeg finished without creating preview_mix.wav.")
        return output_path
