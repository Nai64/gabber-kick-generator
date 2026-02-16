# Gabber Kick Generator

Simple Gabber kick generator with a CustomTkinter GUI.

Features:
- Real-time parameter sliders for length, pitch sweep, harmonics, drive, click and body level
- Preview playback using `simpleaudio`
- Export generated kick as WAV via "Save As..."

Installation (recommended in a venv):

```powershell
pip install -r requirements.txt
```

Run:

```powershell
python gabber_kick.py
```

Notes:
- `customtkinter` provides the modern UI controls. On some systems you may prefer the classic `tkinter` look.
- The synth is a simple demonstrator; feel free to tweak `synth.py` for filters, different envelopes, or more harmonics.

Note: On Windows, if installing `simpleaudio` fails (C++ build tools required), the GUI will fall back to the built-in `winsound` API for preview playback so you can still use the app and export WAV files.
