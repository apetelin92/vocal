from __future__ import annotations

from pathlib import Path

from app.models.job import DownloadFile, JobRecord


class FileExportService:
    _content_types = {
        "vocals.wav": ("audio", "audio/wav"),
        "accompaniment.wav": ("audio", "audio/wav"),
        "melody.mid": ("midi", "audio/midi"),
        "keys.wav": ("audio", "audio/wav"),
        "preview_mix.wav": ("audio", "audio/wav"),
    }

    def __init__(self, storage_root: Path, download_prefix: str = "/api/download"):
        self.storage_root = storage_root
        self.download_prefix = download_prefix.rstrip("/")

    def build_listing(self, job: JobRecord) -> list[DownloadFile]:
        files: list[DownloadFile] = []
        for filename in self._content_types:
            relative = job.paths.outputs.get(filename)
            path = self.storage_root / relative if relative else None
            kind, content_type = self._content_types[filename]
            download_url = f"{self.download_prefix}/{job.id}/{filename}"
            files.append(
                DownloadFile(
                    filename=filename,
                    kind=kind,
                    content_type=content_type,
                    download_url=download_url,
                    preview_url=download_url if kind == "audio" and path and path.exists() else None,
                    exists=bool(path and path.exists()),
                )
            )
        return files
