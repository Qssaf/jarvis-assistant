# Background Jobs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Jarvis runs several jobs at once (voice/typed/phone/scheduled agent tasks and coding jobs handed to Claude Code
or opencode), keeps their news and questions until the user is at the PC, and Stop stops all of them and says what it stopped.

**Architecture:** `brain.Task` holds what used to be per-Brain task state (history, cancel, remote, unattended,
passphrase_ok); `Brain.ask` no longer holds one lock: each task works on a copy of the conversation and joins its turn
back when done. The screen is the one shared resource: `brain.screen_lock`, taken at a task's first screen step (and by
the voice's screen acts), waits for the user to let go of keyboard and mouse. `system.user_idle()` reports how long the
user hasn't touched the PC (Jarvis's own input excluded); jarvis.py holds job news and questions while the user is away.

**Tech Stack:** Python 3.13 stdlib (threading, socket for the Wayland idle protocol, ctypes on Windows), git worktrees,
`claude -p --output-format stream-json`, `opencode run --format json`.

**Spec:** the conversation of 2026-11-02 (user opted out of further questions); decisions below.

**Changed 2026-11-03:** coding jobs go to the user's OpenChamber (its local `/api`), not `opencode run`; Claude Code
is the fallback. See CLAUDE.md (Architecture) for how it's driven.

## Decisions

- Jobs run side by side; only screen work takes turns (`screen_lock`, held from a task's first screen step to its end).
- A task that needs the screen waits while the user is using the PC: input after the task started (+3 s grace) and
  less than `SCREEN_IDLE` (8 s) ago. Jarvis's own input never counts as the user's.
- "At the PC" (`jarvis.at_pc`): keyboard/mouse within `AWAY` (90 s), the mic on, or spoken to within 2 min. Unknown
  idle (no detector) counts as at the PC (old behaviour).
- Job results and job questions wait for `at_pc`; held results come out as one "While you were away: ..." line.
  Reminders, scheduled tasks, checks and WhatsApp/Discord `tell`s keep their current behaviour (my call: changing
  them would silence phone pushes the user relies on).
- Stop (window, tray, phone `/stop`, Telegram `/stop`) stops every task and coding job and says/sends what it stopped.
- A stopped task always answers "Stopped." and is never spoken afterwards.
- `jobs` tool (voice and agent): list, or stop one (by number or words) or all.
- `code` tool (voice and agent): runs `claude` (default when installed) or `opencode` headless in a git worktree
  (`DATA/worktrees/<repo>-<n>`, branch `jarvis/<n>`), commits what it changed there, and reports the diff stat. Never
  merges. A folder that isn't a git repo needs `confirmed: true`. `job` continues an earlier coding job's session.
  Permissions: safety "ask" → `--permission-mode acceptEdits` / opencode without `--auto`; "full" → `bypassPermissions` / `--auto`.
- Long results (> 600 chars) go to the chat in full; the voice says the gist.

## Review Focus

- Two tasks finishing together: each turn joins the history once, in order; New conversation meanwhile drops them.
- Stop while a task waits for the screen, for the user's return, or for an answer: it ends promptly with "Stopped.".
- The user away when a voice task ends: the result is not spoken now, is said once on return, and not twice.
- A coding job whose harness is missing or fails: a clear error, the worktree kept, nothing merged.
- Jarvis typing/clicking must not look like the user being at the PC.

---

### Task 1: system.user_idle, own input, stoppable run_lines

**Files:** Modify `system.py`; Test `test_jarvis.py`

**Interfaces:** Produces `system.user_idle() -> float | None` (inf when the latest input was Jarvis's),
`system.run_lines(args, on_line, cwd=None, timeout=600, halt=None)`.

- [ ] Test: `system._idle_seconds` patched to 5 → `user_idle() == 5`; after a patched `system.click` marks own input
  now, `user_idle() == inf`; `_idle_seconds` → None gives None. `run_lines([python, -c, "print(1); sleep(30)"], ..., halt=ev)`
  returns within 3 s of `ev.set()`.
- [ ] Implement: Wayland watcher (ext_idle_notifier_v1 v2 `get_input_idle_notification`, else v1, 2 s timeout) on a
  daemon thread; GNOME Mutter IdleMonitor via gdbus; X11 `xprintidle`; Windows `GetLastInputInfo`. Decorate
  move_pointer/click/type_text/press_keys/scroll to record `_own_input = [start, end]`.
- [ ] Run tests, commit.

### Task 2: brain.Task, side-by-side tasks, screen lock, jobs tool

**Files:** Modify `brain.py`, `test_jarvis.py`

**Interfaces:** Produces `brain.Task(label="", remote=False, unattended=False)`, `brain.running: list[Task]`,
`brain.screen_lock`, `Brain.ask(text, on_tool, on_thought=None, remote=False, unattended=False, label="")`,
`Brain.interrupt() -> list[str]` (labels stopped), `Brain._run_tool(name, args, task=None)`, `tool_jobs(action, job)`.

- [ ] Tests: two `ask` calls whose backend blocks until both started finish (no global lock); both turns are in
  `contents` afterwards; `interrupt()` returns both labels and both answer "Stopped."; a second task calling `act`
  waits until the first task (holding the screen) ends; with `system.user_idle` → 1 and a task started 10 s ago, the
  screen step waits until it returns 20; `jobs list` numbers running tasks, `jobs stop 1` stops only that one; reset
  during a task leaves the new conversation empty.
- [ ] Implement; move `ask_user` onto Task; update existing tests' `_ask`/`ask_user` call sites.
- [ ] Run tests, commit.

### Task 3: code tool

**Files:** Modify `brain.py`, `test_jarvis.py`

**Interfaces:** Consumes `system.run_lines(halt=)`, `brain.running`. Produces `tool_code(task, folder, harness="",
job="", confirmed=False)`, `brain.HARNESSES`, `brain.job_done = [callable(text)]` (filled by the app).

- [ ] Tests (fake harness = a Python script printing claude stream-json lines and writing a file): in a temp git repo
  the job runs in a new worktree on branch `jarvis/1`, the main checkout is untouched, the change is committed on the
  branch, `job_done` gets the harness's summary and "1 file changed"; `job: "1"` reuses the session id; a non-git
  folder without `confirmed` is refused; Stop kills it and `job_done` isn't called; a missing harness is an error.
- [ ] Implement, run tests, commit.

### Task 4: jarvis.py: parallel do_task, presence, questions queue, Stop summary

**Files:** Modify `jarvis.py`, `remote.py`, `phone.py`, `test_jarvis.py`

- [ ] Tests: two `do_task` calls both start; the voice's `act` is refused while `brain.screen_lock` is held;
  `at_pc` false with idle 300 s and no speech → a finished task's result is held (SILENT response, in the chat) and
  `presence_pass` announces "While you were away" once when idle drops; a second `ask_from_task` waits until the first
  is answered and until the user is at the PC, and Stop ends the wait; `live.stop()` with running tasks announces
  their labels.
- [ ] Implement (`working` becomes a count; drop `task_lock`, `current_task`, `task_screen`, `AGENT_SCREEN_TOOLS`);
  wire `brain.job_done`; remote/phone `/stop` reply what stopped; drop "busy/queued" waits.
- [ ] Run tests, commit.

### Task 5: prompts, docs, evals

**Files:** `jarvis.py` (DO_TASK, LIVE_PROMPT, LIVE_TOOLS, TOOL_LABELS), `prompt.md`, `CHANGELOG.md`, `CLAUDE.md`

- [ ] `agent_eval.py` before/after; add cases: "fix the typo in the readme of my jarvis project" → `code`; "what's
  running?" → `jobs`. Run lint, all tests, one real `claude -p` coding job in a scratch repo.
