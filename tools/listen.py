"""Talk to the robot: record from the microphone, turn speech into text on the laptop, hand it to robot_do.

    .venv/Scripts/python tools/listen.py              # records 4 s, prints what it heard, then the robot acts
    .venv/Scripts/python tools/listen.py --seconds 6
    .venv/Scripts/python tools/listen.py --file x.wav # transcribe a file instead (used by tests)

Speech-to-text is OpenAI Whisper (base.en by default, ~150 MB, downloads once) running locally on the GPU via
transformers - no internet needed after the first run, nothing is sent anywhere. WHISPER=openai/whisper-small.en
for better accuracy (slower). The panel's Speak button runs this.
"""
import argparse
import os
import subprocess
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.environ.get("WHISPER", "openai/whisper-base.en")
RATE = 16000


def record(seconds):
    import sounddevice as sd
    print(f"listening for {seconds:.0f} s... speak now", flush=True)
    audio = sd.rec(int(seconds * RATE), samplerate=RATE, channels=1, dtype="float32")
    sd.wait()
    return audio[:, 0]


def transcribe(audio):
    import torch
    from transformers import pipeline
    asr = pipeline("automatic-speech-recognition", model=MODEL,
                   device=0 if torch.cuda.is_available() else -1)
    t0 = time.perf_counter()
    text = asr({"raw": audio.astype(np.float32), "sampling_rate": RATE})["text"].strip()
    return text, time.perf_counter() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=4.0)
    ap.add_argument("--file", default="")
    ap.add_argument("--no-act", action="store_true", help="only print the text")
    a = ap.parse_args()
    if a.file:
        import soundfile as sf
        audio, sr = sf.read(a.file, dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(1)
        if sr != RATE:
            audio = np.interp(np.linspace(0, len(audio), int(len(audio) * RATE / sr), endpoint=False),
                              np.arange(len(audio)), audio).astype(np.float32)
    else:
        audio = record(a.seconds)
    if np.abs(audio).max() < 0.01:
        print("heard nothing (mic muted or too quiet?)")
        return
    text, secs = transcribe(audio)
    print(f'heard: "{text}"  ({secs:.1f} s to transcribe)', flush=True)
    if text and not a.no_act:
        subprocess.run([sys.executable, "-u", os.path.join(ROOT, "tools", "robot_do.py"), text], cwd=ROOT)


if __name__ == "__main__":
    main()
