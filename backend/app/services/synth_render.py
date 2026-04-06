from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from app.core.config import Settings
from app.services.command_runner import CommandExecutionError, CommandRunner
from app.services.render_presets import get_render_preset_spec


class SynthRenderService:
    def __init__(self, settings: Settings, runner: CommandRunner):
        self.settings = settings
        self.runner = runner

    def _build_render_midi(self, midi_path: Path, output_path: Path, render_preset: str) -> Path:
        try:
            import pretty_midi
        except ImportError as exc:
            raise RuntimeError("pretty_midi is required to apply the selected keys sound.") from exc

        preset = get_render_preset_spec(render_preset)
        midi = pretty_midi.PrettyMIDI(str(midi_path))
        for instrument in midi.instruments:
            instrument.program = preset.program
            instrument.is_drum = False
            instrument.name = preset.label
            for note in instrument.notes:
                note.velocity = preset.velocity

        with NamedTemporaryFile(
            suffix=".mid",
            prefix=f"render-{render_preset}-",
            dir=output_path.parent,
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
        midi.write(str(temp_path))
        return temp_path

    def render(self, midi_path: Path, output_path: Path, render_preset: str) -> Path:
        if not self.settings.soundfont_path:
            raise RuntimeError("SOUNDFONT_PATH is required to render piano audio.")
        if not self.settings.soundfont_path.exists():
            raise RuntimeError(f"SoundFont file not found: {self.settings.soundfont_path}")
        if not midi_path.exists():
            raise RuntimeError(f"MIDI file not found for rendering: {midi_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        render_midi_path = self._build_render_midi(midi_path, output_path, render_preset)
        try:
            self.runner.run(
                [
                    self.settings.fluidsynth_bin,
                    "-n",
                    "-i",
                    "-q",
                    "-a",
                    "file",
                    "-z",
                    "2048",
                    "-F",
                    str(output_path),
                    "-T",
                    "wav",
                    "-r",
                    str(self.settings.normalized_sample_rate),
                    str(self.settings.soundfont_path),
                    str(render_midi_path),
                ]
            )
        except CommandExecutionError as exc:
            raise RuntimeError(f"FluidSynth render failed: {exc}") from exc
        finally:
            if render_midi_path.exists():
                render_midi_path.unlink()
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("FluidSynth finished without creating keys.wav.")
        return output_path
