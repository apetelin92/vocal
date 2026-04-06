from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RenderPresetSpec:
    id: str
    label: str
    description: str
    program: int
    velocity: int = 92


RENDER_PRESETS: tuple[RenderPresetSpec, ...] = (
    RenderPresetSpec(
        id="acoustic_lead",
        label="Acoustic Lead",
        description="Soft flute-like lead that is easier to sing against than the current piano soundfont.",
        program=73,
        velocity=86,
    ),
    RenderPresetSpec(
        id="acoustic_piano",
        label="Classic Piano",
        description="Clean grand piano, best default for melody doubling and vocal guide playback.",
        program=0,
        velocity=92,
    ),
    RenderPresetSpec(
        id="bright_piano",
        label="Bright Piano",
        description="Sharper attack that cuts through a dense accompaniment.",
        program=1,
        velocity=94,
    ),
    RenderPresetSpec(
        id="electric_piano",
        label="Electric Piano",
        description="Softer electric keys tone for pop and lo-fi tracks.",
        program=4,
        velocity=88,
    ),
    RenderPresetSpec(
        id="organ",
        label="Organ",
        description="Sustained organ lead for long vocal lines.",
        program=16,
        velocity=84,
    ),
    RenderPresetSpec(
        id="strings",
        label="Strings",
        description="Light string layer for a smoother melodic guide.",
        program=48,
        velocity=82,
    ),
    RenderPresetSpec(
        id="synth_lead",
        label="Synth Lead",
        description="Synthetic lead tone for a more obvious top melody.",
        program=80,
        velocity=90,
    ),
)

DEFAULT_RENDER_PRESET_ID = RENDER_PRESETS[0].id


def get_render_preset_spec(preset_id: str) -> RenderPresetSpec:
    for preset in RENDER_PRESETS:
        if preset.id == preset_id:
            return preset
    raise KeyError(preset_id)
