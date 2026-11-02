"""Does skipping the wake-word model while the room is quiet (jarvis.WakeGate) miss wake-ups? Replays the user's own
clips (DATA/wake/yes: real wake-ups, DATA/wake/no: what woke it that wasn't them), each after a few seconds of quiet
room noise, through openWakeWord fed every frame and through the gate, and compares the scores. Reads the clips, writes
nothing, needs no network. Prints file names (timestamps) only, never audio:

    .venv/bin/python evals/wake_eval.py [max clips per kind]
"""
import collections, glob, os, sys, wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import jarvis  # noqa: E402


def read(path):
    with wave.open(path) as w:
        audio = np.frombuffer(w.readframes(w.getnframes()), np.int16)
        return audio if w.getframerate() == 16000 and w.getnchannels() == 1 else None


def replay(model, clip, gated, quiet_s=6):
    """The clip's best score, and how many frames the wake-word model ran (pre-roll included)."""
    np.random.seed(0)  # (openWakeWord's reset fills its buffers with random noise: the same for both ways)
    model.reset()
    noise = np.random.default_rng(len(clip)).normal(0, 12, 16000 * (quiet_s + 2)).astype(np.int16)  # the same room both ways
    audio = np.concatenate([noise[:16000 * quiet_s], clip, noise[16000 * quiet_s:]])
    level, recent, gate = jarvis.MicLevel(), collections.deque(maxlen=25), jarvis.WakeGate(model)
    best, ran = 0.0, 0
    for i in range(0, len(audio) - 1279, 1280):
        f = level(audio[i:i + 1280])
        recent.append(f)
        if gated:
            before = gate.skipped
            best = max(best, gate.score(f, recent, level.sound))
            ran += 0 if gate.skipped else 1 + min(before, jarvis.WAKE_PRE_ROLL)
        else:
            best, ran = max(best, max(model.predict(f).values())), ran + 1
    return best, ran


if __name__ == "__main__":
    limit = int(sys.argv[1]) if sys.argv[1:] else 200
    folder = jarvis.wake_folder("hey_jarvis")
    model = jarvis.wake_detector(wakeword_models=[jarvis.wake_model_file("hey_jarvis")], inference_framework="onnx", vad_threshold=0.5)
    changed = []
    for kind in ("yes", "no"):
        clips = [(p, read(p)) for p in sorted(glob.glob(os.path.join(folder, kind, "*.wav")))[-limit:]]
        clips = [(p, c) for p, c in clips if c is not None]
        if not clips:
            print(f"{kind}: no clips in {os.path.join(folder, kind)}")
            continue
        full, gated, runs = [], [], [0, 0]
        for p, c in clips:
            (a, n1), (b, n2) = replay(model, c, False), replay(model, c, True)
            full.append(a), gated.append(b)
            runs[0] += n1
            runs[1] += n2
            if (a >= 0.5) != (b >= 0.5):
                changed.append(f"  {kind}/{os.path.basename(p)}: every frame {a:.2f}, gated {b:.2f}")
        full, gated = np.array(full), np.array(gated)
        print(f"{kind}: {len(clips)} clips | woke every frame {(full >= 0.5).sum()}, gated {(gated >= 0.5).sum()} | "
              f"mean score change {np.abs(full - gated).mean():.3f} | model ran {runs[1] / runs[0]:.0%} as often "
              f"(here 6 s of quiet per clip; a real quiet room is far longer)")
    print("decisions that changed:\n" + "\n".join(changed) if changed else "no decision changed")
