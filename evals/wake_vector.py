"""Writes the Android app's wake-word test vector (android/app/src/test/resources/wake.json): what openWakeWord makes of
a made-up signal, frame by frame, which the app's WakeTest must reproduce with the same models (Wake.kt is a port of
openWakeWord's streaming features). Run it after an openWakeWord update: .venv/bin/python evals/wake_vector.py"""
import json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import jarvis

FRAMES = 40
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "android", "app", "src", "test", "resources", "wake.json")


def signal(n, x=12345):
    """Noise from a tiny generator WakeTest repeats: no audio file, nobody's voice."""
    out = np.empty(n, np.int16)
    for i in range(n):
        x = (x * 1103515245 + 12345) & 0x7fffffff
        out[i] = (x >> 8) % 6001 - 3000
    return out


if __name__ == "__main__":
    model = jarvis.wake_detector(wakeword_models=[jarvis.wake_model_file("hey_jarvis")], inference_framework="onnx")
    audio, scores = signal(FRAMES * 1280), []
    for i in range(FRAMES):
        scores.append(float(max(model.predict(audio[i * 1280:(i + 1) * 1280]).values())))
    vector = {"frames": FRAMES, "feature": [round(float(v), 5) for v in model.preprocessor.feature_buffer[-1]],
              "scores": [round(s, 6) for s in scores[-5:]]}
    with open(OUT, "w") as f:
        json.dump(vector, f)
    print(f"wrote {OUT}: scores {vector['scores']}, feature {vector['feature'][:4]}…")
