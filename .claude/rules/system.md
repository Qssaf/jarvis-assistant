---
paths:
  - "**/system.py"
  - "**/atspi_helper.py"
  - "**/evals/wake_eval.py"
  - "**/evals/wake_vector.py"
---

# The OS layer, the microphone and the wake word

Part of this repository's architecture notes (the rest: `CLAUDE.md` and the other files here). Each paragraph is how
that part works and what broke before.

**OS layer.** Everything platform-specific goes in `system.py`, never in the other modules. It picks the best
available tool at call time:
- Audio: PipeWire `pw-record`/`pw-play`, else sounddevice. The mic slider is the user's (calls, Discord): `MicLevel`
  in `voice_loop` brings speech back to ~4000 RMS whatever the slider or card gain (-20..+40 dB, adapting over ~3 s
  of talking, never on Jarvis's own voice), so the wake word, `feed`'s fixed thresholds and Gemini get a steady level.
  The always-on recording never sits on a Bluetooth headset's mic while there's another: WirePlumber's
  `autoswitch-bluetooth-profile` puts a headset in its call profile for as long as any capture stream is linked to its
  `bluez_input` node, and that node is the default mic whenever the headset is connected. `mic_frames(pick=mic_choice)`
  pins pw-record (`node.dont-move`) to `pick_mic`'s node (the default if it isn't Bluetooth, else the best other one; ""
  = the default: no other mic, or the `bluetooth_mic` setting, `system.headset_mic`), `_follow_mic` asks again every
  `MIC_CHECK` s and restarts it on another (`mic_choice` is None when PipeWire can't be asked: the recorder then stays); notes (`record_audio`) and `ec_module`'s capture use the same choice. Check
  it for real with `pactl list cards` (the bluez card's Active Profile stays a2dp) and `pw-dump`'s links.
  A few seconds after each start `mic_source` logs the node pw-record really reads ("[voice] the microphone is ...");
  if that isn't the echo canceller, the echo-cancelled gate is switched off (half-duplex) instead of hearing itself.
- Screenshots: KDE `jarvis-shot` helper → spectacle → grim → gnome-screenshot → mss.
- Input: wdotool/ydotool on Wayland, pynput otherwise; text on Windows goes in one `SendInput` (`_send_text`).
- Media: MPRIS on Linux; on Windows a long-lived PowerShell (`WIN_MEDIA`, GSMTC) answers one JSON line per request, with
  a timeout that kills it (a stalled app's media session must never block the window's thread pool).
- Windows: kdotool on KDE Wayland, pywinctl otherwise.
- Idle (`user_idle`): Wayland's ext-idle-notify on its own connection (`_idle_watch`, 2 s steps; KWin has no
  `GetSessionIdleTime`), GNOME's Mutter IdleMonitor, `xprintidle`, Windows `GetLastInputInfo`; None if unknown. Input
  Jarvis makes (`@_mine`) doesn't count as the user (`_was_mine`, with Wayland's 2 s step): when the latest input was
  its own, it's the user's seen just before it (`_user_input`), inf if none.
- Accessibility: AT-SPI on Linux via `atspi_helper.py` under `/usr/bin/python3` (it needs `gi`); pywinauto UIA on
  Windows. Both share the same `ask({"cmd": ...})` protocol. On Linux, Chromium and Electron apps only expose their
  page contents when started with `--force-renderer-accessibility` plus `ACCESSIBILITY_ENABLED=1`, and only at
  startup: `tool_launch` adds both when `system.chromium_based` says so. An app that's open but missing from the tree
  never appears, so `a11y_wait` only waits for one Jarvis has just started.

**Echo cancelling** (`echo_cancel`). On Windows, `system.mic_frames` with a target runs livekit's WebRTC canceller fed
by a soundcard WASAPI loopback of the default speakers (Windows-only requirements), falling back to the plain mic via
`on_source` if it can't start; Health's "Echo cancelling" row says which. On Linux/PipeWire, `start_echo_cancel` loads `module-echo-cancel` in `monitor.mode`, so
the reference is everything the default output plays (games, calls, Jarvis), not only Jarvis's voice; the mic reads
`jarvis-ec-source` (pinned with `node.dont-move`: WirePlumber's "follow the default mic" otherwise moved it onto the raw
mic, and Jarvis heard itself; check with `pw-link -l`) and `Speaker.echo_cancelled` swaps the half-duplex mic gate for a level gate: while Jarvis talks,
`feed` sends silence unless the user is clearly talking (the canceller leaves a faint echo Gemini hears as the user). The module lives as long as its
`pw-cli` process: `atexit` stops it, so a restart must run the exit handlers (`restart_soon` does before `execv`).

**Wake word.** `wake_word` is a `store.WAKE_WORDS` key or the path of the user's own `.onnx`; `store.wake_phrase` is
what every message tells the user to say. `VoiceLearner` keeps clips and verifier per wake word (`wake_folder`:
"Hey Jarvis" at the folder's root, a custom model by its contents' hash), and `voice_loop` reloads when the word
changes. openWakeWord's verifier score replaces the model's from `custom_verifier_threshold` (0.1) up, so "Only wake
for my voice" raises the score needed (`wake_bar`, `ONLY_ME`), not that threshold (raising it skips verification). `WakeGate` runs the model only while `MicLevel.sound` (and
`WAKE_TAIL` after), keeping its Silero VAD fed on quiet frames (a VAD that missed the gap zeroed sure wake-ups) and
replaying `WAKE_PRE_ROLL` frames when sound returns; `evals/wake_eval.py` replays the user's own clips both ways.
