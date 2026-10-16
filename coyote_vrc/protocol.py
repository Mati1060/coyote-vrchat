"""DG-LAB Coyote 3.0 BLE V3 protocol — encoding/decoding only, no I/O.

Sources (DG-LAB's official open documentation):
  * coyote/v3/README_V3.md   — UUIDs, B0/BF commands, B1 response
  * coyote/extra/README.md   — meaning of the "wave frequency" (a PERIOD in ms)

Key points from the documentation:
  * B0 (20 bytes) is sent every 100 ms and carries both channels.
  * "Wave frequency" is the period of one output unit in ms (10..1000), sent as a byte
    10..240 after a piecewise compression. So the real maximum is 100 Hz (10 ms) and the
    practical minimum is 1 Hz (1000 ms).
  * Channel intensity: 0..200. Wave intensity (pulse width): 0..100.
  * If ANY frequency byte (outside 10..240) or wave intensity byte (outside 0..100) of a
    channel is invalid, the device drops all 4 slices of that channel.
  * BF (7 bytes) writes the soft intensity limit (0..200) and the balance parameters.
    It takes effect immediately, has no response, and MUST be rewritten on every reconnect.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

DEVICE_NAME = "47L121000"  # Pulse Host 3.0


def _uuid(short: int) -> str:
    return f"0000{short:04x}-0000-1000-8000-00805f9b34fb"


SERVICE_CMD = _uuid(0x180C)
CHAR_WRITE = _uuid(0x150A)    # all commands
CHAR_NOTIFY = _uuid(0x150B)   # all responses (B1)
SERVICE_BATTERY = _uuid(0x180A)
CHAR_BATTERY = _uuid(0x1500)  # 1 byte, 0..100

MAX_INTENSITY = 200           # absolute maximum intensity of each channel
MIN_HZ = 1.0                  # 1000 ms period
MAX_HZ = 100.0                # 10 ms period
WIDTH_MAX = 100               # maximum wave intensity (pulse width)
FREQ_BYTE_MIN = 10
FREQ_BYTE_MAX = 240

# Intensity interpretation codes (2 bits per channel)
KEEP, ADD, SUB, ABS = 0b00, 0b01, 0b10, 0b11


def clamp(value: float, lo: float, hi: float) -> float:
    return lo if value < lo else hi if value > hi else value


# --------------------------------------------------------------------------------------
# Frequency
# --------------------------------------------------------------------------------------
def period_ms_to_byte(period_ms: int) -> int:
    """Official compression of the period (10..1000 ms) into the frequency byte (10..240).

    Uses integer division, as in the documentation's pseudocode. (The doc's table lists
    650 ms -> 204, but the formula itself gives 205; we follow the formula.)
    """
    p = int(period_ms)
    if 10 <= p <= 100:
        return p
    if 101 <= p <= 600:
        return (p - 100) // 5 + 100
    if 601 <= p <= 1000:
        return (p - 600) // 10 + 200
    return 10  # out of range: the doc says to fall back to 10


def hz_to_period_ms(hz: float) -> int:
    hz = clamp(float(hz), MIN_HZ, MAX_HZ)
    return int(round(1000.0 / hz))


def hz_to_byte(hz: float) -> int:
    return period_ms_to_byte(hz_to_period_ms(hz))


def byte_to_hz(byte: int) -> float:
    """Approximate inverse (for display)."""
    b = int(clamp(byte, FREQ_BYTE_MIN, FREQ_BYTE_MAX))
    if b <= 100:
        period = b
    elif b <= 200:
        period = (b - 100) * 5 + 100
    else:
        period = (b - 200) * 10 + 600
    return 1000.0 / period


def sanitize_slices(freq_hz: Sequence[float], width: Sequence[float]) -> tuple[list[int], list[int]]:
    """4 slices of 25 ms: (Hz, width 0..100) -> (frequency bytes, wave intensity bytes)."""
    if len(freq_hz) != 4 or len(width) != 4:
        raise ValueError("exactly 4 slices of 25 ms are required")
    f = [hz_to_byte(h) for h in freq_hz]
    w = [int(round(clamp(float(x), 0, WIDTH_MAX))) for x in width]
    return f, w


# --------------------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------------------
def encode_b0(
    seq: int,
    interp_a: int,
    interp_b: int,
    set_a: int,
    set_b: int,
    freq_a: Sequence[int],
    wave_a: Sequence[int],
    freq_b: Sequence[int],
    wave_b: Sequence[int],
) -> bytes:
    """B0: 20 bytes. Layout:  B0 | seq(4b)+interp(4b) | A | B | freqA×4 | waveA×4 | freqB×4 | waveB×4."""
    for arr in (freq_a, wave_a, freq_b, wave_b):
        if len(arr) != 4:
            raise ValueError("each channel needs 4 frequency values and 4 wave intensity values")
    head = ((seq & 0x0F) << 4) | ((interp_a & 0b11) << 2) | (interp_b & 0b11)
    return bytes([0xB0, head, set_a, set_b, *freq_a, *wave_a, *freq_b, *wave_b])


def encode_bf(
    soft_a: int,
    soft_b: int,
    freq_balance_a: int = 160,
    freq_balance_b: int = 160,
    width_balance_a: int = 100,
    width_balance_b: int = 100,
) -> bytes:
    """BF: 7 bytes. Soft limit A/B (0..200), frequency balance A/B and width balance A/B (0..255)."""
    if not (0 <= soft_a <= MAX_INTENSITY and 0 <= soft_b <= MAX_INTENSITY):
        raise ValueError("soft limit outside 0..200 (the device would ignore the command)")
    return bytes([0xBF, soft_a, soft_b, freq_balance_a, freq_balance_b, width_balance_a, width_balance_b])


def encode_zero(seq: int = 1) -> bytes:
    """Zeroes both channels (absolute mode) and sends a silent wave."""
    silent_f = [FREQ_BYTE_MIN] * 4
    silent_w = [0] * 4
    return encode_b0(seq, ABS, ABS, 0, 0, silent_f, silent_w, silent_f, silent_w)


@dataclass(frozen=True)
class B1:
    seq: int
    a: int
    b: int


def parse_b1(data: bytes) -> Optional[B1]:
    """B1: B1 | seq | actual intensity A | actual intensity B."""
    if len(data) >= 4 and data[0] == 0xB1:
        return B1(seq=data[1], a=data[2], b=data[3])
    return None
