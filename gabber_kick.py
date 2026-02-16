import threading
import wave
import io
import tempfile
import os
import numpy as np
import customtkinter as ctk
from tkinter import filedialog, messagebox

from synth import generate_kick

# Playback backend: try simpleaudio, otherwise fall back to Windows winsound
try:
    import simpleaudio as sa
    _HAS_SIMPLEAUDIO = True
except Exception:
    import winsound
    _HAS_SIMPLEAUDIO = False


class GabberKickApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Gabber Kick Generator")
        self.geometry("680x520")

        ctk.set_default_color_theme("dark-blue")

        self.sample_rate = 44100

        # Controls
        self.length_var = ctk.DoubleVar(value=120.0)
        self.pitch_var = ctk.DoubleVar(value=120.0)
        self.pitch_decay_var = ctk.DoubleVar(value=8.0)
        self.harmonics_var = ctk.DoubleVar(value=0.6)
        self.drive_var = ctk.DoubleVar(value=3.0)
        self.click_var = ctk.DoubleVar(value=0.7)
        self.body_var = ctk.DoubleVar(value=1.0)

        self._build_ui()

    def _build_ui(self):
        frame = ctk.CTkFrame(master=self)
        frame.pack(padx=16, pady=16, fill="both", expand=True)

        title = ctk.CTkLabel(master=frame, text="Gabber Kick Generator", font=ctk.CTkFont(size=20, weight="bold"))
        title.grid(row=0, column=0, columnspan=3, pady=(0, 12))

        # Slider builder
        def add_slider(row, label, var, from_, to_, resolution=0.1):
            lbl = ctk.CTkLabel(master=frame, text=label)
            lbl.grid(row=row, column=0, sticky="w", padx=(6, 8), pady=6)
            s = ctk.CTkSlider(master=frame, from_=from_, to=to_, variable=var, number_of_steps=int((to_-from_)/resolution) if resolution>0 else 0)
            s.grid(row=row, column=1, sticky="ew", pady=6)
            val = ctk.CTkLabel(master=frame, textvariable=var, width=60)
            val.grid(row=row, column=2, padx=(8, 6))

        frame.grid_columnconfigure(1, weight=1)

        add_slider(1, "Length (ms)", self.length_var, 30.0, 800.0, 1.0)
        add_slider(2, "Start pitch (Hz)", self.pitch_var, 60.0, 200.0, 1.0)
        add_slider(3, "Pitch decay", self.pitch_decay_var, 1.0, 18.0, 0.1)
        add_slider(4, "Harmonics (mix)", self.harmonics_var, 0.0, 1.0, 0.01)
        add_slider(5, "Drive", self.drive_var, 0.0, 10.0, 0.1)
        add_slider(6, "Click (transient)", self.click_var, 0.0, 1.0, 0.01)
        add_slider(7, "Body level", self.body_var, 0.0, 1.5, 0.01)

        buttons = ctk.CTkFrame(master=frame)
        buttons.grid(row=8, column=0, columnspan=3, pady=(14, 0))

        play_btn = ctk.CTkButton(master=buttons, text="Preview", command=self._play_async, width=120)
        play_btn.grid(row=0, column=0, padx=8)

        save_btn = ctk.CTkButton(master=buttons, text="Save As...", command=self._save_as, width=120)
        save_btn.grid(row=0, column=1, padx=8)

        hint = ctk.CTkLabel(master=frame, text="Adjust sliders and press Preview. Then Save As... to export WAV.")
        hint.grid(row=9, column=0, columnspan=3, pady=(12, 0))

        # Status label for feedback
        self.status_var = ctk.StringVar(value="Ready")
        status = ctk.CTkLabel(master=frame, textvariable=self.status_var, anchor="w")
        status.grid(row=10, column=0, columnspan=3, sticky="ew", pady=(8,0))

    def _render(self):
        params = dict(
            length_ms=self.length_var.get(),
            pitch_start=self.pitch_var.get(),
            pitch_decay=self.pitch_decay_var.get(),
            harmonics=self.harmonics_var.get(),
            drive=self.drive_var.get(),
            click_level=self.click_var.get(),
            body_level=self.body_var.get(),
            sr=self.sample_rate,
        )
        samples = generate_kick(**params)
        return samples

    def _play_async(self):
        threading.Thread(target=self._play, daemon=True).start()

    def _play(self):
        try:
            self.status_var.set("Rendering...")
            samples = self._render()
            data = (samples * 32767).astype(np.int16)
            if _HAS_SIMPLEAUDIO:
                self.status_var.set("Playing (simpleaudio)...")
                sa.play_buffer(data.tobytes(), 1, 2, self.sample_rate)
            else:
                self.status_var.set("Playing (winsound)...")
                # write to a temporary WAV file because winsound can't play async from memory
                tf = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                tf_name = tf.name
                try:
                    tf.close()
                    with wave.open(tf_name, 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(self.sample_rate)
                        wf.writeframes(data.tobytes())

                    winsound.PlaySound(tf_name, winsound.SND_FILENAME | winsound.SND_ASYNC)

                    # schedule deletion after playback duration + small buffer
                    duration = len(samples) / float(self.sample_rate)
                    def _cleanup(path):
                        try:
                            if os.path.exists(path):
                                os.remove(path)
                        except Exception:
                            pass

                    threading.Timer(duration + 1.5, _cleanup, args=(tf_name,)).start()
                except Exception:
                    # ensure temp file removed on error
                    try:
                        if os.path.exists(tf_name):
                            os.remove(tf_name)
                    except Exception:
                        pass
                    raise
            self.status_var.set("Playing (async)")
        except Exception as e:
            # show error so user can see why preview fails
            self.status_var.set(f"Error: {e}")
            try:
                messagebox.showerror("Playback error", str(e))
            except Exception:
                pass

    def _save_as(self):
        fn = filedialog.asksaveasfilename(defaultextension='.wav', filetypes=[('WAV files','*.wav')])
        if not fn:
            return
        try:
            self.status_var.set("Rendering for save...")
            samples = self._render()
            data = (samples * 32767).astype(np.int16)
            with wave.open(fn, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(data.tobytes())
            self.status_var.set(f"Saved: {fn}")
        except Exception as e:
            self.status_var.set(f"Save error: {e}")
            try:
                messagebox.showerror("Save error", str(e))
            except Exception:
                pass


if __name__ == '__main__':
    app = GabberKickApp()
    app.mainloop()
