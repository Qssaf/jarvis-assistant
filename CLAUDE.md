# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
./install.sh                          # Linux: .venv (uv, Python 3.13), deps, `jarvis` launcher, app-menu entry
.venv/bin/python test_jarvis.py       # all self-checks; prints "ok" (Windows: .venv\Scripts\python)
.venv/bin/python -m pyflakes *.py     # lint (the "local_backends imported but unused" warning is expected)
.venv/bin/python jarvis.py --no-voice # run without the microphone; the window opens
jarvis --listen                       # tell a running instance to start listening
```

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
  attribute once hid a crash that killed voice after the first wake word.
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

**Tools.** `brain.TOOLS` maps a name to `(function, description, JSON schema)`. A function returns a dict, or
`(dict, jpeg_bytes)` to attach a screenshot. `briefing` is dispatched specially in `Brain._run_tool`. Results from
outside sources (`OUTSIDE_CONTENT`, accounts, plugins) get the `UNTRUSTED` note. To add a tool: put it in `TOOLS`,
in `LIVE_TOOLS` if the voice model should run it directly, and in `TOOL_LABELS` for the notch/chat label.

**Accounts and plugins.** Plugins are MCP servers (`McpServer`: streamable HTTP with OAuth, or a stdio command). Each
keeps one connection, and concurrent calls open their own. Composio is the default plugin. For connected toolkits,
`APP_TOOLS` slugs are loaded as direct tools via `COMPOSIO_GET_TOOL_SCHEMAS` and run through
`COMPOSIO_MULTI_EXECUTE_TOOL`; `app_data` unwraps Composio's double-wrapped results.

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
  `preferred_name(memory)` (the persona otherwise drifts back to "sir").
- Messaging on screen relies on `act`'s `expect` step (a vision yes/no that stops the plan) and on `locate` refusing
  near-miss names: together they keep a misheard name from sending a message to the wrong chat.

**State.** `store.py` keeps settings (unknown keys dropped, types coerced, `agent_models` validated), plugins,
`memory.md`, reminders and sessions under `system.CONFIG` / `system.DATA`. Files holding tokens are written with
`private=True`.

**Window and API.** `window.py` doesn't touch the brain directly. It calls `get(path)`/`post(path, data)`, which map
to `api_get`/`api_post` in jarvis.py, and receives events through `emit()` → `clients` queues. Over real HTTP,
`serve_app` only accepts `/api/listen` and `/api/show`, and only with the per-run token and a matching Host header.

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
