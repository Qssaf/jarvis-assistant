# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
./install.sh                          # Linux: .venv (uv, Python 3.13), deps, `jarvis` launcher, app-menu entry
.venv/bin/python test_jarvis.py       # all self-checks; prints "ok" (Windows: .venv\Scripts\python)
.venv/bin/python -m pyflakes *.py     # lint (CI runs it and the tests on Linux and Windows)
.venv/bin/python jarvis.py --no-voice # run without the microphone; the window opens
jarvis --listen                       # tell a running instance to start listening (--region: ask about a dragged area)
jarvis --task "..." / --say "..."     # have it do a task (prints the reply) or say something; jarvis --mcp: the same as an MCP server
EVAL_MODELS="aistudio gemini-3.8-flash low" .venv/bin/python evals/agent_eval.py [case ...]  # agent eval (spends model requests)
.venv/bin/python evals/voice_eval.py [case-prefix ...]   # ~150 real-life requests to the voice model (one Live session each)
.venv/bin/python evals/whatsapp_eval.py [case ...]       # made-up chats through WhatsApp auto-replies (REPLY_PROMPT)
.venv/bin/python evals/proactive_eval.py [case ...]      # made-up sent messages through people.Tracker's promise prompt
.venv/bin/python evals/wake_eval.py [max clips]          # the user's wake clips through openWakeWord, gated vs every frame (offline)
.venv/bin/python evals/wake_vector.py                    # rewrites the app's WakeTest vector (wake.json) from openWakeWord
(cd android && WAKE_MODELS=$PWD/../.venv/lib/python3.13/site-packages/openwakeword/resources/models ./gradlew testDebugUnitTest)
#   the app's tests (the SDK is in ~/Android/Sdk, named by the gitignored android/local.properties); assembleDebug builds the APK;
#   one class: add --tests '*WakeTest*'; on a phone: ~/Android/Sdk/platform-tools/adb install -r app/build/outputs/apk/debug/app-debug.apk
pyside6-lupdate -no-obsolete qml/*.qml jarvis.py window.py -ts translations/jarvis_<code>.ts  # after changing texts
#   (en: add -pluralonly), translate, then: pyside6-lrelease translations/*.ts
(cd whatsapp-helper && go vet ./... && go test ./...)  # the WhatsApp helper (CI runs it too); one test: go test -run TestRang .
```

- CI (`.github/workflows/tests.yml`) runs lint and tests on Linux and Windows. `release.yml` builds `Jarvis.exe` with
  PyInstaller, starts it headless as a smoke test, compiles `packaging/windows/jarvis.iss` (Inno Setup) into
  `Jarvis-Setup-<version>.exe` (signed only when `WINDOWS_CERT_*` secrets exist), builds the Android APK (release-signed
  with `ANDROID_KEYSTORE_*` secrets, else `-debug`), and a last job attaches the zip, installer and APK to the GitHub
  release when a `v*` tag is pushed. The auto-updater (`update_now`) downloads `Jarvis-windows.zip` and checks the
  asset's `digest`: keep that name. `packaging/aur` is the Arch package (/opt install, per-user venv on first run).
  Pushing a tag publishes a public release: ask first.
- The GitHub repo is private (since 2026-11-13): Jarvis.exe's updater, the AUR package and the source copy's update check
  (raw.githubusercontent.com) can't read it, so they find nothing new; making it public again restores them.
- `evals/agent_eval.py` runs the real `Brain.ask` on real models against simulated tools (nothing on the PC or in
  accounts is touched) and checks the moves the agent made. Run it before and after prompt or tool changes. Keep eval
  harnesses in the repo, not a temp dir.
- `evals/voice_eval.py` types real-life requests to the real voice model with the real prompt, memory and accounts:
  reads run for real, changes and screen/PC actions are simulated behind the real safety gates, and every `store`
  write and `system` action function is patched to raise first. Its transcripts hold personal data: `EVAL_OUT` goes
  outside the repo. Run it after `LIVE_PROMPT` or voice tool changes.

- There's no test framework: `test_jarvis.py` is one script of plain `assert`s run top to bottom, so "one test" means
  running the relevant snippet in `python -c`. It points `XDG_CONFIG_HOME`/`XDG_DATA_HOME`/`APPDATA` at a temp dir
  before importing anything; keep that first so tests never touch real settings, memory or reminders. A run takes
  about 50 s; when it hangs, `timeout -s ABRT 120 .venv/bin/python -X faulthandler test_jarvis.py` prints where.
- `openwakeword` is installed with `--no-deps` (its tflite dependency has no current wheels); don't add it to
  `requirements.txt`.
- Finding the running Jarvis: never `pgrep -f`/`pkill -f` with "jarvis.py" in the pattern (it matches the shell running
  the command, which then kills itself); match `[.]venv/bin/python .../jarvis.py` in `ps -eo pid,args` instead.
  SIGTERM quits it cleanly (exit handlers run); start the installed one again detached with `setsid -f
  ~/.local/bin/jarvis` (environment variables such as `JARVIS_WA_LOG` reach it). Its log is `jarvis.log` in
  `system.DATA` (`~/.local/share/jarvis` on Linux). Restart only when it's idle: check the log's last lines (a reply
  being said, a task, or notes started with no "Your notes on ... are ready" after them: their file holds the transcript
  so far, but the summary and the piece being recorded are lost).
- From `CONTRIBUTING.md`: a bug fix comes with a check that fails without it; nothing personal (names, numbers, emails,
  keys) in code, tests, prompts or commit messages; user-visible changes get a `CHANGELOG.md` line.
- Running a second copy alongside an installed Jarvis: set `JARVIS_HUD_PORT` to another port and point the XDG dirs
  elsewhere, otherwise `main()` finds the running instance and just opens its window.
- In a fresh config dir, write `{}` to `<config>/jarvis/plugins.json` first. Otherwise the default Composio plugin
  starts an OAuth sign-in and opens the user's browser. Set `PYTHON_KEYRING_BACKEND=keyring.backends.fail.Keyring` to
  keep test keys out of the real keychain.
- `jarvis.py` sets `TQDM_DISABLE=1`: tqdm's `\r` bars (model downloads, learning the wake word) used to land mid-line
  and hide `[you]`/`[jarvis]` lines. Older logs still have them: read those with `tr '\r' '\n'` and never drop lines
  containing `%|` (the text after the bar is a real log line).
- Tests should use the real objects (e.g. `jarvis.Speaker()`) rather than hand-made fakes: a fake with an old
  attribute once hid a crash that killed voice after the first wake word. Tests that build `Brain.__new__` or
  `Live.__new__` set the attributes they need by hand (`contents`, `asking`, `quick_tasks` as a dict...): a new
  attribute on those classes usually needs adding there.
- Windows CI runs the same file: a check of a Linux-only path must force it (`system.IS_WINDOWS = False`, then restore),
  and timestamps must stay before the year 3000 (Windows can't format later ones). Its temp folder is a short 8.3 name
  (`C:\Users\RUNNER~1`): compare real paths (a symlinked `TMPDIR` reproduces it here); and nothing makes the XDG config
  folder there (settings live under `APPDATA`): a check writing into it makes it first.
- The test window load fails on any QML warning, and it also checks that every `<rootId>.fn()` a page calls is defined
  in that page (Settings once lost its `set()` and every switch silently did nothing).
- GUI checks without touching the user's screen: `docs/screens.py OUT [page...]` renders pages with made-up data (it
  also makes the README's pictures). Off screen it draws in software, without blur or shadows (MultiEffect); to see
  those, start a hidden compositor (`kwin_wayland --virtual --socket NAME`) and run it with `WAYLAND_DISPLAY=NAME
  QT_QPA_PLATFORM=wayland`. Apps there still register on the session's AT-SPI bus, so accessibility can be tested too.

## Architecture

**Processes and threads.** `jarvis.py` is the entry point. One Qt event loop (tray, notch, window) runs on the main
thread, and everything else runs on daemon threads: the wake-word loop (`voice_loop`), the local HTTP API
(`serve_app`), the reminder and deadline loops, an asyncio loop for Gemini Live (`Live`), and another for MCP
(`Brain.loop`).

**Two models cooperate.**
- `Live` (jarvis.py) holds the Gemini Live voice session. It runs the quick tools itself (`LIVE_TOOLS`, plus direct
  account tools) and hands long jobs to the agent through the non-blocking `do_task` tool.
- `Brain.ask` (brain.py) is the agent loop: `_generate` walks a chain of `(backend, model, thinking)` entries, skipping
  ones that are busy or rate-limited (`Overloaded`/`down_until`, with background probes), but re-raises `BadRequest`.
  Each model is asked on its own thread: one that hasn't answered after `HEDGE[thinking]` s ("minimal", "low" only) gets
  the next one asked beside it and the first answer wins; the slow one's late failure still marks it down. A test that
  stubs `threading.Thread` must let those through (only `probe` is stubbed).
  When none answers it raises `NoModel`; a task's step (`_think`) then waits and asks again (`PATIENCE`) while that's
  `transient`, and at `MAX_STEPS` the model is asked once, without tools, for what's done and what's left.
  Independent calls (accounts, plugins, `PARALLEL_TOOLS`) run in parallel; screen tools keep their order.
- A voice call of a change (`ONCE_TOOLS`, or an account tool that isn't `is_read_action`) goes through `_send_once`: the
  same arguments again before the user speaks are refused (the model re-calls a send right after it worked).
- `Live` has resilience logic that's easy to break: request tracking (`inflight`), session resumption, `_recover`
  and `_relisten` after drops, the `_watch` silence watchdog, and half-duplex mic gating while the speaker plays.
  A tool reply sent with `scheduling="SILENT"` (always for `stop_listening` and `ignore`, the voice's "say nothing" for noise) gets no spoken answer, so the request
  must be cleared (`inflight = None`) or the watchdog reconnects 12 s later and re-asks. Something Jarvis says on its
  own (`announce`: reminders, scheduled tasks, `--say`) waits 25 s instead, and never asks the user to repeat it. Code in `_run`'s `except`
  that schedules a reconnect must read `self.mic` first: the `finally` turns it off before the callback runs.
- Quiet hours (`store.quiet_now`: the `quiet_from`/`quiet_until` schedule or `do_not_disturb`): `announce` says nothing
  unless `loud` (WhatsApp's "always let through" names), and every other unprompted line (`_progress`, a result after the
  session closed, the morning briefing, which waits) checks it too; the chat, notification and phones still get it. The
  agent's question (`ask_from_task`) is then asked only if the user is talking with Jarvis (mic on, or spoke < 2 min ago).
- Away from the PC (`at_pc`: no keyboard/mouse for `AWAY` s by `system.user_idle`, mic off, no talk for 2 min): a
  do_task's result goes SILENT into the session and into `held`; coding jobs' news (`job_done`) too. `presence_pass`
  says `held` in one "While you were away" line once they're back. Agents' questions wait for `at_pc` and take turns
  (`Live.asking`). Reminders, scheduled tasks, checks and `tell` keep their own rules.
- Languages: `language` is the main one, `languages` the others allowed (`store.spoken` names them); the voice, WhatsApp
  calls and auto-replies all follow both. An old `call_language` is read as `languages` until settings are next saved.
- Each batch of quick tool calls has its own `halt` event (`quick_tasks`: task -> halt), passed to `tool_act`;
  `_cancel_quick` sets it and cancels the task. Voice acts check only their halt, agent acts their task's `cancel`
  (Stop, New conversation, `jobs` stop), so cutting the voice off never stops the agent and a superseded
  call's late cancel never stops the new one. Never cancel asyncio tasks from another thread: use `call_soon_threadsafe`.
  A query tool asked again with the same arguments while the first is still running (noise "interrupting" makes the
  model re-ask) shares that run's answer (`asked`); a finished one is shared for 3 s at most, never longer (a screen or
  a list may have changed). A voice act that types goes through `_type_once` (shielded, one at a time): the same text
  isn't sent again until the user speaks, and text a cancelled act left in the box isn't typed over it.
- Tasks run side by side (`brain.running`, each a `brain.Task`: its own `contents`, `cancel`, `remote`, `unattended`,
  `passphrase_ok`, `label`). `Brain.ask` gives a task a copy of the conversation and `_join`s its turn back when done:
  the whole trace if no other task joined meanwhile (`joined`), else just what was asked and answered; nothing after
  New conversation (`contents` rebound). A stopped task always answers "Stopped." (never spoken). The screen is the one
  shared thing: a task's first `SCREEN_WORK` tool takes `brain.screen_lock` until the task ends (`_take_screen`), and
  waits while the user has used keyboard or mouse since the task started (+`SCREEN_GRACE`) until `SCREEN_IDLE` s idle;
  the voice's `VOICE_SCREEN_ACTS` take it too, or are refused. `Brain.interrupt` stops every task and returns their
  labels (Stop says them). `jobs` lists or stops them by `Task.n` (a number kept for the task's life), never the task
  calling it (`caller`: its label is the request itself), and only "all" stops every one. A task's `ask_user` lets go of
  the screen while it waits. The voice doesn't start a `do_task` identical to one running (`Live.doing`, `task_key`).
  `code` starts a coding job in a git worktree under `DATA/worktrees` on branch
  `jarvis/<stamp>-<n>`, commits what it changed there and reports through `job_done`; never merges. It answers at once:
  the number is taken under `code_lock`, and the worktree copy and starting OpenChamber happen in `_code_run` (the voice
  gives up after 60 s). `code_jobs` (job number -> worktree, session) lives for the run only. The user's coding agent is OpenChamber (`_chamber_run`): its
  local server's port is `desktopLocalPort` in its own settings.json (`system.app_config`; `openchamber_url(start=True)`
  launches it), and its `/api` is opencode v2's without a password from localhost: `POST /session` {title, location:
  {directory}}, `POST /session/<id>/prompt` {text} (returns at once), `GET /session/<id>` (done when `time.idle` is
  later than the prompt; `outcome`), `GET /session/<id>/message` (newest first: `assistant` items' `content` text/tool),
  `POST /session/<id>/interrupt`. Its permissions are OpenChamber's own settings; a failed or empty poll is retried for
  2 min (`CHAMBER_POLL`). Without it, `HARNESSES` (`claude -p --output-format stream-json`, `acceptEdits` unless safety
  is "full"), with the task on stdin (`run_lines(stdin_text=)`: npm's `claude.cmd` goes through cmd.exe, which splits
  free text at quotes, `&` or a new line). Tests use a fake server: never the real one.
- Task reminders (`task: true`) and the `checks` loop run `Brain.ask(..., unattended=True)` (`run_unattended`): its own
  empty history, and `confirmed` is dropped from every agent call (in `_ask`, not `_run_tool`: the voice
  runs its tools there meanwhile), so nothing that waits for a yes runs. A
  check that answers NOTHING stays quiet; anything else is added to the conversation (`add_turn`, so "yes, do it" from the
  phone has its context) and goes through `tell` (chat, notification, voice, `push` to phones).

**Tools.** Files a tool fetches for the user (`drive_file` with `save_to`, a WhatsApp document) go through `save_file`:
only into `own_folder`s (the home folder, nothing hidden), under a `safe_name`, never over another file.
`brain.TOOLS` maps a name to `(function, description, JSON schema)`. A function returns a dict, or
`(dict, jpeg_bytes)` to attach a screenshot. `briefing`, `classroom_due`, `classroom_announcements`, `drive_file`, `ask_user` and
`account_settings`, `approvals` (entries with `None`) are Brain methods dispatched in `Brain._dispatch` (behind
`_run_tool`'s key guard). Results from outside
sources (`OUTSIDE_CONTENT`, accounts, plugins) get the `UNTRUSTED` note. To add a tool: put it in `TOOLS`, in
`LIVE_TOOLS` if the voice model should run it directly (`QUERY_TOOLS` if its result must be spoken), and in
`TOOL_LABELS` for the notch/chat label. brain.py never imports jarvis.py: what a tool needs from the app is a
module-level one-item list the app fills in `main()` (`asker`, `on_image`, `on_change`, `on_plan`, `on_asked`, `notes_done`, `job_done`), and
Brain fills the model ones (`vision`, `pointer`, `painter`, `grounder`, `notes`).

**Safety in code, not only prompts.** With the `safety` setting on "ask" (the default), risky shell commands
(`RISKY_COMMAND`) and account changes in "ask" mode (`needs_yes`: not `is_read_action`) are refused until the model
passes `confirmed: true` (`with_confirmed` adds it to those schemas; it's stripped before Composio sees it). A plain
`rm` is rewritten to `gio trash` unless `permanent: true`. `launch` (and `act`'s launch step) runs in a shell too, so it
refuses risky commands in "ask" mode (use `run_command`). Every change that runs is logged (`brain.changed` →
`store.log_change`) for `recent_changes` / "undo that".
With a spoken passphrase set (`store.PASSPHRASE`, a secret), a voice `confirmed: true` also needs it in `last_heard`
(`Live._tool`; typed text counts), and an agent task's needs an `ask_user` answer that carried it (`passphrase_ok`;
phone tasks are exempt). `emit` and `ask_user` replace it with `•••`, so it's never in the chat, sessions or log.
`Brain._run_tool` (the real dispatcher is `_dispatch`) refuses a call whose arguments hold a saved key or sign-in token
(`saved_secrets`: keychain provider keys and Telegram, the Google, opencode, plugin and `DATA/mcp` token files; 16+
characters, read again every 30 s) and hides them in every result (`hide_secrets`), for the voice and the agent alike.
Remembered approvals (`store.approvals`, `approvals.json` in CONFIG, never in backups): `needs_yes` skips a slug the user
lifted, and `approvals allow` passes only `may_stop_asking`: the user's latest own words (`user_said`, the app's
`live.last_heard`; a phone task's label; never an unattended task's) say not to ask (`NO_ASK`), name the app
(`APP_WORDS`), and hold the passphrase when one is set (not needed from the phone).

**Wake word.** `wake_word` is a `store.WAKE_WORDS` key or the path of the user's own `.onnx`; `store.wake_phrase` is
what every message tells the user to say. `VoiceLearner` keeps clips and verifier per wake word (`wake_folder`:
"Hey Jarvis" at the folder's root, a custom model by its contents' hash), and `voice_loop` reloads when the word
changes. openWakeWord's verifier score replaces the model's from `custom_verifier_threshold` (0.1) up, so "Only wake
for my voice" raises the score needed (`wake_bar`, `ONLY_ME`), not that threshold (raising it skips verification). `WakeGate` runs the model only while `MicLevel.sound` (and
`WAKE_TAIL` after), keeping its Silero VAD fed on quiet frames (a VAD that missed the gap zeroed sure wake-ups) and
replaying `WAKE_PRE_ROLL` frames when sound returns; `evals/wake_eval.py` replays the user's own clips both ways.

**Models per job.** `MODEL_JOBS` (agent, look, point, point_strong, search, image) each run on `models_for(job)`: the
`<job>_models` setting (lines `"backend model thinking"`) or the built-in list. `_generate` skips entries in
`down_until`; a 429 with `PerDay` pauses that model until the Pacific-midnight reset (`quota_reset_in`), and when every
entry is marked down (a network blip) the first "not answering" one is tried anyway. `count_use` keeps today's requests
per model for the Health page.

**Accounts and plugins.** Plugins are MCP servers (`McpServer`: streamable HTTP with OAuth, or a stdio command). Each
keeps one connection, and concurrent calls open their own. Composio is the default plugin. For connected toolkits,
`APP_TOOLS` slugs are loaded as direct tools via `COMPOSIO_GET_TOOL_SCHEMAS` and run through
`COMPOSIO_MULTI_EXECUTE_TOOL`; `app_data` unwraps Composio's double-wrapped results (None when a call failed: keep
that distinct from "nothing there", as `briefing` and `classroom_work` do). Remote logins are renewed `REFRESH_EARLY`
before they expire: the MCP SDK counts a stored token's lifetime from when it's loaded, and a token refused
mid-connection makes it start a whole new browser sign-in. Only a refresh the server refuses (`rejected`: 400/401/403) may lead to a sign-in tab;
when it's out of reach the old token is kept, and a plugin that couldn't connect for that reason (`unreachable`) is
retried with backoff (it used to stay broken until a restart).

**OS layer.** Everything platform-specific goes in `system.py`, never in the other modules. It picks the best
available tool at call time:
- Audio: PipeWire `pw-record`/`pw-play`, else sounddevice. The mic slider is the user's (calls, Discord): `MicLevel`
  in `voice_loop` brings speech back to ~4000 RMS whatever the slider or card gain (-20..+40 dB, adapting over ~3 s
  of talking, never on Jarvis's own voice), so the wake word, `feed`'s fixed thresholds and Gemini get a steady level.
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

Supported targets are Windows and Linux only (no macOS).

**Screen coordinates.** Models point on a 0–1000 grid (`locate`, `to_pixels`), and `screen_size` updates from every
screenshot. The voice model can't see images, so `act` from voice refuses coordinate clicks: targets are described
(`click_on`) and found by `POINT_MODELS`.

**Prompts.**
- Voice persona: `LIVE_PROMPT` in jarvis.py. The agent's instructions: `prompt.md`.
- Both contain `{SYSTEM}`, replaced at runtime with `system.describe()` (OS-specific hints). Keep them generic:
  nothing about a particular user, machine or distro. `LIVE_PROMPT` also has `{ADDRESS}`, filled from
  `preferred_name(memory)` (the persona otherwise drifts back to "sir"), `{LANGUAGE}` (`language` and `languages`) and
  `{PERSONA}` (`PERSONAS[personality]`). `prompt.md` changes are checked with `evals/agent_eval.py`.
- Messaging on screen relies on `act`'s `expect` step (a vision yes/no that stops the plan) and on `locate` refusing
  near-miss names: together they keep a misheard name from sending a message to the wrong chat.

**Echo cancelling** (`echo_cancel`). On Windows, `system.mic_frames` with a target runs livekit's WebRTC canceller fed
by a soundcard WASAPI loopback of the default speakers (Windows-only requirements), falling back to the plain mic via
`on_source` if it can't start; Health's "Echo cancelling" row says which. On Linux/PipeWire, `start_echo_cancel` loads `module-echo-cancel` in `monitor.mode`, so
the reference is everything the default output plays (games, calls, Jarvis), not only Jarvis's voice; the mic reads
`jarvis-ec-source` (pinned with `node.dont-move`: WirePlumber's "follow the default mic" otherwise moved it onto the raw
mic, and Jarvis heard itself; check with `pw-link -l`) and `Speaker.echo_cancelled` swaps the half-duplex mic gate for a level gate: while Jarvis talks,
`feed` sends silence unless the user is clearly talking (the canceller leaves a faint echo Gemini hears as the user). The module lives as long as its
`pw-cli` process: `atexit` stops it, so a restart must run the exit handlers (`restart_soon` does before `execv`).

**Phone.** `remote.py` long-polls the user's own Telegram bot (token in the keychain as `telegram`) and answers only the
chat paired with the code shown in Settings (five wrong codes and a chat is ignored). Its tasks run `Brain.ask(...,
remote=True)` on their own thread, so `/stop` is still read while one works; `ask_user` refuses (the user can't answer
out loud). Phone tasks run side by side with the others; `/stop` stops them all and says which.
`phone.py` is the Android app's link (`android/`, Kotlin), two ways with one handshake: the PC and the app both dial out to
the user's own relay (`relay/worker.js`, a Cloudflare Worker with one Durable Object per PC that only forwards frames),
and with `phone_direct` the PC also listens on `phone.PORT` (only while a phone is paired or a pairing code shows) for
phones on its own network or VPN: the pairing code and every `ready` carry `system.local_addresses()`, and the app
races them against the relay (`Link.kt`: direct wins). `phones[c]` holds each connection's `send`/`close`, whichever way
it came. Inside the channel: `ask`/`stop`; `get`/`post` for `PHONE_GET`/`PHONE_POST` only (never settings, keys or
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

**WhatsApp.** `whatsapp.py` drives `jarvis-wa` (`whatsapp-helper/`, Go, ~30 MB; it replaced WhatsApp Web in a headless
Chromium, ~1 GB): whatsmeow for messages, and `internal/` is WaCalls' call code (MIT; our changes are listed in its
README: received packets decoded once though every relay forwards them, RFC 3711 rollover guessing, one decode at a
time). They talk JSON lines (`main.go`'s top comment): `WhatsApp.ask(cmd, ...)` waits for `{"id", "ok"|"error"}`,
`tell_call` (`speak`, `hush`, `hangup`) gets no answer, and events (`msg`, `call`, `callstate`, `audio`, `state`, `qr`,
`error`) go to `event` (events carry ids too: only a line without `ev` is an answer). Its stderr goes into Jarvis's
log as `[whatsapp] helper:` (warnings only; `JARVIS_WA_LOG=info` or `debug` for calls or every stanza). whatsmeow
keeps no history, so the helper saves messages (and incoming calls, `rang`: a number that only rang is a chat) in its
own tables of the login's SQLite file (`DATA/whatsapp.db`,
owner-only, never in backups) and asks the phone for earlier ones (`BuildHistorySyncRequest`) when a chat has fewer
than asked for. Chats are keyed by phone-number JID when the LID's is known. "contact" means the name is in
the phone's address book (`FullName`, from app state). Call audio is 16 kHz PCM both ways; Gemini's 24 kHz voice is
resampled and paced in real time by the helper (`speak`: 60 ms MLow frames; the call keeps itself alive with silence).
For an incoming call, a `CallAccept` means the user answered on another device. `helper()` finds the binary next to
Jarvis.exe (release.yml builds it), next to its source (the AUR package), or builds it into `DATA/bin` with `go` when
missing or older than the source (install.sh does too). Auto-replies go through `brain._generate` with only that chat
(no tools, no memory; `{FREE}`: calendar busy times when `whatsapp_share_free`), within `REPLY_LIMIT`/`CHAT_LIMIT` an
hour; a contact's voice message is transcribed on arrival (`_listen`, `HEAR_LIMIT`) and its words saved as its text
(`transcript`); the ids Jarvis sent persist in `whatsapp.json` (`mine`); answered calls are a separate Gemini Live session (`CallSession`). The agent's
`whatsapp_read`/`whatsapp_send` reach it through `brain.whatsapp_link`; sending follows the `whatsapp` account mode and
`confirmed`, and a name must match exactly one chat. What WhatsApp `tell`s the user joins the agent's history
(`add_turn`, with a call's transcript), except rings (`keep=False`): the history is capped at 80 messages. A 2.1 browser
profile (`DATA/whatsapp`) is deleted on start and the user is asked to link again.

**Discord.** `discord.py` drives the user's running Vesktop over Chromium's debugging port (`PORT`, 127.0.0.1): one
`Runtime.evaluate` per call runs `JS` in the page, which uses Vencord's `Vencord.Webpack.Common` stores (`ChannelStore`,
`ReadStateStore`, `RestAPI`, `MessageActions.sendMessage`): the real client, no bot, no copied token. Settings' *Restart
Vesktop* (`system.restart_vesktop`) restarts it with `FLAG`, also written to `vesktop-flags.conf` when the launcher reads
it (Arch) and to Vesktop's own `autostart/vesktop.desktop` (it runs Electron directly, skipping the launcher). `discord_read`/`discord_send`/`discord_react`/`discord_media` resolve names through `brain.pick` (shared with
WhatsApp's `find`); changes follow the `discord` account mode. `Listener` keeps one connection with a `jarvisDiscord`
binding; JS's `listen` subscribes to `MESSAGE_CREATE` (DMs and pings only), re-installed every 30 s (a Discord reload
drops it; `a.v` is the JS's hash). People rules (`<app>_always`/`<app>_never`, `whatsapp.contact_rule`, the
`people_rules` tool) are shared with WhatsApp, and so are `whatsapp.decide` and its limits for the opt-in
`discord_replies` ("friends": friends' one-to-one DMs only). `unsend` (one tool for both apps: the helper's `unsend`
sends whatsmeow's `BuildRevoke`, Discord's JS deletes through `RestAPI`) only takes back the user's own message, the
newest in the chat or the one holding `text`, and is in `ONCE_TOOLS`: a second call would delete the one before it. Jarvis's own replies are known by `(channel, text)` in
`mine` (memory only).

**Search, recordings, learning.** `search_mine` matches every word in the sessions' messages (you, jarvis and the
system notices: WhatsApp and Discord lines), notes files, WhatsApp (the helper's `search` over `jarvis_msgs`, calls left
out), people pages and memory, newest first; screen history apart. `read_file` on an `AUDIO_TYPES` file is
`Notes.from_file`: `system.audio_chunks` (ffmpeg) cuts it into `CHUNK` pieces; one piece's words come back at once, more
are transcribed in order and written up like live notes. Live notes record `both` by default (`system.record_audio`:
two `pw-record`s, the PC's sound and the mic, mixed by `mix_wavs` when each piece stops; "pc" alone once caught only
Jarvis's own voice in a meeting held in the room), start the first piece in `start` (a PC that can't record says so),
and write their file after every piece, named by when they started (`_write`), so a restart keeps the transcript. A voice
`notes` start turns the mic off (the meeting kept the voice answering it). `learn_pass` (every 2 min): once the session's last you/jarvis line is `LEARN_AFTER` old,
`Brain.learn` asks the agent's models once (`LEARN`) for at most three new facts the user said; `learned.json` is
stamped first, so a failing model isn't asked again; `learn_from_talk` turns it off.

**People, promises, attention.** `people.py`: `people.json` holds a page per person (notes with an optional `until`,
`seen`/`wrote` per app from one-to-one WhatsApp and Discord messages via `talked`, which writes at most every 5 min per
person, and `promises`). `Tracker` (`people.tracker[0]`, made in `main()`) takes the user's own outgoing messages (and
WhatsApp sends Jarvis made for them; Discord's come back through `Listener`), keeps only ones `HINT` says talk about
later, and after `wait` seconds asks the agent's models once per burst (`PROMPT`); a promise with a time gets a
reminder, the rest go on the evening list. `evals/proactive_eval.py` checks the prompt. `Brain.person` and
`Brain.waiting_on_me` are the tools (dispatched in `_dispatch`); `evening_digest` (jarvis.py) scans the day's sent
mail, then tells `digest_text(waiting_on_me(listing=True))` once a day; `waiting.json` remembers that list's chats
(`listed`: said apart next time if still waiting) and `skip`'s names (`leave_off`: hidden until a newer message or
promise). `people.meeting` writes a calendar event with its guests matched to pages (`Brain.events` reads them). `Attention` (jarvis.py, `attention.json`): `announce(...,
kind=)` of a kind the user let pass three times in a row (no speech within `HEEDED` s) is only shown for a backoff;
`loud` and `asked` (reminders, scheduled tasks) are never held back. Skills (`store.skills`, the `skill` tool): ways
a screen task worked, offered in `_ask` through `matching_skills`; a task of 3+ screen steps that saved none gets one
`SKILL_NUDGE` (its answer is kept). `activity.py` (opt-in `screen_history`): `system.focused()` every `POLL` s, a line
per change in `DATA/activity/<day>.jsonl`, never in backups.

**State.** `store.py` keeps settings (unknown keys dropped, types coerced, `*_models`, `language`, `safety`... validated),
plugins, `memory.md`, reminders (optionally repeating: `next_time`), routines, the change log and sessions under
`system.CONFIG` / `system.DATA`. Files holding tokens are written with `private=True`. `delete_data` removes everything
personal by its module constants (tests point some of them elsewhere). `export_data`/`import_data` move everything but
secrets in one zip (no keys, logins, WhatsApp profile, phone keys or the pickled verifier: only its clips; paths and
names are checked on import). `tidy` (daily `tidy_loop`) deletes what's older than `keep_days`, and `rotate_log` caps
`jarvis.log` at startup.

**Memory.** `main()` calls `system.lean_memory()` first (glibc `M_ARENA_MAX` 2: ~60 mostly idle threads each kept an arena of freed memory); `system.trim_memory()` (also clears `linecache`: logged tracebacks kept every source file's lines) runs after each agent task, voice session and hourly. `wake_detector` cuts openWakeWord's 10 s `raw_data_buffer` of Python ints to 2 s. The window's QML is built on first `present()` and freed `RELEASE` ms after it's hidden; `Backend` is a `qmlRegisterSingletonType` (a registered instance stays tied to its first engine).

**Background loops.** `background(fn, restart=True)` restarts a loop that dies (voice, reminders, calendar/Classroom
reminders, the user's `checks`, the phone links), with backoff; `system.mic_frames` restarts `pw-record` itself when PipeWire restarts.

**Window and API.** The window is Qt Quick: `window.py` registers a `Backend` QObject as the QML singleton `Jarvis.Backend`
(`qml/*.qml`, theme tokens in `qml/Theme.qml`). QML calls `Api.get/post` → `Backend.request` (thread pool) → `get(path)`/`post(path,
data)`, which map to `api_get`/`api_post` in jarvis.py, and events from `emit()` reach it because `Backend` sits in `clients` (it has
`put()`). Polled values (state, mic level) refresh at 30 fps, only while the window is shown (`Backend.watch`); the notch ticks at 30 fps only while it shows. The look ("glass": tokens in `Theme.qml`, shared pieces
like `Glass`, `Section`, `Chip`, `StatusDot`, the arc reactor in `Orb.qml`) is shared with the phone app's `Theme.kt`.
QML gotchas: the engine loads local files only (`window.LocalOnly`): Qt fetches the pictures in rich text and Markdown by
itself, so a reply's image link could carry data out; a web picture is saved first (`system._web_art` for covers). File paths become URLs through `Backend.fileUrl`/`localPath` (`"file://" + path` broke on Windows); `AbstractButton` has a FINAL `icon` (ours is `symbol`); local
`Label.qml`/`Page.qml` get shadowed by QtQuick.Controls (ours are `Txt`, `ScrollPage`); `#AARRGGBB` colours; font sizes go
through `Theme.px(n)` (the text-size setting, rounded to whole pixels); QtSvg only reads `#rrggbb`; `window.py` forces the
Basic style (Windows' native one ignores custom backgrounds). The first-run `SetupWizard` covers the window until
`setup_done`. `ScrollPage`'s `index: true` (Settings) lists the page's `Section`s beside it (hidden in a narrow window) and
jumps to one; Home's "Working on" (`Today.qml`) polls `/api/jobs` (`brain.running`) and stops one task with
`/api/jobs/<n>/stop`. Every user-visible QML text goes through `qsTr()` (`.arg()` for values, `%n` plurals; Python's tray/notch
texts through `QCoreApplication.translate`); `window_languages` (priority list, `store.WINDOW_LANGUAGES`) installs
`translations/jarvis_<code>.qm` up to the first `en` (`Window.languages`, live `retranslate`). After changing texts run
the lupdate/lrelease commands in window.py's `TRANSLATIONS` comment: the tests check each `.qm` matches its `.ts`. Arabic
mirrors the layout, so place things with anchors, not `x:` (a mirrored anchor against an unmirrored `x` ends up off
screen); `Txt` aligns left by default so mirroring moves it. `docs/screens.py` takes `WINDOW_LANGUAGES="ar"` to render a
language. Never start apps on a private `dbus-run-session` here: its AT-SPI launcher takes over the
session's accessibility socket. Web fetches (`fetch`, the headless browser, `show_image`) go through the `Guard` proxy in brain.py. Over real HTTP,
`serve_app` only accepts `/api/listen`, `/api/show`, `/api/region`, `/api/task` and `/api/say`, and only with the per-run token and a
matching Host header. `/api/task` (`jarvis --task`, `jarvis --mcp`) runs unattended, like a scheduled task.

**Backends.** `AIStudio` (Gemini's native API) plus `OpenAICompatible` for every provider in `brain.providers()`
(built-ins, the user's `providers.json`, Ollama). `Brain.backend(name)` builds them lazily, and `forget_backend` runs
after a key changes. `to_openai`/`from_openai` translate between the Gemini-format history the agent keeps and the
OpenAI chat format; Gemini thought signatures ride along as `thoughtSignature` parts and are only sent to Google hosts.
Keys live in the OS keychain via `store.secret`/`set_secret`, falling back to a 0600 `keys.json`; tests force the file
fallback with `PYTHON_KEYRING_BACKEND`. The voice uses Gemini Live; when Live can't be opened (`Live._fall_back`, retried
after `LIVE_RETRY`) or `always_backup_voice` is on, `Backup` (jarvis.py) takes Live's mic, typed text and announcements:
it cuts requests at a pause, `Brain.hear` writes them down, `Brain.ask` answers, `Brain.speak` (or `system.speech_wav`)
says it. `hear`/`speak` are `MODEL_JOBS` whose failures all move on to the next model (`_speech`, no probes).

**Account modes.** `store.connector_modes()` (connectors.json) holds ask/full/read_only/paused per Composio toolkit.
`account_block` enforces paused and read-only in `run_app_tool`, on `COMPOSIO_MULTI_EXECUTE_TOOL` calls and on WhatsApp
and Discord reads (`WA_READ`, `DC_READ`); `COMPOSIO_MANAGE_CONNECTIONS` may only list or add (disconnecting is the
Accounts page's); a backup's import keeps each account's stricter mode;
`is_read_action` is a verb heuristic on the slug, and unknown verbs count as changes. `account_policy()` feeds both
prompts.

**Google sign-in.** The `antigravity` backend (brain.py) uses Google accounts signed in from the Models page
(`google_sign_in`: Antigravity's OAuth client, read by `google_client()` from the opencode Antigravity plugin
(`PLUGIN_REPO`, found through `opencode.json` first) or the env file and never committed (GitHub's push protection blocks it), PKCE, a callback on `localhost:51121`, then `loadCodeAssist` /
`onboardUser` for the account's project) plus any from the opencode plugin's `antigravity-accounts.json`. A request asks
each account once at most: a 429 rests that account for that model (`Antigravity.resting`, as long as `limit_info` reads
from the reply; the plugin's `rateLimitResetTimes` count too) and the next one is asked, except
`MODEL_CAPACITY_EXHAUSTED` (no account's fault: not sprayed over the others); a 403 "disabled in this account" rests the
account for good, another 401/403 for 10 min; with every account resting it raises `Overloaded` with `retry_after` (so
no "hi" probe) and sends nothing. Waits follow the Antigravity CLI (`agy_delay`, by `refusals` in a row per account
and model, reset by an answer; never shorter than Google's delay): a 429's rest and a 5xx's `retry_after`. A timeout or
lost connection carries `retry_after` 30 s, a 404 an hour: the CLI never sends "hi" probes, and it has no pacing of
its own, so neither has Jarvis. One account at a time: `idx` (the one that answered last) takes every model's
requests until it can't, and on opencode's accounts it's set to the plugin's `activeIndexByFamily` one whenever that
changes (`followed`), so the two apps aren't on two accounts at once. A refused token refresh is `Overloaded` too, never `BadRequest` (that would stop the
whole model chain).
Opt-in and warned about (Google may suspend accounts used this way). With no account its constructor raises
`LookupError`, so its entries (first in every built-in list) are skipped and Brain says nothing. Tests point
`OPENCODE_ACCOUNTS` and `PLUGIN_CONSTANTS` at temp files.

**Backends in code.** A gitignored `local_backends.py`, imported at the end of
brain.py, may register more classes in `brain.BACKENDS` and prepend entries to the model lists (`LOOK_MODELS`,
`POINT_MODELS`, `SEARCH_MODELS`, `IMAGE_MODELS`).

## Skill plan
Stack: Python 3.13 (core), Qt Quick/QML (window), Go (whatsapp-helper/), Kotlin/Compose (android/), JS Worker (relay/),
Remotion/TSX + Manim (video/: the trailer, see video/README.md)
Always: verification-before-completion, karpathy-guidelines
Stack skills: python-patterns
Chains: feature=brainstorming → writing-plans → test-driven-development (asserts in test_jarvis.py first) →
verification-before-completion → requesting-code-review; bug=systematic-debugging → test-driven-development (a check
that fails without the fix) → verification-before-completion → requesting-code-review; refactor=writing-plans →
test-driven-development → verification-before-completion → requesting-code-review; ui=impeccable → accessibility,
verified with docs/screens.py (one screenshot of the finished state); prompt/tool change=feature chain, verified with
evals/agent_eval.py (and voice_eval.py for LIVE_PROMPT) before and after; video=remotion-best-practices → manim-video → emil-design-eng,
verified with rendered frames (one contact sheet); decision=council →
architecture-decision-records; big work=writing-plans → subagent-driven-development
Sizes: every size runs the full chain; size sets depth only (tiny=brief steps, large=deep steps + subagents)
Overlays: security-checklist (safety gates, secrets, serve_app API, phone handshake, plugin OAuth); search-first (new
integration); claude-api only when code calls Anthropic models
Agents: verification-before-completion→tester, requesting-code-review→code-reviewer (not installed → inline)
Not for this project: cpp-coding-standards, cpp-testing, fastapi-patterns, react-patterns, mysql-patterns,
motion-foundations, motion-advanced, minecraft-architect, web-design-guidelines,
frontend-design
Missing: Go, Kotlin/Compose → vault: none → find-skills if wanted

## Skill notes
- requesting-code-review inline (no reviewer agent, never a Workflow: it burned the user's usage): a full-diff pass after green tests still found 6 real bugs; a whole-codebase pass, area by area with a scratch notes file, found 16; a second full read (every file, a repro or failing check per suspect before any fix) found 13 more; the parts never read before (QML pages, evals, packaging) gave 6 more, one a privacy leak a local HTTP server proved: re-reading pays, and so does probing Qt's own behaviour.
- Tests and evals must stub the real desktop (`system._idle_seconds`, `system.fullscreen`): a full-screen game failed the suite. verification-before-completion includes CI: after a push, check the run really ran and passed (`gh run list`): an unparsable workflow is red with no jobs, unseen for three pushes.
- Evals: the default chain (no EVAL_MODELS) worked when one model was 503; `EVAL_OUT` is a file path; a new change tool must be simulated in voice_eval first (it runs real tools); Live closes with 1006 once the key's daily quota is gone; 1011 "Resource has been exhausted" after ~12 sessions in 15 min is a short window (back in ~10 min; the running Jarvis shares the key); a spoken-reply check must strip "\u200b" (the model "says" it).
- OpenChamber: drive it through its own local `/api` (port in its settings.json); never read its opencode server's password (blocked as credential digging, rightly).
- "Gives up / can't do X / rate limited" reports: read the logs first (`jarvis.log`; for Google accounts also the opencode plugin's `antigravity-logs/` and the accounts file's limits); the causes were code (a model outage killing the task, a tool missing a capability, the plugin saving 503 "No capacity" as a rate limit) more than the prompt or Google.
