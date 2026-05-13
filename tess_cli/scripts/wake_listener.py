import argparse
import os
import re
import subprocess
import tempfile
import time

import numpy as np
import scipy.io.wavfile as wav
import sounddevice as sd
import whisper


class TessWakeListener:
    """
    Wake flow:
    1) detect two claps in a short window
    2) record short voice snippet
    3) if "tess" is heard, launch Start_TESS.bat
    """

    def __init__(
        self,
        start_script,
        sample_rate=16000,
        chunk_duration=0.05,
        clap_window_sec=1.5,
        clap_refractory_sec=0.18,
        post_clap_listen_sec=3.0,
    ):
        self.start_script = os.path.abspath(start_script)
        self.sample_rate = int(sample_rate)
        self.chunk_size = int(self.sample_rate * chunk_duration)
        self.clap_window_sec = float(clap_window_sec)
        self.clap_refractory_sec = float(clap_refractory_sec)
        self.post_clap_listen_sec = float(post_clap_listen_sec)
        self.last_clap_time = 0.0
        self.clap_times = []
        self.cooldown_until = 0.0
        self.model = None

    def _load_model(self):
        if self.model is None:
            print("[WAKE] Loading Whisper model (tiny)...")
            self.model = whisper.load_model("tiny")

    def _estimate_noise_threshold(self, seconds=1.0):
        frames = int(self.sample_rate * seconds)
        data = sd.rec(frames, samplerate=self.sample_rate, channels=1, dtype="int16")
        sd.wait()
        rms = float(np.sqrt(np.mean(np.square(data.astype(np.float32)))))
        return max(rms * 4.0, 1200.0)

    def _heard_wake_word(self):
        frames = int(self.sample_rate * self.post_clap_listen_sec)
        print("[WAKE] Two claps detected. Say 'Tess'...")
        audio = sd.rec(frames, samplerate=self.sample_rate, channels=1, dtype="int16")
        sd.wait()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_wav = f.name
        try:
            wav.write(tmp_wav, self.sample_rate, audio)
            self._load_model()
            result = self.model.transcribe(tmp_wav, fp16=False)
            text = (result.get("text") or "").strip().lower()
            clean = re.sub(r"[^a-z\s]", " ", text)
            print(f"[WAKE] Heard: {text or '(silence)'}")
            return ("tess" in clean) or (" test " in f" {clean} ")
        finally:
            try:
                os.remove(tmp_wav)
            except OSError:
                pass

    def _is_tess_running(self):
        try:
            out = subprocess.check_output(
                ["tasklist", "/v", "/fo", "csv"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).lower()
            return "tess ai supervisor" in out
        except Exception:
            return False

    def _launch_tess(self):
        if self._is_tess_running():
            print("[WAKE] TESS is already running.")
            return
        if not os.path.exists(self.start_script):
            print(f"[WAKE] Start script not found: {self.start_script}")
            return
        print("[WAKE] Launching TESS terminal...")
        os.startfile(self.start_script)  # Windows only

    def run(self):
        print("[WAKE] Calibrating microphone...")
        threshold = self._estimate_noise_threshold()
        print(f"[WAKE] Clap threshold: {threshold:.1f}")
        print("[WAKE] Listening for 2 claps + 'tess' ... (Ctrl+C to stop)")

        with sd.InputStream(
            samplerate=self.sample_rate, channels=1, dtype="int16"
        ) as stream:
            while True:
                now = time.time()
                data, _ = stream.read(self.chunk_size)
                rms = float(np.sqrt(np.mean(np.square(data.astype(np.float32)))))

                if now < self.cooldown_until:
                    continue

                if rms >= threshold and (now - self.last_clap_time) > self.clap_refractory_sec:
                    self.last_clap_time = now
                    self.clap_times.append(now)
                    self.clap_times = [t for t in self.clap_times if now - t <= self.clap_window_sec]

                    if len(self.clap_times) >= 2:
                        self.clap_times.clear()
                        if self._heard_wake_word():
                            self._launch_tess()
                            self.cooldown_until = time.time() + 8.0
                        else:
                            print("[WAKE] Wake word not detected.")


def main():
    default_start = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "Start_TESS.bat")
    )
    parser = argparse.ArgumentParser(description="TESS clap+voice wake listener")
    parser.add_argument(
        "--start-script",
        default=default_start,
        help="Path to Start_TESS.bat",
    )
    args = parser.parse_args()
    listener = TessWakeListener(start_script=args.start_script)
    listener.run()


if __name__ == "__main__":
    main()

