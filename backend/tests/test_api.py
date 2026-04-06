from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def test_upload_endpoint_returns_expected_shape(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/jobs/upload",
            data={"render_preset": "synth_lead"},
            files={"file": ("demo.mp3", BytesIO(b"fake-audio"), "audio/mpeg")},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["job_id"]
        assert payload["status"] == "uploaded"
        assert payload["original_filename"] == "demo.mp3"
        assert payload["render_preset"] == "synth_lead"
        assert isinstance(payload["events"], list)


def test_render_presets_endpoint_returns_options(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        response = client.get("/api/render-presets")

        assert response.status_code == 200
        payload = response.json()
        assert len(payload) >= 3
        assert payload[0]["id"] == "acoustic_lead"
