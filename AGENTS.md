# AGENTS.md

Jarvis: a voice assistant for the PC. Python 3.13 (core), Qt Quick (window), Go (`whatsapp-helper/`), Kotlin
(`android/`), a JS worker (`relay/`). Linux and Windows; no macOS.

`CLAUDE.md` holds the full notes, one paragraph per subsystem, each a list of past failures. OpenCode loads this file
*instead of* it, so before changing an area read its paragraph there: `grep -n '^\*\*' CLAUDE.md` lists them.

## Commands

```bash
./install.sh                                   # Linux: .venv (uv, Python 3.13), deps, the `jarvis` launcher
.venv/bin/python test_jarvis.py                # every check, about a minute; prints "ok"
.venv/bin/python -m pyflakes *.py evals/*.py   # lint (CI lints *.py only)
.venv/bin/python jarvis.py --no-voice          # the window, without the microphone
(cd whatsapp-helper && go vet ./... && go test ./...)
(cd android && WAKE_MODELS=$PWD/../.venv/lib/python3.13/site-packages/openwakeword/resources/models ./gradlew testDebugUnitTest)
```

- There's no test framework: `test_jarvis.py` is one script of plain `assert`s, top to bottom. "One test" is the
  snippet run with `python -c`. It points `XDG_CONFIG_HOME`/`XDG_DATA_HOME`/`APPDATA` and the keyring at a temp dir
  before importing anything: keep that first. When it hangs, this prints where:
  `timeout -s ABRT 120 .venv/bin/python -X faulthandler test_jarvis.py`
- CI runs the same file on Windows: a check of a Linux-only path forces `system.IS_WINDOWS = False`, then restores it.
- `openwakeword` is installed with `--no-deps`: never add it to `requirements.txt`.
- After changing a text the user sees (QML `qsTr()`, tray, notch): the `pyside6-lupdate`/`pyside6-lrelease` commands
  in `window.py`'s `TRANSLATIONS` comment. The tests compare each `.qm` with its `.ts`.
- A `v*` tag publishes a release, and must match `VERSION` in `jarvis.py` and a `## <version> ` section replacing
  `## Unreleased` in `CHANGELOG.md`. Ask before tagging or pushing.

## Layout

- `jarvis.py` is the entry point: the Qt loop on the main thread, everything else on daemon threads. `Live` there is
  the voice (Gemini Live; its prompt is `LIVE_PROMPT`, its tools `LIVE_TOOLS`); long jobs go to the agent by `do_task`.
- `brain.py` is the agent (`Brain.ask`; its prompt is `prompt.md`), every tool (`TOOLS`), model backends, accounts and
  plugins. It never imports `jarvis.py`: what a tool needs from the app is a module-level one-item list `main()` fills.
- `system.py`: everything OS-specific, and nowhere else. `store.py`: settings, memory, reminders, keys.
  `window.py` + `qml/`: the window.
- A new tool goes in `TOOLS`, in `LIVE_TOOLS` if the voice runs it itself (`QUERY_TOOLS` if its result must be
  spoken) and in `TOOL_LABELS`. One that changes something is simulated in `evals/voice_eval.py` first: that eval
  runs real tools.

## Rules

- A bug fix starts with a check in `test_jarvis.py` that fails without it. Tests use the real objects
  (`jarvis.Speaker()`), not fakes. Those that build `Brain.__new__`/`Live.__new__` set attributes by hand: a new
  attribute on those classes usually needs adding there.
- Nothing personal in code, tests, evals, prompts or commit messages: no names, numbers, emails, keys, nor the user's
  own courses, contacts or file names (logs and eval transcripts are full of them). Prompts stay generic: `{SYSTEM}`
  is filled in at runtime.
- Safety lives in code, not only in prompts (`RISKY_COMMAND`, `needs_yes`, `confirmed: true`). A behaviour that must
  hold gets a code gate, mirrored in `voice_eval.py`'s simulation: a prompt rule alone holds some of the time.
- A change the user can see gets a line under `## Unreleased` in `CHANGELOG.md`.
- Review code inline: no reviewer subagent or workflow (it burned the user's usage).
- UI changes are checked with `docs/screens.py OUT [page...]` (made-up data, never the user's screen). The test's
  window load fails on any QML warning.

## Evals

They spend the user's model quota and are run by hand, never in CI.

```bash
EVAL_RUNS=3 EVAL_OUT=/tmp/a.json .venv/bin/python evals/agent_eval.py [case id or kind ...]  # Brain.ask, simulated tools
EVAL_RUNS=3 EVAL_OUT=/tmp/v.json .venv/bin/python evals/voice_eval.py [case-prefix ...]      # one Live session a case
```

- A change to `prompt.md`, a tool's description or `LIVE_PROMPT`: run the cases it touches before and after, three
  runs each (a case that passes once may fail the next time). `EVAL_VERBOSE=1` prints every call;
  `EVAL_MODELS="aistudio gemini-3.8-flash low"` picks the models.
- `prompt.md` is read again on every request: don't edit it while an agent eval is running.
- `voice_eval.py` reads the user's real accounts (changes are simulated), so `EVAL_OUT` goes outside the repo. The
  harnesses themselves stay in `evals/`.
- An agent going round in circles may be the case's `world` printing nothing, or the wrong thing. Read the trace and
  fix the world before the prompt, then take the "before" again.
- Live closes with 1011 after about a dozen sessions in 15 minutes (the eval waits `EVAL_WAIT`, 600 s) and 1006 once
  the day's quota is gone. The running Jarvis shares the key.

## The running Jarvis

- The user's Jarvis is usually running, from this checkout (`~/.local/bin/jarvis` starts its `jarvis.py`): an edit
  takes effect at its next start. Restart it only when it's idle (`CLAUDE.md` says how to tell).
- Never `pgrep -f`/`pkill -f` with "jarvis.py": the pattern matches the shell running it. Use
  `ps -eo pid,args | grep '[.]venv/bin/python [^ ]*jarvis[.]py'`.
- "It gave up", "it can't do X": read `~/.local/share/jarvis/jarvis.log` first. The cause was code more often than
  the prompt.
- `CLAUDE.md`'s "Working on the live app" lists what past sessions learned (restarting, read-only live checks,
  debugging memory, eval traps) and the decisions not to undo: read it before changing an area it names.
- A second copy off screen also needs `env -u DISPLAY QT_QPA_PLATFORM=offscreen` and `brain.OPENCODE_ACCOUNTS` pointed
  elsewhere (a fixed path: the copy otherwise uses the real Google accounts).
- A second copy, or any run in a fresh config dir: point the XDG dirs elsewhere, set `JARVIS_HUD_PORT`, write `{}` to
  `<config>/jarvis/plugins.json` first (otherwise the default plugin opens a sign-in in the user's browser) and set
  `PYTHON_KEYRING_BACKEND=keyring.backends.fail.Keyring`.
