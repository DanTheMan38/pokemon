from __future__ import annotations

from pathlib import Path
import math
import random
import struct
import wave


ROOT = Path(__file__).resolve().parents[1]
AUDIO_DIR = ROOT / "assets" / "audio"
SAMPLE_RATE = 22050
MAX_AMP = 32767

NOTE_INDEX = {
    "C": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
}


def note_to_freq(note: str) -> float:
    if note == "R":
        return 0.0

    pitch = note[:-1]
    octave = int(note[-1])
    semitone = NOTE_INDEX[pitch]
    midi = semitone + (octave + 1) * 12
    return 440.0 * (2 ** ((midi - 69) / 12))


def write_wave(path: Path, samples: list[float]) -> None:
    clipped = [max(-1.0, min(1.0, sample)) for sample in samples]
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(
            b"".join(struct.pack("<h", int(sample * MAX_AMP)) for sample in clipped)
        )


def envelope(position: int, total: int, attack: float = 0.03, release: float = 0.16) -> float:
    attack_samples = max(1, int(total * attack))
    release_samples = max(1, int(total * release))
    if position < attack_samples:
        return position / attack_samples
    if position > total - release_samples:
        return max(0.0, (total - position) / release_samples)
    return 1.0


def oscillator(phase: float, kind: str) -> float:
    if kind == "square":
        return 1.0 if math.sin(phase) >= 0 else -1.0
    if kind == "triangle":
        return (2 / math.pi) * math.asin(math.sin(phase))
    if kind == "sine":
        return math.sin(phase)
    if kind == "saw":
        turns = phase / (2 * math.pi)
        return 2 * (turns - math.floor(turns + 0.5))
    raise ValueError(f"Unknown oscillator: {kind}")


def add_tone(
    buffer: list[float],
    start_seconds: float,
    duration_seconds: float,
    frequency: float,
    *,
    volume: float,
    kind: str,
    vibrato: float = 0.0,
    vibrato_rate: float = 5.0,
) -> None:
    if frequency <= 0:
        return

    start = int(start_seconds * SAMPLE_RATE)
    total = max(1, int(duration_seconds * SAMPLE_RATE))
    end = min(len(buffer), start + total)
    for index in range(start, end):
        offset = index - start
        t = offset / SAMPLE_RATE
        freq = frequency * (1 + vibrato * math.sin(2 * math.pi * vibrato_rate * t))
        phase = 2 * math.pi * freq * t
        amp = oscillator(phase, kind) * envelope(offset, total) * volume
        buffer[index] += amp


def add_noise_burst(
    buffer: list[float],
    start_seconds: float,
    duration_seconds: float,
    *,
    volume: float,
    color: str = "white",
) -> None:
    rng = random.Random(1337 + int(start_seconds * 1000))
    start = int(start_seconds * SAMPLE_RATE)
    total = max(1, int(duration_seconds * SAMPLE_RATE))
    end = min(len(buffer), start + total)
    last = 0.0
    for index in range(start, end):
        offset = index - start
        env = envelope(offset, total, attack=0.02, release=0.85)
        if color == "soft":
            noise = (rng.random() * 2 - 1) * 0.6 + last * 0.4
            last = noise
        else:
            noise = rng.random() * 2 - 1
        buffer[index] += noise * env * volume


def add_kick(buffer: list[float], start_seconds: float, volume: float = 0.55) -> None:
    start = int(start_seconds * SAMPLE_RATE)
    total = int(0.18 * SAMPLE_RATE)
    end = min(len(buffer), start + total)
    for index in range(start, end):
        offset = index - start
        t = offset / SAMPLE_RATE
        freq = 88 - t * 46
        env = envelope(offset, total, attack=0.01, release=0.92)
        sample = math.sin(2 * math.pi * freq * t) * env * volume
        buffer[index] += sample


def add_hihat(buffer: list[float], start_seconds: float, volume: float = 0.12) -> None:
    add_noise_burst(buffer, start_seconds, 0.045, volume=volume, color="white")


def render_music(
    length_beats: float,
    bpm: int,
    events: list[tuple[float, str, float, str, float, float, float]],
    drums: list[tuple[str, float]],
) -> list[float]:
    beat = 60.0 / bpm
    total_seconds = length_beats * beat
    buffer = [0.0 for _ in range(int(total_seconds * SAMPLE_RATE))]

    for start_beat, note, duration, kind, volume, vibrato, vibrato_rate in events:
        add_tone(
            buffer,
            start_beat * beat,
            duration * beat,
            note_to_freq(note),
            volume=volume,
            kind=kind,
            vibrato=vibrato,
            vibrato_rate=vibrato_rate,
        )

    for drum, start_beat in drums:
        when = start_beat * beat
        if drum == "kick":
            add_kick(buffer, when)
        elif drum == "hat":
            add_hihat(buffer, when)
        elif drum == "snare":
            add_noise_burst(buffer, when, 0.1, volume=0.18, color="soft")

    return buffer


def render_sfx(components: list[tuple[str, float, float, float, str, float, float]], noise=None) -> list[float]:
    total_seconds = 0.0
    for _, start, duration, _, _, _, _ in components:
        total_seconds = max(total_seconds, start + duration)
    if noise:
        for _, start, duration, _ in noise:
            total_seconds = max(total_seconds, start + duration)

    buffer = [0.0 for _ in range(int(total_seconds * SAMPLE_RATE) + 1)]
    for note, start, duration, volume, kind, vibrato, vibrato_rate in components:
        add_tone(
            buffer,
            start,
            duration,
            note_to_freq(note),
            volume=volume,
            kind=kind,
            vibrato=vibrato,
            vibrato_rate=vibrato_rate,
        )
    if noise:
        for color, start, duration, volume in noise:
            add_noise_burst(buffer, start, duration, volume=volume, color=color)
    return buffer


def build_overworld_theme() -> list[float]:
    events: list[tuple[float, str, float, str, float, float, float]] = []
    drums: list[tuple[str, float]] = []
    chords = [
        ("C4", "E4", "G4", "C3"),
        ("A3", "C4", "E4", "A2"),
        ("F3", "A3", "C4", "F2"),
        ("G3", "B3", "D4", "G2"),
        ("C4", "E4", "G4", "C3"),
        ("A3", "C4", "E4", "A2"),
        ("F3", "A3", "C4", "F2"),
        ("G3", "B3", "D4", "G2"),
    ]
    melodies = [
        ["G5", "E5", "D5", "C5"],
        ["E5", "G5", "A5", "G5"],
        ["A5", "G5", "E5", "C5"],
        ["D5", "E5", "G5", "R"],
        ["G5", "A5", "G5", "E5"],
        ["C6", "A5", "G5", "E5"],
        ["F5", "E5", "D5", "C5"],
        ["E5", "G5", "C6", "R"],
    ]

    for bar, chord in enumerate(chords):
        base = bar * 4
        arp = [chord[0], chord[1], chord[2], chord[1], chord[2], chord[1], chord[0], chord[1]]
        for step, note in enumerate(arp):
            events.append((base + step * 0.5, note, 0.45, "square", 0.11, 0.0, 5.0))
        events.append((base, chord[3], 1.75, "triangle", 0.18, 0.0, 5.0))
        events.append((base + 2, chord[3], 1.75, "triangle", 0.18, 0.0, 5.0))
        melody = melodies[bar]
        for beat_index, note in enumerate(melody):
            if note != "R":
                events.append((base + beat_index, note, 0.85, "sine", 0.14, 0.01, 6.0))

        drums.extend([("kick", base), ("hat", base + 1), ("snare", base + 2), ("hat", base + 3)])
        drums.extend([("hat", base + 0.5), ("hat", base + 1.5), ("hat", base + 2.5), ("hat", base + 3.5)])

    return render_music(32, 134, events, drums)


def build_battle_theme() -> list[float]:
    events: list[tuple[float, str, float, str, float, float, float]] = []
    drums: list[tuple[str, float]] = []
    chords = [
        ("A3", "C4", "E4", "A2"),
        ("F3", "A3", "C4", "F2"),
        ("G3", "B3", "D4", "G2"),
        ("E3", "G3", "B3", "E2"),
        ("A3", "C4", "E4", "A2"),
        ("F3", "A3", "C4", "F2"),
        ("G3", "B3", "D4", "G2"),
        ("E3", "G3", "B3", "E2"),
    ]
    leads = [
        ["A5", "C6", "E6", "C6", "A5", "C6", "E6", "G6"],
        ["A5", "C6", "F6", "E6", "C6", "A5", "G5", "E5"],
        ["G5", "B5", "D6", "B5", "G5", "B5", "D6", "E6"],
        ["E5", "G5", "B5", "D6", "B5", "G5", "E5", "R"],
        ["A5", "C6", "E6", "G6", "E6", "C6", "A5", "G5"],
        ["F6", "E6", "C6", "A5", "F5", "A5", "C6", "E6"],
        ["G5", "B5", "D6", "G6", "D6", "B5", "G5", "E5"],
        ["E5", "G5", "B5", "D6", "G6", "E6", "C6", "R"],
    ]

    for bar, chord in enumerate(chords):
        base = bar * 4
        bass_steps = [0, 0.75, 1.5, 2.25, 3.0]
        for step in bass_steps:
            events.append((base + step, chord[3], 0.55, "triangle", 0.19, 0.0, 5.0))
        arp = [chord[0], chord[1], chord[2], chord[1], chord[2], chord[1], chord[0], chord[2]]
        for step, note in enumerate(arp):
            events.append((base + step * 0.5, note, 0.34, "square", 0.11, 0.0, 5.0))
        for step, note in enumerate(leads[bar]):
            if note != "R":
                events.append((base + step * 0.5, note, 0.36, "saw", 0.10, 0.014, 7.0))

        drums.extend([("kick", base), ("hat", base + 0.5), ("snare", base + 1), ("hat", base + 1.5)])
        drums.extend([("kick", base + 2), ("hat", base + 2.5), ("snare", base + 3), ("hat", base + 3.5)])

    return render_music(32, 156, events, drums)


def build_victory_jingle() -> list[float]:
    return render_sfx(
        [
            ("C5", 0.00, 0.16, 0.22, "square", 0.0, 5.0),
            ("E5", 0.16, 0.16, 0.22, "square", 0.0, 5.0),
            ("G5", 0.32, 0.20, 0.22, "square", 0.0, 5.0),
            ("C6", 0.52, 0.38, 0.24, "square", 0.0, 5.0),
            ("C4", 0.00, 0.90, 0.08, "triangle", 0.0, 5.0),
        ]
    )


def build_sound_effects() -> dict[str, list[float]]:
    return {
        "menu_move": render_sfx([("C6", 0.0, 0.05, 0.18, "square", 0.0, 5.0)]),
        "confirm": render_sfx(
            [
                ("G5", 0.0, 0.06, 0.16, "square", 0.0, 5.0),
                ("C6", 0.04, 0.08, 0.18, "square", 0.0, 5.0),
            ]
        ),
        "cancel": render_sfx(
            [
                ("C6", 0.0, 0.05, 0.16, "square", 0.0, 5.0),
                ("G5", 0.04, 0.08, 0.18, "square", 0.0, 5.0),
            ]
        ),
        "interact": render_sfx(
            [
                ("E5", 0.0, 0.07, 0.18, "triangle", 0.0, 5.0),
                ("A5", 0.06, 0.10, 0.18, "square", 0.0, 5.0),
            ]
        ),
        "pickup": render_sfx(
            [
                ("C6", 0.0, 0.08, 0.18, "square", 0.0, 5.0),
                ("E6", 0.07, 0.08, 0.18, "square", 0.0, 5.0),
                ("G6", 0.14, 0.12, 0.18, "square", 0.0, 5.0),
            ]
        ),
        "grass_step": render_sfx([], noise=[("soft", 0.0, 0.07, 0.10)]),
        "encounter": render_sfx(
            [
                ("A5", 0.00, 0.08, 0.18, "saw", 0.0, 5.0),
                ("E6", 0.05, 0.08, 0.20, "saw", 0.0, 5.0),
                ("A6", 0.10, 0.14, 0.22, "square", 0.0, 5.0),
            ],
            noise=[("white", 0.02, 0.18, 0.08)],
        ),
        "attack": render_sfx(
            [
                ("C5", 0.00, 0.05, 0.12, "square", 0.0, 5.0),
                ("G4", 0.04, 0.06, 0.12, "square", 0.0, 5.0),
            ],
            noise=[("white", 0.00, 0.10, 0.10)],
        ),
        "hit": render_sfx(
            [("C3", 0.0, 0.10, 0.24, "triangle", 0.0, 5.0)],
            noise=[("soft", 0.0, 0.08, 0.13)],
        ),
        "heal": render_sfx(
            [
                ("C5", 0.00, 0.10, 0.14, "sine", 0.0, 5.0),
                ("E5", 0.08, 0.10, 0.14, "sine", 0.0, 5.0),
                ("A5", 0.16, 0.16, 0.16, "square", 0.0, 5.0),
            ]
        ),
        "orb": render_sfx(
            [
                ("G5", 0.0, 0.08, 0.16, "triangle", 0.0, 5.0),
                ("D5", 0.04, 0.10, 0.16, "square", 0.0, 5.0),
            ],
            noise=[("soft", 0.0, 0.10, 0.07)],
        ),
        "capture": render_sfx(
            [
                ("C6", 0.00, 0.08, 0.18, "square", 0.0, 5.0),
                ("E6", 0.08, 0.08, 0.18, "square", 0.0, 5.0),
                ("G6", 0.16, 0.12, 0.18, "square", 0.0, 5.0),
                ("C7", 0.28, 0.20, 0.20, "square", 0.0, 5.0),
            ]
        ),
        "level_up": render_sfx(
            [
                ("C5", 0.00, 0.08, 0.16, "square", 0.0, 5.0),
                ("E5", 0.08, 0.08, 0.16, "square", 0.0, 5.0),
                ("G5", 0.16, 0.08, 0.16, "square", 0.0, 5.0),
                ("C6", 0.24, 0.20, 0.18, "square", 0.0, 5.0),
            ]
        ),
        "quest": render_sfx(
            [
                ("G5", 0.00, 0.08, 0.16, "square", 0.0, 5.0),
                ("C6", 0.08, 0.08, 0.16, "square", 0.0, 5.0),
                ("E6", 0.16, 0.12, 0.16, "square", 0.0, 5.0),
                ("G6", 0.28, 0.20, 0.18, "square", 0.0, 5.0),
            ]
        ),
        "run": render_sfx(
            [
                ("E5", 0.00, 0.05, 0.16, "triangle", 0.0, 5.0),
                ("C5", 0.04, 0.07, 0.16, "triangle", 0.0, 5.0),
            ]
        ),
        "faint": render_sfx(
            [
                ("A4", 0.00, 0.10, 0.14, "square", 0.0, 5.0),
                ("E4", 0.08, 0.12, 0.14, "triangle", 0.0, 5.0),
                ("C4", 0.18, 0.20, 0.14, "triangle", 0.0, 5.0),
            ]
        ),
        "error": render_sfx(
            [
                ("C5", 0.00, 0.05, 0.16, "square", 0.0, 5.0),
                ("Bb4", 0.06, 0.10, 0.16, "square", 0.0, 5.0),
            ]
        ),
    }


def main() -> None:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    write_wave(AUDIO_DIR / "overworld_theme.wav", build_overworld_theme())
    write_wave(AUDIO_DIR / "battle_theme.wav", build_battle_theme())
    write_wave(AUDIO_DIR / "victory_jingle.wav", build_victory_jingle())
    for name, samples in build_sound_effects().items():
        write_wave(AUDIO_DIR / f"{name}.wav", samples)
    print(f"Generated audio assets in {AUDIO_DIR}")


if __name__ == "__main__":
    main()
