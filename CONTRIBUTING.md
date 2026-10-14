# Contributing

Thanks for helping. Jarvis is a small codebase on purpose: a few Python modules and a Qt Quick window.

## Set up

```bash
./install.sh                       # Linux: .venv (uv, Python 3.13), packages, the `jarvis` launcher
.venv/bin/python test_jarvis.py    # every check; prints "ok" (Windows: .venv\Scripts\python)
.venv/bin/python -m pyflakes *.py  # lint
.venv/bin/python jarvis.py --no-voice  # the window, without the microphone
```

CI runs the same lint and tests on Linux and Windows for every push and pull request.

Prompt or tool changes: run `evals/agent_eval.py` before and after (it uses your models: see its first lines).

## Where things live

| File | What it does |
| --- | --- |
| `jarvis.py` | The app: the voice session (`Live`), reminders and calendar loops, the window's API, the tray |
| `brain.py` | The agent (`Brain.ask`), every tool (`TOOLS`), model backends and fallbacks, accounts and plugins |
| `system.py` | Everything that depends on the OS: audio, screenshots, input, windows, the shell |
| `store.py` | Settings, memory, reminders, routines, sessions, keys |
| `remote.py` | Jarvis on your phone: the Telegram bot link |
| `window.py`, `qml/` | The window (Qt Quick); `Theme.qml` holds the colours |
| `prompt.md` | The agent's instructions (the voice's are `LIVE_PROMPT` in `jarvis.py`) |
| `test_jarvis.py` | Plain `assert`s, run top to bottom |

`CLAUDE.md` has more detail on the architecture and its pitfalls.

## Rules

- **Tests for every change.** For a bug, first a check that fails without the fix. Tests use the real objects, and never
  the user's settings, memory, reminders or keychain (`test_jarvis.py` points everything at a temp folder first).
- **Platform code goes in `system.py`**, never in the other modules. Windows and Linux are supported; macOS isn't.
- **Prompts stay generic**: nothing about a particular user, machine or distro.
- **Nothing personal in the repo**: no names, emails, locations or keys in code, tests, prompts or commit messages.
  Your own model backends go in the gitignored `local_backends.py`.
- **Safety stays in code**, not only in prompts: risky actions are gated by `safety` and the account modes.

## Pull requests

Keep them focused, add a line to `CHANGELOG.md` under a new version, and describe how you checked the change.
