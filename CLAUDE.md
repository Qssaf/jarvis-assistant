# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
./install.sh                          # Linux: .venv (uv, Python 3.13), deps, `jarvis` launcher, app-menu entry
.venv/bin/python test_jarvis.py       # all self-checks; prints "ok" (Windows: .venv\Scripts\python)
.venv/bin/python -m pyflakes *.py     # lint (CI runs it and the tests on Linux and Windows)
.venv/bin/python jarvis.py --no-voice # run without the microphone; the window opens
jarvis --listen                       # tell a running instance to start listening (--region: ask about a dragged area)
EVAL_MODELS="aistudio gemini-3.8-flash low" .venv/bin/python evals/agent_eval.py [case ...]  # agent eval (spends model requests)
```

- CI (`.github/workflows/tests.yml`) runs lint and tests on Linux and Windows. `release.yml` builds `Jarvis.exe` with
  PyInstaller, starts it headless as a smoke test, and attaches the zip to the GitHub release when a `v*` tag is pushed
  (only new releases get a Windows build). Pushing a tag publishes a public release: ask first.
- `evals/agent_eval.py` runs the real `Brain.ask` on real models against simulated tools (nothing on the PC or in
  accounts is touched) and checks the moves the agent made. Run it before and after prompt or tool changes. Keep eval
  harnesses in the repo, not a temp dir.

- There's no test framework: `test_jarvis.py` is one script of plain `assert`s run top to bottom, so "one test" means
  running the relevant snippet in `python -c`. It points `XDG_CONFIG_HOME`/`XDG_DATA_HOME`/`APPDATA` at a temp dir
  before importing anything; keep that first so tests never touch real settings, memory or reminders.
- `openwakeword` is installed with `--no-deps` (its tflite dependency has no current wheels); don't add it to
  `requirements.txt`.
- Running a second copy alongside an installed Jarvis: set `JARVIS_HUD_PORT` to another port and point the XDG dirs
  elsewhere, otherwise `main()` finds the running instance and just opens its window.
- In a fresh config dir, write `{}` to `<config>/jarvis/plugins.json` first. Otherwise the default Composio plugin
  starts an OAuth sign-in and opens the user's browser. Set `PYTHON_KEYRING_BACKEND=keyring.backends.fail.Keyring` to
  keep test keys out of the real keychain.
- The log uses `\r` progress bars on first start (wake-word model downloads), so read it with `tr '\r' '\n'`.
- Tests should use the real objects (e.g. `jarvis.Speaker()`) rather than hand-made fakes: a fake with an old
  attribute once hid a crash that killed voice after the first wake word. Tests that build `Brain.__new__` or
  `Live.__new__` set the attributes they need by hand (`ask_lock`, `remote`, `quick_tasks` as a dict...): a new
  attribute on those classes usually needs adding there.
- Windows CI runs the same file: a check of a Linux-only path must force it (`system.IS_WINDOWS = False`, then restore),
  and timestamps must stay before the year 3000 (Windows can't format later ones).
- The test window load fails on any QML warning, and it also checks that every `<rootId>.fn()` a page calls is defined
  in that page (Settings once lost its `set()` and every switch silently did nothing).
- GUI checks without touching the user's screen: render the window with `QT_QPA_PLATFORM=offscreen` and
  `widget.grab()`, or run apps inside a hidden compositor (`kwin_wayland --virtual --socket NAME`, then start them with
  `WAYLAND_DISPLAY=NAME`). Apps there still register on the session's AT-SPI bus, so accessibility can be tested too.

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
  Independent calls (accounts, plugins, `PARALLEL_TOOLS`) run in parallel; screen tools keep their order.
- `Live` has resilience logic that's easy to break: request tracking (`inflight`), session resumption, `_recover`
  and `_relisten` after drops, the `_watch` silence watchdog, and half-duplex mic gating while the speaker plays.
  A tool reply sent with `scheduling="SILENT"` (always for `stop_listening`) gets no spoken answer, so the request
  must be cleared (`inflight = None`) or the watchdog reconnects 12 s later and re-asks. Code in `_run`'s `except`
  that schedules a reconnect must read `self.mic` first: the `finally` turns it off before the callback runs.
- Each batch of quick tool calls has its own `halt` event (`quick_tasks`: task -> halt), passed to `tool_act`;
  `_cancel_quick` sets it and cancels the task. Voice acts check only their halt, agent acts only the global
  `interrupt_act` flag (Stop / New conversation), so cutting the voice off never stops the agent and a superseded
  call's late cancel never stops the new one. Never cancel asyncio tasks from another thread: use `call_soon_threadsafe`.
- `Brain.ask` holds `ask_lock`: voice and phone tasks take turns over the shared history and screen.

**Tools.** `brain.TOOLS` maps a name to `(function, description, JSON schema)`. A function returns a dict, or
`(dict, jpeg_bytes)` to attach a screenshot. `briefing`, `classroom_due`, `drive_file`, `ask_user` and
`account_settings` (entries with `None`) are Brain methods dispatched in `Brain._run_tool`. Results from outside
sources (`OUTSIDE_CONTENT`, accounts, plugins) get the `UNTRUSTED` note. To add a tool: put it in `TOOLS`, in
`LIVE_TOOLS` if the voice model should run it directly (`QUERY_TOOLS` if its result must be spoken), and in
`TOOL_LABELS` for the notch/chat label. brain.py never imports jarvis.py: what a tool needs from the app is a
module-level one-item list the app fills in `main()` (`asker`, `on_image`, `on_change`, `on_plan`, `notes_done`), and
Brain fills the model ones (`vision`, `pointer`, `painter`, `grounder`, `notes`).

**Safety in code, not only prompts.** With the `safety` setting on "ask" (the default), risky shell commands
(`RISKY_COMMAND`) and account changes in "ask" mode (`needs_yes`: not `is_read_action`) are refused until the model
passes `confirmed: true` (`with_confirmed` adds it to those schemas; it's stripped before Composio sees it). A plain
`rm` is rewritten to `gio trash` unless `permanent: true`. Every change that runs is logged (`brain.changed` →
`store.log_change`) for `recent_changes` / "undo that".

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
mid-connection makes it start a whole new browser sign-in.

**OS layer.** Everything platform-specific goes in `system.py`, never in the other modules. It picks the best
available tool at call time:
- Audio: PipeWire `pw-record`/`pw-play`, else sounddevice.
- Screenshots: KDE `jarvis-shot` helper → spectacle → grim → gnome-screenshot → mss.
- Input: wdotool/ydotool on Wayland, pynput otherwise.
- Windows: kdotool on KDE Wayland, pywinctl otherwise.
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
  `preferred_name(memory)` (the persona otherwise drifts back to "sir"), `{LANGUAGE}` (the `language` setting) and
  `{PERSONA}` (`PERSONAS[personality]`). `prompt.md` changes are checked with `evals/agent_eval.py`.
- Messaging on screen relies on `act`'s `expect` step (a vision yes/no that stops the plan) and on `locate` refusing
  near-miss names: together they keep a misheard name from sending a message to the wrong chat.

**Phone.** `remote.py` long-polls the user's own Telegram bot (token in the keychain as `telegram`) and answers only the
chat paired with the code shown in Settings (five wrong codes and a chat is ignored). Its tasks run `Brain.ask(...,
remote=True)`: `ask_user` refuses (the user can't answer out loud). `Brain.ask_lock` makes voice and phone tasks take turns.

**State.** `store.py` keeps settings (unknown keys dropped, types coerced, `*_models`, `language`, `safety`... validated),
plugins, `memory.md`, reminders (optionally repeating: `next_time`), routines, the change log and sessions under
`system.CONFIG` / `system.DATA`. Files holding tokens are written with `private=True`. `delete_data` removes everything
personal by its module constants (tests point some of them elsewhere).

**Background loops.** `background(fn, restart=True)` restarts a loop that dies (voice, reminders, calendar/Classroom
reminders, the phone link), with backoff; `system.mic_frames` restarts `pw-record` itself when PipeWire restarts.

**Window and API.** The window is Qt Quick: `window.py` registers a `Backend` QObject as the QML singleton `Jarvis.Backend`
(`qml/*.qml`, theme tokens in `qml/Theme.qml`). QML calls `Api.get/post` → `Backend.request` (thread pool) → `get(path)`/`post(path,
data)`, which map to `api_get`/`api_post` in jarvis.py, and events from `emit()` reach it because `Backend` sits in `clients` (it has
`put()`). Polled values (state, mic level) refresh at 30 fps. QML gotchas: `AbstractButton` has a FINAL `icon` (ours is `symbol`); local
`Label.qml`/`Page.qml` get shadowed by QtQuick.Controls (ours are `Txt`, `ScrollPage`); `#AARRGGBB` colours; font sizes go
through `Theme.px(n)` (the text-size setting, rounded to whole pixels); QtSvg only reads `#rrggbb`; `window.py` forces the
Basic style (Windows' native one ignores custom backgrounds). The first-run `SetupWizard` covers the window until
`setup_done`. Never start apps on a private `dbus-run-session` here: its AT-SPI launcher takes over the
session's accessibility socket. Web fetches (`fetch`, the headless browser, `show_image`) go through the `Guard` proxy in brain.py. Over real HTTP,
`serve_app` only accepts `/api/listen`, `/api/show` and `/api/region`, and only with the per-run token and a matching Host header.

**Backends.** `AIStudio` (Gemini's native API) plus `OpenAICompatible` for every provider in `brain.providers()`
(built-ins, the user's `providers.json`, Ollama). `Brain.backend(name)` builds them lazily, and `forget_backend` runs
after a key changes. `to_openai`/`from_openai` translate between the Gemini-format history the agent keeps and the
OpenAI chat format; Gemini thought signatures ride along as `thoughtSignature` parts and are only sent to Google hosts.
Keys live in the OS keychain via `store.secret`/`set_secret`, falling back to a 0600 `keys.json`; tests force the file
fallback with `PYTHON_KEYRING_BACKEND`. The voice always uses Gemini Live.

**Account modes.** `store.connector_modes()` (connectors.json) holds ask/full/read_only/paused per Composio toolkit.
`account_block` enforces paused and read-only in `run_app_tool` and on `COMPOSIO_MULTI_EXECUTE_TOOL` calls;
`is_read_action` is a verb heuristic on the slug, and unknown verbs count as changes. `account_policy()` feeds both
prompts.

**Backends in code.** A gitignored `local_backends.py`, imported at the end of
brain.py, may register more classes in `brain.BACKENDS` and prepend entries to the model lists (`LOOK_MODELS`,
`POINT_MODELS`, `SEARCH_MODELS`, `IMAGE_MODELS`).
