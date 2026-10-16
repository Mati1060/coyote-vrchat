"""Basic patterns.

As in the official apps, a pattern shapes the WAVEFORM (frequency in Hz and pulse width 0..100)
over time. The channel intensity (the "volume", 0..200) still comes from the sliders/OSC/AI.
Each function receives the pattern time `t` (seconds, already multiplied by the speed) and
returns (hz, width).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, Dict, Tuple

Sample = Tuple[float, float]


@dataclass(frozen=True)
class PatternDef:
    key: str
    label: str
    period: float          # length of one cycle in seconds (used by "alternate A/B")
    description: str
    fn: Callable[[float, float, float, int], Sample]


def _const(t: float, hz: float, w: float, seed: int) -> Sample:
    return hz, w


def _breathing(t: float, hz: float, w: float, seed: int) -> Sample:
    return hz, w * (0.5 - 0.5 * math.cos(2 * math.pi * t / 8.0))


def _pulse(t: float, hz: float, w: float, seed: int) -> Sample:
    return hz, (w if (t % 1.0) < 0.3 else 0.0)


def _heartbeat(t: float, hz: float, w: float, seed: int) -> Sample:
    ph = t % 1.2
    return hz, (w if (ph < 0.12 or 0.28 <= ph < 0.40) else 0.0)


def _ramp(t: float, hz: float, w: float, seed: int) -> Sample:
    return hz, w * ((t % 5.0) / 5.0)


def _sweep(t: float, hz: float, w: float, seed: int) -> Sample:
    phase = (t % 12.0) / 12.0
    tri = 1.0 - abs(2.0 * phase - 1.0)          # 0 -> 1 -> 0
    return 5.0 * (100.0 / 5.0) ** tri, w         # exponential sweep 5 -> 100 -> 5 Hz


def _random(t: float, hz: float, w: float, seed: int) -> Sample:
    step = int(t / 0.5)
    rng = random.Random(seed * 100003 + step)    # deterministic per 0.5 s step
    return rng.uniform(5.0, 100.0), rng.uniform(0.3, 1.0) * w


def _staccato(t: float, hz: float, w: float, seed: int) -> Sample:
    return hz, (w if (t % 0.25) < 0.10 else 0.0)


PATTERNS: Dict[str, PatternDef] = {
    p.key: p
    for p in (
        PatternDef("const", "Constant", 1.0, "Fixed frequency and width from the sliders", _const),
        PatternDef("breathing", "Breathing", 8.0, "Width rises and falls smoothly (8 s per cycle)", _breathing),
        PatternDef("pulse", "Pulses", 1.0, "0.3 s on / 0.7 s off", _pulse),
        PatternDef("heartbeat", "Heartbeat", 1.2, "Two quick beats per cycle", _heartbeat),
        PatternDef("ramp", "Ramp", 5.0, "Width rises from 0 to max over 5 s and restarts", _ramp),
        PatternDef("sweep", "Frequency sweep", 12.0, "Frequency goes 5 to 100 Hz and back (12 s)", _sweep),
        PatternDef("random", "Random", 0.5, "Frequency and width re-rolled every 0.5 s", _random),
        PatternDef("staccato", "Staccato", 0.25, "Short, quick taps", _staccato),
    )
}

DEFAULT_PATTERN = "const"


def sample(key: str, t: float, base_hz: float, base_width: float, seed: int = 0) -> Sample:
    """Pattern value at time t, already limited to 1..100 Hz and 0..100 width."""
    hz, width = PATTERNS[key].fn(max(0.0, t), base_hz, base_width, seed)
    return max(1.0, min(100.0, hz)), max(0.0, min(100.0, width))


def labels() -> Dict[str, str]:
    return {k: p.label for k, p in PATTERNS.items()}
