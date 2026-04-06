from pathlib import Path

from app.core.config import Settings
from app.services.transcription import SomeTranscriber


class StubRunner:
    def __init__(self):
        self.command = None
        self.cwd = None

    def run(self, command, cwd=None, timeout=None):
        self.command = command
        self.cwd = cwd
        output_path = Path(command[-1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"MThd")


class StubQuality:
    def inspect(self, midi_path: Path) -> int:
        return 8

    def is_usable(self, note_count: int) -> bool:
        return True


def test_some_transcriber_resolves_paths_before_invoking_infer(tmp_path: Path):
    repo_path = tmp_path / "external" / "SOME"
    repo_path.mkdir(parents=True)
    (repo_path / "infer.py").write_text("print('stub')\n")

    model_dir = tmp_path / "models" / "some"
    model_dir.mkdir(parents=True)
    model_path = model_dir / "model.ckpt"
    model_path.write_text("checkpoint")
    (model_dir / "config.yaml").write_text("task_cls: stub\n")

    input_path = tmp_path / "storage" / "jobs" / "job-1" / "outputs" / "vocals.wav"
    input_path.parent.mkdir(parents=True)
    input_path.write_bytes(b"wav")

    runner = StubRunner()
    transcriber = SomeTranscriber(
        Settings(
            some_enabled=True,
            some_repo_path=repo_path,
            some_model_path=model_path,
            some_python_bin="/usr/bin/python3",
        ),
        runner,
        StubQuality(),
    )

    relative_input = input_path.relative_to(tmp_path)
    relative_output = Path("storage/jobs/job-1/work/melody_raw.mid")

    cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        result = transcriber.transcribe(relative_input, relative_output)
    finally:
        os.chdir(cwd)

    assert result.engine == "some"
    assert result.note_count == 8
    assert result.midi_path == (tmp_path / relative_output).resolve()
    assert runner.cwd == repo_path.resolve()
    assert runner.command[0] == "/usr/bin/python3"
    assert Path(runner.command[1]).is_absolute()
    assert Path(runner.command[3]).is_absolute()
    assert Path(runner.command[5]).is_absolute()
    assert Path(runner.command[7]).is_absolute()
