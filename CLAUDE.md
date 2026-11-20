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
EVAL_MODELS="aistudio gemini-3.8-flash low" .venv/bin/python evals/agent_eval.py [case or kind ...]  # agent eval (spends model requests)
.venv/bin/python evals/voice_eval.py [case-prefix ...]   # ~175 real-life requests to the voice model (one Live session each)
EVAL_RUNS=3 EVAL_OUT=/tmp/x.json ...                     # both: each case three times, transcripts to a file outside the repo
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
  Pushing a tag publishes a public release: ask first. release.yml fails a `v*` tag unless `VERSION` in jarvis.py is
  that version and `## Unreleased` in CHANGELOG.md has been renamed `## <version> ` (bump both together first; lines
  once landed under the already-released 2.1.0).
- The GitHub repo is public again (while private from 2026-11-13 the updater, the AUR package and the update check found
  nothing new): every push and tag is visible.
- `packaging/aur`: after changing PKGBUILD run `makepkg --printsrcinfo > .SRCINFO`; the tests fail when `.SRCINFO`'s
  depends, makedepends, optdepends or source differ from PKGBUILD.
- `AGENTS.md` is OpenCode's short copy of these notes (it loads that file instead of this one): a change to the commands
  or rules here needs the same change there.
- `evals/agent_eval.py` runs the real `Brain.ask` on real models against simulated tools (nothing on the PC or in
  accounts is touched) and checks the moves the agent made. Run it before and after prompt or tool changes. Keep eval
  harnesses in the repo, not a temp dir. Cases have a `kind` (`tools`, `solving`: the first try isn't the answer,
  `context`: `turns` that lean on earlier ones, `safety`, `honesty`). The right moves in more than `REQUESTS` model
  requests (a case's own `requests`) is `SLOW`, and doesn't pass. A case's `world` has to answer as a real PC would
  (what a tool saved is in `ls`, what `kwriteconfig6` wrote reads back, `echo` echoes, `grep -B` shows the lines above):
  an agent going round in circles may be a world that printed nothing, or the wrong thing (`shortcut` and
  `ps_unplugged` were), or one that stood still: a look after the change has to show it (`ps_wrong_name`'s `ls` kept the
  old name after `mv`, `discord_send`'s screen kept the old chat after the click: each was 31 requests of "it didn't
  work"). Read the trace and fix the world before the prompt, then take the "before" again. A check can take a fourth
  argument, the world as the agent left it (a microphone left muted, who a message went to: a case with `chat` is a
  small chat app, `chat_step`). A new check is tried on a made-up good trace and a lazy one before it's trusted.
  The default shell answers basics (`basics()`: `ps`/`which`/`env`/`echo`, input tools "command not found"), and a
  chat plan the real `chat_unchecked` refuses shows in the trace as `act refused` (`brain.system.focused` is stubbed
  to the case's first window).
- `evals/voice_eval.py` types real-life requests to the real voice model with the real prompt, memory and accounts:
  reads run for real, changes and screen/PC actions are simulated behind the real safety gates, and every `store`
  write and `system` action function is patched to raise first. Its transcripts hold personal data: `EVAL_OUT` goes
  outside the repo. Run it after `LIVE_PROMPT` or voice tool changes. `ctx_` cases lean on the talk before (`talk`
  seeds it), `solve_` ones aren't answered by the first try; `run_tool` applies `jarvis.tool_limit` as `Live._tool`
  does. Live turns sessions away (1011) after about a dozen in 15 minutes: the case waits `EVAL_WAIT` seconds (600) and
  runs again.

- There's no test framework: `test_jarvis.py` is one script of plain `assert`s run top to bottom, so "one test" means
  running the relevant snippet in `python -c`. It points `XDG_CONFIG_HOME`/`XDG_DATA_HOME`/`APPDATA` at a temp dir
  before importing anything; keep that first so tests never touch real settings, memory or reminders. A run takes
  about 75 s; when it hangs, `timeout -s ABRT 120 .venv/bin/python -X faulthandler test_jarvis.py` prints where.
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
  attribute on those classes usually needs adding there. The file's last section builds a real `jarvis.Live` (its
  `Speaker.play` replaced, `brain.asker` put back) for the request tracking: `_handle`, `_recover`, `_watch`, `_task`.
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

## Working on the live app (from past sessions)

- The installed launcher (`~/.local/bin/jarvis`) runs this checkout's `.venv/bin/python jarvis.py` in a
  `systemd-run --user --scope` unit `app-jarvis-<pid>`: whatever branch is checked out is what the next restart runs,
  and other sessions' uncommitted work may sit in the same checkout (commit only your own files; never revert theirs).
- `prompt.md` is read again on every agent request (`Brain._system`): an edit changes the running Jarvis at once and any
  agent eval that's running. `LIVE_PROMPT` and code need a restart.
- After a change, restart it (when idle, as above) and check it in `jarvis.log` yourself; hand back to the user only
  what needs their phone or another person (scanning the WhatsApp QR, a real incoming call). Check it's running first
  (the log's last line may be from the night before), and wait for the old pid to exit after SIGTERM before `setsid
  -f`: started too early, the new one only opened the old one's window. To restart during notes, wait in the background
  for "Your notes on ... are ready" first.
- A second copy for benchmarks: besides the XDG/port/plugins steps above, `env -u DISPLAY QT_QPA_PLATFORM=offscreen`
  (with `DISPLAY` set, `qt_args` passes `-platform xcb`, which beats the env var and opened real windows), and point
  `brain.OPENCODE_ACCOUNTS` elsewhere: it is a fixed `~/.config/opencode/...` path, not an XDG one, so an "isolated"
  copy still spent a real Google account's request.
- Live checks against the user's real accounts stay read-only: never send a real WhatsApp/Discord message, reply,
  reaction or call to test (dry-run the step before the send); keep requests on the signed-in Google accounts to a few
  pings. The auto-mode classifier blocked probing `brain.Antigravity` directly and building third-party Go code
  unasked: don't route around it.
- The user's own `<job>_models` settings override the built-in lists (`LOOK_MODELS`, `POINT_MODELS`...): read
  `settings.json` before judging a list change by the running app.
- No debugger attaches (`ptrace_scope` 1, no py-spy). Memory of the whole tree: `systemctl --user show
  app-jarvis-<pid>.scope -p MemoryCurrent` (includes page cache); the Python process alone: `/proc/<pid>/smaps_rollup`;
  per-thread CPU: `/proc/<pid>/task/*/stat`; allocations: tracemalloc in a second copy.
- RAM and CPU are a standing concern (1-1.3 GB drew complaints): keep heavy libraries out of the long-lived process
  (the voice verifier trains in its own `jarvis.py --learn-voice` process; day to day `Verifier` scores `verifier.pkl` in
  numpy, so scikit-learn/SciPy never stay loaded), and keep background features cheap (screen history reads only the
  focused window's title).
- Evals: times in cases are relative to now (a fixed "14:00" or "Wednesday" failed in the evening and on other days);
  a new file of personal data goes in voice_eval's `PROTECTED` (an eval once wrote a made-up person into the real
  `people.json`), and anything new agent_eval would read of the user's gets a stand-in (`MEMORY`, `people.index`,
  `store.matching_skills`; a subprocess check in the tests guards it). Fix eval failures by merging rules, not one
  bullet per case (`prompt.md` grew from 8k to 21k characters for nothing, then was merged back to ~15.6k). Known noisy
  cases: `announcements` (wants "physics", gets the course code), `shortcut` (passes about half the runs).
- Scrub ids taken from `jarvis.log` (Drive file ids, course codes, chat ids) before they reach a test, an eval or a
  subagent's brief, as well as names, numbers and emails.
- Test traps: patching `whatsapp.time.sleep` patches every module's `time.sleep` (same module object): end waits with a
  `threading.Timer` that sets an event. Phone checks: `phone_back()` gives a fresh handshake when an earlier block left
  the channel counter stale (AES-GCM `InvalidTag`); `_watch_floor` is cancelled when each `asyncio.run` ends.

**Decisions not to undo** (each was asked for or argued out with the user):
- WhatsApp calls must stay: that's why it's whatsmeow + WaCalls (copied into `internal/`: Go's `internal` packages
  can't be imported from another module), not a messages-only library. Received SRTP is decrypted but its auth tag is
  deliberately not checked (`media/srtp.go` `Unprotect`): relays may re-sign packets with a hop-by-hop key Jarvis
  doesn't have, so checking could mute every call.
- Coding jobs go to OpenChamber, not opencode; set up but not starting, the job fails with a clear error rather than
  quietly switching to Claude Code.
- Antigravity uses the user's own plugin fork (`PLUGIN_REPO`, not on npm; the npm package with a similar name is
  someone else's: never point anyone at it). Pacing follows the Antigravity CLI: a 10-a-minute cap was built and
  removed on request; no "hi" probes, one account at a time. Never tune it to look like Google's client or to dodge
  enforcement. The `antigravity gemini-4-hydrogen-sonar` route is kept though Google's app shows it "Unavailable".
- Declined: small jobs on a local Ollama model, Discord calls, switching to or merging OpenJarvis (ideas only),
  Langfuse (the Cost page stays local), a confirm step in phone pairing, routing typed chat straight to the agent (it
  would break typed answers to the voice's questions).
- WhatsApp auto-replies default to "contacts" (drafts were the default and the user removed that: "I want jarvis to
  have some freedom"): don't make defaults stricter without asking. The phone is meant to work anywhere over the
  user's relay; direct is an extra.
- `Brain.person` and `waiting_on_me(skip=)` take a lone near match on purpose (`person("sam")` finds "Sam Lee", pinned
  in the tests); sending never does (`brain.pick` only lists them).
- An outside fork was reviewed (2026-11-01) and rejected but for its Windows save retry (`store._swap`, without
  its non-atomic `copyfile` fallback); its plain-HTTP location lookup and approval pop-ups stay out.
- `screen_time` reads QHealth's database (`system.QHEALTH_DB`) read-only (`mode=ro`, 3 s timeout, schema checked by
  `QHEALTH_NEEDS`); `QHEALTH_IDLE` copies QHealth's idle list and drifts if it changes. Never write to its DB or repo.

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
  `transient`, and at `MAX_STEPS` the model is asked once, without tools, for what's done and what's left. A reply with
  no text and no call is asked again (three in a row: the task says it got no answer, never "Done."). A task that
  fails after steps ran keeps them (`Task.failed` ends its history, joined by `ask`), and the error names what ran.
  Independent calls (accounts, plugins, `PARALLEL_TOOLS`) run in parallel; screen tools keep their order.
- A task's steps go through `Progress`: every `CHECKPOINT_EVERY` steps, and on a stall signal (3 steps all `failed`, a
  step whose non-`blind` calls all repeat an earlier `outcome`, 5 run_commands in a row), `_ask` appends a `checkpoint`
  note (goal + `Task.plan`, which `plan` now keeps) to that step's tool results, and the next step runs `deeper`: one
  thinking level up (`one_up`), hedged at twice its level's HEDGE; a model that 400s the raised level is asked as listed
  and kept in `refused_levels`. Gate refusals (`refused`: "not run:"/"NOT DONE") are neither failures nor stall signals.
  `_generate(agent=True)` (task steps only) sorts `is_lite` entries last and never hedges into one (looks, points and
  search keep lite-first racing); a step a lite entry answers `notify`s once per model per day (`lite_told`). Jarvis's
  own notes in a task start with `NOTE`, and `trim` never cuts there; `LESSON_NUDGE` follows a task with 2+ real
  failures, no remember/skill and an answer that isn't a question. A voice task's turn has the talk first and the
  voice's summary after it, named as one (given the summary first, "at 5" was sent where the user said half past six).
  Tests building `Brain.__new__` that reach agent steps set `lite_told` and `refused_levels`.
- A voice call of a change (`ONCE_TOOLS`, or an account tool that isn't `is_read_action`) goes through `_send_once`: the
  same arguments again before the user speaks are refused (the model re-calls a send right after it worked), and so is
  one whose first answer never reached the model (`told`, set when `_quick` delivers): a cut-off call still finishes
  (shielded), so `_quick` answers it "NOT stopped", never "cancelled" (only an act that types nothing really stops). It went only
  if `call_error` finds no failure (an email that failed inside Composio's result was "just done" on the second try, and
  the user was told it was sent); one that failed twice isn't tried a third time.
  A result is SILENT after Gemini spoke only for a change that worked: reads (`QUERY_TOOLS`, account reads) and errors are said.
- Context: `recent_talk` is the conversation as both models get it ("HH:MM who: text", newest last; notices only from
  the last `NOTICE_KEEP`). `_config` puts it in the voice's prompt; a do_task passes it as `Brain.ask(context=)` (its
  task text is the voice's summary: the user's words win); people's messages and calls shown while a session is open go
  in as `Live.notice` (client content, `turn_complete=False`, at a quiet moment or before the next request). The work log:
  one line per finished tool call (`work_line`: keys and passphrase hidden, <= 180 chars) in `sessions.current["work"]`
  via `log_work`, never a chat message; the voice's from `Live._answer` (conversation id taken before the call), tasks'
  through `brain.on_done`, only while `self.contents is task.base`, under `history_lock` as `_join`; `recent_talk` merges
  the last `WORK_KEEP` of them by time: the newest are sure of a quarter of the limit (`WORK_SHARE`: a long talk fills
  whatever it's given, and left room for one of them or none), older ones take the room the talk leaves; nothing
  `log_work` does may fail the call. At
  startup `pick_up` makes the newest conversation current again (`Sessions.resume(RESUME_WITHIN)`, newest file by
  mtime, checked by `_readable`) unless the user ended it with New conversation (`sessions/left` holds that id). A voice
  `whatsapp_send`/`discord_send` to someone the user didn't name while they're talking with someone else there is
  refused once (`wrong_person`), a different second message to the same chat for one request always (`sent_to`), and
  typed text is never `ignore`d. After `VOICE_TOOL_LIMIT` tools for one request the voice is told to stop and say
  what's in the way and hand the job to do_task, and after `VOICE_COMMAND_LIMIT` `run_command`s to hand the digging to
  do_task (`tool_limit`, a pure function). `repeat_call`/`note_call` (pure, mirrored in voice_eval's `run_tool`) refuse a
  voice call identical to one since the user spoke: a read once its answer reached the model (`told`) and within
  `READ_FRESH`, a call that failed twice, a change that went (`REPEATABLE`: media); `forget_reads` drops the reads on any
  change (the voice's, a task's via `note_change`), a do_task result, a notice, an unprompted `_send` or a session opened
  without resumption. `CHANGING_ARGS` make a read a change and `READING_ACTIONS` a list a read (`jobs list` after a stop); `call_error` sees
  Composio's failure inside the result text. A call a gate refuses is logged (`[voice] <tool> refused:`): it ran
  nothing, so no `[tool]` line said why the voice stopped. A tracked `_send` (a picked region, an announcement) starts
  a new tool count. `evals/voice_eval.py`'s cases can seed the chat (`talk`) and mirror those gates.
- `Live` has resilience logic that's easy to break: request tracking (`inflight`), session resumption, `_recover`
  and `_relisten` after drops, the `_watch` silence watchdog, and half-duplex mic gating while the speaker plays.
  `_recover` and the watchdog stand back only for the request's own work (`_own_work`: a quick tool running, or a
  do_task this request started, kept in `inflight["tasks"]`), never for another request's task; quick tools whose
  answers can't be sent because the session closed reopen one and hand them over (`_hand_over`, as `_task` does).
  A tool reply sent with `scheduling="SILENT"` (always for `stop_listening` and `ignore`, the voice's "say nothing" for noise) gets no spoken answer, so the request
  must be cleared (`inflight = None`) or the watchdog reconnects 12 s later and re-asks. A tracked `_send` that isn't an
  announcement clears `announcing`: typed while an announcement was still to be said, the answer was kept out of the
  chat as announced text (and with `speak_typed_replies` off nothing came back at all). Something Jarvis says on its
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
  isn't sent again until the user speaks, and text isn't typed over what's in the box when the act before was cut off
  (`left`) or nothing was said since (a finished act's text is typed again when the user asks).
- Tasks run side by side (`brain.running`, each a `brain.Task`: its own `contents`, `cancel`, `remote`, `unattended`,
  `passphrase_ok`, `label`). `Brain.ask` gives a task a copy of the conversation and `_join`s its turn back when done:
  the whole trace if no other task joined meanwhile (`joined`), else just what was asked and answered; nothing after
  New conversation (`contents` rebound). A stopped task always answers "Stopped." (never spoken). The screen is the one
  shared thing: a task's first `SCREEN_WORK` tool takes `brain.screen_lock` until the task ends (`_take_screen`), and
  waits while the user has used keyboard or mouse since the task started (+`SCREEN_GRACE`) until `SCREEN_IDLE` s idle;
  a task already holding it waits the same way when the user takes them back, then its next call that isn't a look
  (`SCREEN_LOOKS`) is refused once with `MOVED` (a "not run:" gate), and an agent `act` asks `pause` before each step
  and stops when the user moved (it typed on into the window the user had switched to); the voice's `VOICE_SCREEN_ACTS` take it too, or are refused. `Brain.interrupt` stops every task and returns their
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
  free text at quotes, `&` or a new line), or Antigravity when the user names it or `claude` isn't installed (`agy
  --output-format stream-json --mode accept-edits -p=<task>`, `--conversation <id>` to continue: `TASK_FLAG`, since agy
  reads no prompt on stdin; its `init`/`step_update`/`result` events are read in `harness_event`). Tests use a fake server and fake
  commands: never the real ones.
- `check_pass` counts "new since" from the last check that got an answer (`ok` in checks.json), not the last one started.
  checks.json's `found` is what that one found ("" for NOTHING); `/api/checks`'s `last` shows it on Memory, with
  `looking` while a pass (`CHECKS_LABEL`) runs. Memory's Try now (`/api/checks/test`, `try_check`) runs one check at once
  and only shows its answer there. `run_unattended` returns the answer ("" for nothing), None if failed or stopped.
- Task reminders (`task: true`) and the `checks` loop run `Brain.ask(..., unattended=True)` (`run_unattended`): its own
  empty history, and `confirmed` is dropped from every agent call (in `_ask`, not `_run_tool`: the voice
  runs its tools there meanwhile), so nothing that waits for a yes runs. A
  check that answers NOTHING stays quiet; anything else is added to the conversation (`add_turn`, so "yes, do it" from the
  phone has its context) and goes through `tell` (chat, notification, voice, `push` to phones).

**Tools.** Files a tool fetches for the user (`drive_file` with `save_to`, a WhatsApp document) go through `save_file`:
only into `own_folder`s (the home folder, nothing hidden), under a `safe_name`, never over another file.
`brain.TOOLS` maps a name to `(function, description, JSON schema)`. A function returns a dict, or
`(dict, jpeg_bytes)` to attach a screenshot. `briefing`, `classroom_due`, `todo` (`todo_items`: Google Tasks, reminders, promises, Classroom; Home's To do card), `classroom_announcements`, `classroom_materials`, `drive_file`, `ask_user` and
`account_settings`, `approvals` (entries with `None`) are Brain methods dispatched in `Brain._dispatch` (behind
`_run_tool`'s key guard). Results from outside
sources (`OUTSIDE_CONTENT`, accounts, plugins) get the `UNTRUSTED` note. To add a tool: put it in `TOOLS`, in
`LIVE_TOOLS` if the voice model should run it directly (`QUERY_TOOLS` if its result must be spoken), and in
`TOOL_LABELS` for the notch/chat label. brain.py never imports jarvis.py: what a tool needs from the app is a
module-level one-item list the app fills in `main()` (`asker`, `on_image`, `on_change`, `on_plan`, `on_asked`, `notes_done`, `job_done`), and
Brain fills the model ones (`vision`, `pointer`, `painter`, `grounder`, `notes`, `decider`). `decider` is Gemini's
Decisions API (`AIStudio.decide`, yes/no probabilities, no output tokens), used only while the point models include
`aistudio`: `screen_yes` feeds `watch` and `act`'s `expect`, which trust it from `SURE` and ask `pointer` otherwise.

**Safety in code, not only prompts.** With the `safety` setting on "ask" (the default), risky shell commands
(`RISKY_COMMAND`) and account changes in "ask" mode (`needs_yes`: not `is_read_action`) are refused until the model
passes `confirmed: true` (`with_confirmed` adds it to those schemas; it's stripped before Composio sees it). A tool
that changes things isn't risky in its reading forms (`RISKY_BUT_READING`: `systemctl status`, `pacman -Q`, `pip list`,
`crontab -l`; only options that take no value may come before the reading word, so `systemctl -p status stop x` still
asks): a look that needs a yes teaches the model to pass `confirmed` itself. Code handed to an interpreter that deletes, moves or overwrites is risky too (`INLINE_CODE` and `CODE_CHANGES`, two one-pass
patterns over the whole command: `python3 -c "import shutil; shutil.rmtree(...)"` ran unasked, on one line, several, or
in a here-document); code that only reads or works something out still runs. A plain
`rm` is rewritten to `gio trash` unless `permanent: true`. `launch` (and `act`'s launch step) runs in a shell too, so it
refuses risky commands in "ask" mode (use `run_command`). Every change that runs is logged (`brain.changed` →
`store.log_change`) for `recent_changes` / "undo that".
With a spoken passphrase set (`store.PASSPHRASE`, a secret), a voice `confirmed: true` also needs it in `last_heard`
(`Live._tool`; typed text counts), and an agent task's needs an `ask_user` answer that carried it (`passphrase_ok`;
phone tasks are exempt). `emit` and `ask_user` replace it with `•••`, so it's never in the chat, sessions or log.
`Brain._run_tool` (the real dispatcher is `_dispatch`) refuses a call whose arguments hold a saved key or sign-in token
(`saved_secrets`: keychain provider keys and Telegram, the Google, opencode, plugin and `DATA/mcp` token files; 16+
characters, read again every 30 s) and hides them in every result (`hide_secrets`), for the voice and the agent alike.
An agent `act` plan that types and then presses Return in a chat app (`CHAT_APP`: the window in front or the plan's
`app`/`launch`) with no `expect` step before the Return is refused with `CHECK_CHAT` (`chat_unchecked`, in `_ask`'s
`run`, whatever the safety setting; the voice has its own checks in `Live._type_once`). Remembered approvals (`store.approvals`, `approvals.json` in CONFIG, never in backups): `needs_yes` skips a slug the user
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
per model for the Health page. Every backend also records its reply's tokens (`count_tokens` with `gemini_usage` /
`openai_usage`; Gemini Live's per-request `usage_metadata` through `count_live`, WhatsApp calls too) in `usage.json`
(90 days); `cost_report` prices them from `PRICES` (Google's paid tier, dated tiers, per modality) for the Cost page.
Gemini 4 Hydrogen's speed depends on the route (measured 2026-11-20): `antigravity gemini-4-hydrogen-sonar` answers a task
step or a look in about 3 s, `aistudio gemini-4-hydrogen` in 17-25 s whatever the prompt or thinking, so that route has
60 s in `SLOW_ROUTES` (at "low"'s 20 s half its replies were cut off, and the "hi" probes ate its quota). Both are in
`agent_models` only, after aistudio gemini-3.8-flash medium: it refuses "minimal" thinking with a
400, and on the free key it answered in 35-40 s, hit 503s and used its daily quota up in about ten requests (first in
the list it answered 0 of 191 task steps, and each step waited 8 s for it).

**Accounts and plugins.** Plugins are MCP servers (`McpServer`: streamable HTTP with OAuth, or a stdio command). Each
keeps one connection, and concurrent calls open their own. A call that fails is sent again once after reconnecting,
but a change (`call(again=False)`: not `is_read_action`) only when it surely never arrived (`unsent`). `app_data` reads
results whole (`limit=None`; the model's copy is capped at 20,000 characters, and says where it was cut). A list too
long for Composio comes back as a sample plus a file in its own sandbox (`remote_file_info`): nothing here can read it,
so `whole` turns that into an error saying what works (`TOO_LARGE`: less at a time), and `app_data` reads `pageSize`
lists page by page instead. Composio is the default plugin. For connected toolkits,
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
  `preferred_name(memory)` (the persona otherwise drifts back to "sir"; it reads memory line by line, and a name is quoted
  text or capitalised words ending at any other word: "Kai instead of sir" reached people's auto-replies), `{LANGUAGE}` (`language` and `languages`) and
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
hour (sent ones only); with `whatsapp_replies` on "drafts" (opt-in; "contacts" is the default) the reply isn't sent but `tell`s the user (its own Attention kind, `whatsapp_draft`),
after a 💬 line holding it (`wrong_person` reads who from that line); a contact's voice message is transcribed on arrival (`_listen`, `HEAR_LIMIT`) and its words saved as its text
(`transcript`); the ids Jarvis sent persist in `whatsapp.json` (`mine`); answered calls are a separate Gemini Live session (`CallSession`:
`open` connects its voice before `accept`, so a call isn't picked up without one; `_ring` and `dial` take the call under `lock`, one at a time). The agent's
`whatsapp_read`/`whatsapp_send` reach it through `brain.whatsapp_link` (a tool waits `CONNECT_WAIT` for a link that's
coming up, `_need`; `brain.pick` takes a chat's own id too; an auto-reply whose send fails still shows the message,
with `UNSENT`, in Discord's `_answer` as well); sending follows the `whatsapp` account mode and
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
and write their file after every piece, named by when they started (`_write`), so a restart keeps the transcript. A
piece no model could write down is tried again (`PATIENCE`), then its WAV is kept beside the notes (`_keep`); a recorder
ends itself after `RECORD_LIMIT` and at exit (`end_recordings`), so none outlives Jarvis. A voice
`notes` start turns the mic off (the meeting kept the voice answering it), and so does a `mark` (a bookmark: the moment
the request was first heard, `inflight["at"]`, and a label; a ★ line at its place in the transcript, and the summary
prompt, `Notes.SUMMARY` via `_summary_prompt`, asks for a Marked moments part). `learn_pass` (every 2 min): once the session's last you/jarvis line is `LEARN_AFTER` old,
`Brain.learn` asks the agent's models once (`LEARN`) for at most three new facts the user said or "Lesson: ..." lines
(their corrections of how Jarvis works), reading `sessions.since(at, at)`: every conversation changed since the stamp;
`learned.json` is stamped first, so a failing model isn't asked again (a transient `NoModel`, offline for a moment,
puts the stamp back for `LEARN_TRIES` passes and doesn't stop the loop); each pass logs one `[learn]` line;
`learn_from_talk` turns it off. `brain.pick` matches names as written, then exactly one `plain_name` match (decorated
letters, emoji, accents and marks dropped; "Sam & Lee" isn't "Sam Lee"); near matches are listed, never picked. Looks
leave Jarvis's own window out: `own_window` (window.on_screen) makes `own_note` add `OWN_WINDOW` to `tool_look` and
`screen_yes` (`tool_look(whole=False)` for a dragged region).

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

**State.** `store.py` keeps settings (unknown keys dropped, types coerced, `*_models`, `language`, `safety`... validated;
the file holds only values that aren't the default, so changing a default changes it for everyone who kept it),
plugins, `memory.md`, reminders (optionally repeating: `next_time`), routines, the change log and sessions under
`system.CONFIG` / `system.DATA`. Files holding tokens are written with `private=True`. `delete_data` removes everything
personal by its module constants (tests point some of them elsewhere). `export_data`/`import_data` move everything but
secrets in one zip (no keys, logins, WhatsApp profile, phone keys or the pickled verifier: only its clips; paths and
names are checked on import). `tidy` (daily `tidy_loop`) deletes what's older than `keep_days`, and `rotate_log` caps
`jarvis.log` at startup.

**Memory.** `main()` calls `system.lean_memory()` first (glibc `M_ARENA_MAX` 2: ~60 mostly idle threads each kept an arena of freed memory); `system.trim_memory()` (also clears `linecache`: logged tracebacks kept every source file's lines) runs after each agent task, voice session and hourly. `wake_detector` cuts openWakeWord's 10 s `raw_data_buffer` of Python ints to 2 s. The window's QML is built on first `present()` and freed `RELEASE` ms after it's hidden; `Backend` is a `qmlRegisterSingletonType` (a registered instance stays tied to its first engine).

**Background loops.** `background(fn, restart=True)` restarts a loop that dies (voice, reminders, calendar/Classroom
reminders, the user's `checks`, the phone links), with backoff; `system.mic_frames` restarts `pw-record` itself when PipeWire restarts.

**Window and API.** Jarvis's own Qt platform (XWayland for the notch) goes in `qt_args`, never `os.environ` (launched
apps inherited it). The window is Qt Quick: `window.py` registers a `Backend` QObject as the QML singleton `Jarvis.Backend`
(`qml/*.qml`, theme tokens in `qml/Theme.qml`). QML calls `Api.get/post` → `Backend.request` (thread pool) → `get(path)`/`post(path,
data)`, which map to `api_get`/`api_post` in jarvis.py, and events from `emit()` reach it because `Backend` sits in `clients` (it has
`put()`). Polled values (state, mic level) refresh at 30 fps, only while the window is shown (`Backend.watch`); the notch ticks at 30 fps only while it shows. The look ("glass": tokens in `Theme.qml`, shared pieces
like `Glass`, `Section`, `Chip`, `StatusDot`, the arc reactor in `Orb.qml`) is shared with the phone app's `Theme.kt`.
QML gotchas: the engine loads local files only (`window.LocalOnly`): Qt fetches the pictures in rich text and Markdown by
itself, so a reply's image link could carry data out; a web picture is saved first (`system._web_art` for covers). File paths become URLs through `Backend.fileUrl`/`localPath` (`"file://" + path` broke on Windows); `AbstractButton` has a FINAL `icon` (ours is `symbol`); local
`Label.qml`/`Page.qml` get shadowed by QtQuick.Controls (ours are `Txt`, `ScrollPage`); `#AARRGGBB` colours; font sizes go
through `Theme.px(n)` (the text-size setting, rounded to whole pixels); QtSvg only reads `#rrggbb`; `window.py` forces the
Basic style (Windows' native one ignores custom backgrounds). Buttons, switches and chips are `Qt.TabFocus` (Tab reaches
them, a click doesn't move the typing) with `Focus { keyboard: true }` on `visualFocus` and Enter as `click()`; a chip
that's only a label sets `Qt.NoFocus`; `ScrollPage` scrolls a control Tab reached into view. The first-run `SetupWizard` covers the window until
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
fallback with `PYTHON_KEYRING_BACKEND`. A provider may have several (`store.secrets`: one keychain entry, a key per
line; `secret` is the first): `brain.Keys` uses one at a time inside the backend, below the model chain (the one that
answered last stays; `http_error`'s `key=True`, a 429, 401/403 or Gemini's 400 `API_KEY_INVALID`, rests it, per model
for a limit, for all for `KEY_REST` when refused), and the chain only sees `Overloaded` once every key rests. One key
behaves as before. Gemini Live tries each of `gemini_keys()` once per session open (`Live._next_key`,
`brain.live_key`, which WhatsApp's calls follow). The window only ever gets a key's last four characters. The voice uses Gemini Live; when Live can't be opened (`Live._fall_back`, retried
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
Warned about (Google may suspend accounts used this way); not opt-in for opencode's accounts: `google_accounts` uses that
file whenever it exists (enabled ones only; `projectId`-only accounts, added from the plugin's menu, are valid). With no account its constructor raises
`LookupError`, so its entries (first in every built-in list) are skipped and Brain says nothing. Tests point
`OPENCODE_ACCOUNTS` and `PLUGIN_CONSTANTS` at temp files.

**Backends in code.** A gitignored `local_backends.py`, imported at the end of
brain.py, may register more classes in `brain.BACKENDS` and prepend entries to the model lists (`LOOK_MODELS`,
`POINT_MODELS`, `SEARCH_MODELS`, `IMAGE_MODELS`).

## Skill plan
Stack: Python 3.13 (core), Qt Quick/QML (window), Go (whatsapp-helper/), Kotlin/Compose (android/), JS Worker (relay/),
Remotion/TSX + Manim (video/: the trailer, see video/README.md)
Always: verification-before-completion
Stack skills: python-patterns
Chains: feature=brainstorming → writing-plans → test-driven-development (asserts in test_jarvis.py first) →
verification-before-completion → requesting-code-review; bug=systematic-debugging → test-driven-development (a check
that fails without the fix) → verification-before-completion → requesting-code-review; refactor=writing-plans →
test-driven-development → verification-before-completion → requesting-code-review; ui=impeccable → accessibility,
verified with docs/screens.py (one screenshot of the finished state); prompt/tool change=feature chain, verified with
evals/agent_eval.py (and voice_eval.py for LIVE_PROMPT) before and after; video=remotion-best-practices → manim-video → emil-design-eng,
verified with rendered frames (one contact sheet); decision=council →
architecture-decision-records; big work=writing-plans → subagent-driven-development
Overlays: security-checklist (safety gates, secrets, serve_app API, phone handshake, plugin OAuth); search-first (new
integration); claude-api only when code calls Anthropic models
Not for this project: cpp-coding-standards, cpp-testing, fastapi-patterns, react-patterns, mysql-patterns,
motion-foundations, motion-advanced, minecraft-architect, web-design-guidelines,
frontend-design
Missing: Go, Kotlin/Compose → vault: none → find-skills if wanted

## Skill notes
- requesting-code-review inline (no reviewer agent, never a Workflow: it burned the user's usage): a full-diff pass after green tests still found 6 real bugs; a whole-codebase pass, area by area with a scratch notes file, found 16; a second full read (every file, a repro or failing check per suspect before any fix) found 13 more; the parts never read before (QML pages, evals, packaging) gave 6 more, one a privacy leak a local HTTP server proved: re-reading pays, and so does probing Qt's own behaviour. With Ultracode on and the user asking for few subagents, one read-only 4-reader sweep that had to write a repro script per finding gave 28 real ones (fixes inline, each repro rerun).
- Tests and evals must stub the real desktop (`system._idle_seconds`, `system.fullscreen`): a full-screen game failed the suite, and the window load read the desktop's real media player (`canned` in the test now answers `/api/media`). verification-before-completion includes CI: after a push, check the run really ran and passed (`gh run list`): an unparsable workflow is red with no jobs, unseen for three pushes.
- Evals: the default chain (no EVAL_MODELS) worked when one model was 503; `EVAL_OUT` is a file path; a new change tool must be simulated in voice_eval first (it runs real tools); Live closes with 1006 once the key's daily quota is gone; 1011 "Resource has been exhausted" after ~12 sessions in 15 min is a short window (back in ~10 min; the running Jarvis shares the key); a spoken-reply check must strip "\u200b" (the model "says" it). A voice-prompt rule alone fixed a relay case in 2 of 5 runs: run eval cases 3+ times, and back a must-hold behaviour with a code gate (mirrored in voice_eval's simulation).
- OpenChamber: drive it through its own local `/api` (port in its settings.json); never read its opencode server's password (blocked as credential digging, rightly).
- A review that starts from `jarvis.log` pays: tracebacks, `[tool] ... error:` counted by tool, requests with nothing
  within 30 s, and the exchanges before a frustrated request gave 9 of 15 bugs (a typed answer lost behind an
  announcement, auto-reply threads dying at the send). Tests written for code that already works are tried on
  mutations of it in a temp copy before they're trusted (34 tried: one too-loose assert, one bad mutation).
- "Gives up / can't do X / rate limited" reports: read the logs first (`jarvis.log`; for Google accounts also the opencode plugin's `antigravity-logs/` and the accounts file's limits); the causes were code (a model outage killing the task, a tool missing a capability, the plugin saving 503 "No capacity" as a rate limit) more than the prompt or Google.
