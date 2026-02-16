import numpy as np


def generate_kick(length_ms=120.0, pitch_start=120.0, pitch_decay=8.0, harmonics=0.6, drive=3.0, click_level=0.7, body_level=1.0, sr=44100):
    """
    Synthesize a gabber-style kick.

    Parameters:
    - length_ms: length in milliseconds
    - pitch_start: starting frequency of the pitch sweep (Hz)
    - pitch_decay: controls how fast the pitch falls (larger = faster)
    - harmonics: 0..1 mix of added harmonics
    - drive: amount of waveshaping
    - click_level: level of the transient click
    - body_level: overall body level multiplier
    - sr: sample rate

    Returns: mono float32 numpy array in range [-1,1]
    """
    length = max(0.02, length_ms / 1000.0)
    n = int(sr * length)
    t = np.linspace(0, length, n, endpoint=False)

    # Pitch envelope: exponential decay from pitch_start down to a low sub frequency
    # Convert to angular frequency per sample by integration
    # Make decay scaled so pitch_decay controls speed
    decay = np.clip(pitch_decay, 0.001, 100.0)
    freq = pitch_start * np.exp(-decay * t / length)

    # Integrate phase
    phase = 2.0 * np.pi * np.cumsum(freq) / sr
    base = np.sin(phase)

    # Add harmonics (simple additive with decreasing amplitude)
    if harmonics > 0.001:
        harm = np.zeros_like(base)
        # add 2nd and 3rd harmonics with decreasing amplitude
        harm += 0.6 * np.sin(2 * phase)
        harm += 0.3 * np.sin(3 * phase)
        blended = base * (1.0 - harmonics) + harm * harmonics
    else:
        blended = base

    # Body amplitude envelope: fast attack, exponential-ish decay
    env = np.exp(-6.0 * t / length)
    body = blended * env * body_level

    # Click transient: high-frequency burst at start
    click = click_level * np.sin(2.0 * np.pi * 6000.0 * t) * np.exp(-t * 4000.0)

    sig = body + click

    # Drive / waveshaping
    if drive > 0.01:
        sig = np.tanh(sig * drive)

    # gentle final smoothing fade to avoid zipper noise
    sig *= np.linspace(1.0, 0.0, n)

    # normalize
    peak = np.max(np.abs(sig))
    if peak > 0:
        sig = sig / peak * 0.95

    return sig.astype(np.float32)
