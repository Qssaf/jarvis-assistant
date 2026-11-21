---
paths:
  - "**/phone.py"
  - "**/remote.py"
  - "**/android/**"
  - "**/relay/**"
---

# The phone: Telegram, the Android app and the relay

Part of this repository's architecture notes (the rest: `CLAUDE.md` and the other files here). Each paragraph is how
that part works and what broke before.

**Phone.** `remote.py` long-polls the user's own Telegram bot (token in the keychain as `telegram`) and answers only the
chat paired with the code shown in Settings (five wrong codes and a chat is ignored). Its tasks run `Brain.ask(...,
remote=True)` on their own thread, so `/stop` is still read while one works; `ask_user` refuses (the user can't answer
out loud). Phone tasks run side by side with the others; `/stop` stops them all and says which.
`phone.py` is the Android app's link (`android/`, Kotlin), two ways with one handshake: the PC and the app both dial out to
the user's own relay (`relay/worker.js`, a Cloudflare Worker with one Durable Object per PC that only forwards frames),
and with `phone_direct` the PC also listens on `phone.PORT` (only while a phone is paired or a pairing code shows) for
phones on its own network or VPN: the pairing code and every `ready` carry `system.local_addresses()`, and the app
races them against the relay (`Link.kt`: direct wins). `phones[c]` holds each connection's `send`/`close`, whichever way
it came. An `ask`'s id comes back on its `reply`; the PC keeps each phone's last `KEEP` answers, sent or not (one sent into
a dying link was lost), the app's `hello` names the ids it still waits for (`waiting`) and gets them again after `ready`,
whose `lost` lists the ones this PC doesn't know (it restarted): the app then says to check on the PC before asking again. Inside the channel: `ask`/`stop`; `get`/`post` for `PHONE_GET`/`PHONE_POST` only (never settings, keys or
data); `event` mirrors every `emit` log line and state (`PhoneLink.put` sits in `clients`); `voice`/`audio`/`barge` make
the phone the microphone and speaker of the PC's one `Live` session (`jarvis.PhoneVoice`: `Speaker.remote` gets the
voice, `voice_loop` stops feeding the PC's mic, half-duplex always; the PC's own wake word takes the floor back, and a
wake-word start is refused while the PC is listening; `_watch_floor` tells the phone when `PhoneVoice.over`); `wake`
sends openWakeWord's three ONNX models in `CHUNK`s. `Live.phone_at` keeps talk from the phone from counting as `at_pc`.
In the app, `App.kt`'s `Jarvis` object owns the link, microphone (`Mic`), voice (`Player`) and state for both the
activity and `JarvisService` (a foreground service: `microphone` type only when started with the app on screen, so
after a reboot the wake word waits for the app to be opened); `Wake.kt` is a port of openWakeWord's streaming features
(`WakeTest` checks it number for number against `evals/wake_vector.py`'s vector, given `WAKE_MODELS`); `Gemini.kt` is
the phone alone with the user's key (Gemini Live over a raw WebSocket) when the PC can't be reached. The PC signs its relay login with its key (the id is that key's hash); the app trusts the PC's other key from
the pairing QR and runs the handshake in `phone.py`'s docstring (P-256 ECDH, HKDF, AES-GCM with counter nonces). The app's UI is
Jetpack Compose (`Screens.kt` takes plain state, so `ScreensTest`'s Paparazzi renders it with made-up data:
`./gradlew recordPaparazziDebug`). The Python and Kotlin sides must stay byte-compatible: `android/app/src/test/resources/handshake.json` is checked by both
`test_jarvis.py` and the app's `HandshakeTest` (`./gradlew testDebugUnitTest`: tests.yml's android job runs them too; `Pairing.parse` refuses links the app couldn't
connect with). Test
the relay locally with `npx wrangler dev` in `relay/`.
