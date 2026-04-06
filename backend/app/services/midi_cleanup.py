from __future__ import annotations

from pathlib import Path

from app.core.config import Settings


class MidiCleanupService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _merge_same_pitch(self, notes: list) -> list:
        merge_gap = self.settings.midi_merge_gap_ms / 1000
        merged = []
        for note in notes:
            if not merged:
                merged.append(note)
                continue
            previous = merged[-1]
            if previous.pitch == note.pitch and note.start - previous.end <= merge_gap:
                previous.end = max(previous.end, note.end)
                previous.velocity = max(previous.velocity, note.velocity)
            else:
                merged.append(note)
        return merged

    def _snap_octaves(self, notes: list) -> list:
        if not self.settings.midi_octave_snap_enabled or not notes:
            return notes

        jump_limit = self.settings.midi_octave_snap_jump_semitones
        min_pitch = self.settings.midi_target_pitch_min
        max_pitch = self.settings.midi_target_pitch_max
        snapped = [notes[0]]

        for note in notes[1:]:
            previous = snapped[-1]
            best_pitch = note.pitch
            best_distance = abs(note.pitch - previous.pitch)
            for shift in (-24, -12, 0, 12, 24):
                candidate = note.pitch + shift
                if candidate < min_pitch or candidate > max_pitch:
                    continue
                distance = abs(candidate - previous.pitch)
                if distance < best_distance:
                    best_pitch = candidate
                    best_distance = distance
            if best_distance <= jump_limit or abs(note.pitch - previous.pitch) > jump_limit:
                note.pitch = best_pitch
            snapped.append(note)
        return snapped

    def cleanup(self, input_path: Path, output_path: Path) -> Path:
        try:
            import pretty_midi
        except ImportError as exc:
            raise RuntimeError("pretty_midi is required for MIDI cleanup.") from exc

        midi = pretty_midi.PrettyMIDI(str(input_path))
        flattened = []
        for instrument in midi.instruments:
            flattened.extend(instrument.notes)

        min_note = self.settings.midi_min_note_ms / 1000
        quantize = self.settings.midi_quantize_ms / 1000 if self.settings.midi_quantize_ms > 0 else None

        filtered = []
        for note in sorted(flattened, key=lambda item: (item.start, item.pitch, item.end)):
            if (note.end - note.start) >= min_note:
                if quantize:
                    note.start = round(note.start / quantize) * quantize
                    note.end = max(note.start + min_note, round(note.end / quantize) * quantize)
                else:
                    note.end = max(note.start + min_note, note.end)
                filtered.append(note)

        merged = self._merge_same_pitch(filtered)
        snapped = self._snap_octaves(merged)
        cleaned_notes = self._merge_same_pitch(snapped)

        cleaned = pretty_midi.PrettyMIDI()
        instrument = pretty_midi.Instrument(program=0, name="Piano")
        instrument.notes = cleaned_notes
        cleaned.instruments.append(instrument)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cleaned.write(str(output_path))
        return output_path
