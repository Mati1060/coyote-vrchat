"""Slider math for the GUI, kept separate so it can be tested without tkinter."""
from __future__ import annotations


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def value_from_x(x: float, width: float, pad: float, vmin: float, vmax: float, resolution: float = 1.0) -> float:
    """Mouse position (pixels) -> slider value, snapped to `resolution`."""
    span = max(1.0, width - 2 * pad)
    frac = clamp((x - pad) / span, 0.0, 1.0)
    raw = vmin + frac * (vmax - vmin)
    snapped = round(raw / resolution) * resolution
    return clamp(snapped, vmin, vmax)


def x_from_value(v: float, width: float, pad: float, vmin: float, vmax: float) -> float:
    """Slider value -> position (pixels)."""
    span = max(1.0, width - 2 * pad)
    if vmax == vmin:
        return pad
    return pad + clamp((v - vmin) / (vmax - vmin), 0.0, 1.0) * span
