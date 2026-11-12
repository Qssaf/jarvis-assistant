# Phone voice remote Implementation Plan

> **For agentic workers:** executed natively in one session (no subagents). Steps use checkbox syntax for tracking.

**Goal:** The Android app becomes a voice remote for the PC's Jarvis: wake word, Jarvis's real voice, the PC's chat
mirrored live, notifications, Today and PC controls, over a direct Wi-Fi/Tailscale link or the relay, with a Gemini key
for when the PC is off.

**Architecture:** The phone borrows the PC's one `Live` session: its mic frames go into `live.feed`, and `Speaker`
sends Jarvis's voice to the phone instead of the speakers (`Speaker.remote`). Everything else (tools, tasks, safety
gates) is the PC's, unchanged. `PhoneLink` gains a second transport (a WebSocket server on the PC, same handshake) and
new ops over the same encrypted channel. The app keeps the link and the microphone in a foreground service.

**Tech Stack:** Python (`phone.py`, `jarvis.py`, websockets), Kotlin/Compose, OkHttp, onnxruntime-android (openWakeWord).

**Spec:** this file (the design was settled in conversation, 2026-11-10).

## Decisions (the user's)
- Voice remote that relies on the PC, "with a lot of features"; a Gemini key for offline work.
- Direct Wi-Fi/Tailscale beside the Cloudflare relay.
- Android SDK installed in `~/Android/Sdk` (`android/local.properties`, gitignored).

## Decisions (mine)
- One voice session for PC and phone: whoever woke Jarvis last has the floor. Half-duplex on the phone (tap to interrupt).
- The wake word's three ONNX models come from the PC over the link (the PC's chosen wake word, nothing bundled).
- A paired phone may read `/api/today`, `/api/reminders`, `/api/media`, `/api/system`, `/api/conversation`,
  `/api/screen` and post `/api/media/*`, `/api/stop`, `/api/new`, `/api/reminders`: nothing else of the window's API.
- The direct port (47800, or the next free) only listens while a phone is paired or a pairing code is showing, and
  `phone_direct` (default on) is set. Unauthenticated peers get the handshake and nothing else.
- Offline: the phone opens Gemini Live itself with the user's key (voice and text); it says it can't reach the PC.

## Global Constraints
- Python and Kotlin stay byte-compatible (`handshake.json`); protocol ops are JSON inside sealed frames.
- Nothing personal in code/tests; platform code in `system.py`; user-visible changes in `CHANGELOG.md`.
- `phone.py` never imports `jarvis.py`: what it needs is passed in (`voice`, `api`).
- No commits unless asked.

## Protocol v2 (inside the encrypted channel)
Phone → PC: `pair`, `hello {token}`, `ask {id,text}`, `stop`, `voice {on}`, `audio {d}` (16 kHz PCM16, base64),
`barge`, `get {id,path}`, `post {id,path,data}`, `wake`.
PC → phone: `paired`, `ready {name,direct,wake}`, `working`, `reply {id?,text}`, `stopped`, `error`, `event {...}`
(every `emit`), `voice {on,why?}`, `audio {d}` (24 kHz), `hush`, `got {id,data|error}`, `file {name,i,n,d}`,
`wake {phrase,files}`.
Pair link: `{v:1, r: relay or "", s, k, p, d: ["ip:port", ...]}`; a link needs `r` or `d`.

## Review Focus
- Phone drops mid-session: the floor is released, the PC's own mic works again.
- "Hey Jarvis" at the PC while the phone has the floor: the PC takes it, the phone is told.
- A stranger on the LAN connects to the direct port: handshake only, no state kept after it closes.
- PC's address changed (DHCP): the phone still connects through the relay, and learns the new address from `ready`.
- A phone asks for a path outside the whitelist: refused, nothing runs.

## Tasks
- [x] 1. `phone.py`: transports (`phones[c]["send"/"close"]`), `_serve` direct server, `direct_addresses()`
  (`system.local_addresses()`), pairing without a relay. Tests: pair + ask over localhost with `phone.connect`; a bad
  first frame is closed; whitelist refusal.
- [x] 2. `phone.py` + `jarvis.py`: `event` mirror (`put`), `get`/`post` whitelist (`api` callbacks), voice floor
  (`PhoneVoice` in jarvis.py, `Speaker.remote`, `voice_loop` skip), `wake` file transfer. Tests with the real
  `jarvis.Speaker()`.
- [x] 3. Settings page: pair without a relay, show the direct address; translations.
- [x] 4. Android: `Link.kt` (race direct/relay, v2), `Wake.kt` (+ vector test against openWakeWord), `Audio.kt`,
  `JarvisService.kt`, `Gemini.kt` (offline Live), `App.kt` (state), `Screens.kt` (Talk / Today / PC tabs, settings),
  manifest (mic service, notifications, share target, assist).
- [x] 5. Build, unit tests, Paparazzi screenshot; CHANGELOG, CLAUDE.md, README.
