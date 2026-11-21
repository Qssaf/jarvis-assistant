# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
./install.sh                          # Linux: .venv (uv, Python 3.13), deps, `jarvis` launcher, app-menu entry
.venv/bin/python test_jarvis.py       # all self-checks; prints "ok" (Windows: .venv\Scripts\python)
.venv/bin/python -m pyflakes *.py docs/*.py evals/*.py  # lint (CI lints *.py only, and runs the tests on Linux and Windows)
.venv/bin/python jarvis.py --no-voice # run without the microphone; the window opens
jarvis --listen                       # tell a running instance to start listening (--region: ask about a dragged area)
jarvis --task "..." / --say "..."     # have it do a task (prints the reply) or say something; jarvis --mcp: the same as an MCP server
jarvis --reset-people-lock            # take forgotten People passwords off (the page's and the secret one for hidden people)
EVAL_MODELS="aistudio gemini-3.8-flash low" .venv/bin/python evals/agent_eval.py [case or kind ...]  # agent eval (spends model requests)
.venv/bin/python evals/voice_eval.py [case-prefix ...]   # ~175 real-life requests to the voice model (one Live session each)
EVAL_RUNS=3 EVAL_OUT=/tmp/x.json ...                     # both: each case three times, transcripts to a file outside the repo
.venv/bin/python evals/whatsapp_eval.py [case ...]       # made-up chats through WhatsApp auto-replies (REPLY_PROMPT)
.venv/bin/python evals/proactive_eval.py [case ...]      # made-up sent messages through people.Tracker's promise prompt
.venv/bin/python evals/learn_eval.py [case ...]          # made-up talks through Brain.learn's LEARN prompt (what's kept)
.venv/bin/python evals/people_eval.py [case ...]         # made-up chats through Brain.profile_of (people.PROFILE_PROMPT)
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
  once landed under the already-released 2.1.0). A release also bumps `versionName`/`versionCode` in
  `android/app/build.gradle.kts` and `pkgver` in `packaging/aur/PKGBUILD` (its tarball sum `SKIP` until the tag exists,
  then `updpkgsums` and `.SRCINFO` again); the next change after a release starts a new `## Unreleased`.
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
  about 100 s; when it hangs, `timeout -s ABRT 300 .venv/bin/python -X faulthandler test_jarvis.py` prints where (120 cut
  off runs that were only slow).
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
- A clean exit ends the log with `--- stopped <time>`, after `[jarvis] stopping: <why>` when the tray's Quit or a signal
  asked for it (`stopping`). A log that just ends was a crash or a kill: look in `coredumpctl list` and the journal.
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
- Home's side column is clock, Now playing, Working on, To do, This PC (pinned in the tests), and the notch and tray
  say "speaking" in the listening cyan: both were changed on an audit's advice and the user had them put back.
- An outside fork was reviewed (2026-11-01) and rejected but for its Windows save retry (`store._swap`, without
  its non-atomic `copyfile` fallback); its plain-HTTP location lookup and approval pop-ups stay out.
- `screen_time` reads QHealth's database (`system.QHEALTH_DB`) read-only (`mode=ro`, 3 s timeout, schema checked by
  `QHEALTH_NEEDS`); `QHEALTH_IDLE` copies QHealth's idle list and drifts if it changes. Never write to its DB or repo.

## Architecture

**Processes and threads.** `jarvis.py` is the entry point. One Qt event loop (tray, notch, window) runs on the main
thread, and everything else runs on daemon threads: the wake-word loop (`voice_loop`), the local HTTP API
(`serve_app`), the reminder and deadline loops, an asyncio loop for Gemini Live (`Live`), and another for MCP
(`Brain.loop`).

Supported targets are Windows and Linux only (no macOS).

**Two models cooperate.** `Live` (jarvis.py) holds the Gemini Live voice session and runs the quick tools itself; long
jobs go to the agent loop, `Brain.ask` (brain.py), through the non-blocking `do_task` tool. brain.py never imports
jarvis.py. What must hold (safety, sending once, not promising what nothing is doing) is a gate in code, not only prompt
text, and `evals/voice_eval.py` mirrors the voice's gates.

**Area notes.** How each part works, and what broke there before, is in `.claude/rules/`. A file there loads by itself
when a file it names is opened with the Read, Edit or Write tool; reached only through `grep`, `sed` or a script, it
doesn't. So before changing an area, Read its notes:

| Notes | Covers | Loads for |
| - | - | - |
| `.claude/rules/voice-and-agent.md` | Live and Brain.ask in detail, context and the work log, tasks side by side, tools, prompts, screen coordinates, search, notes, learning | `jarvis.py`, `brain.py`, `prompt.md`, `evals/agent_eval.py`, `evals/voice_eval.py`, `evals/learn_eval.py` |
| `.claude/rules/safety-and-accounts.md` | the yes gates, the passphrase, saved secrets, approvals, account modes, plugins (MCP, Composio) | `brain.py`, `jarvis.py`, `store.py`, `qml/AccountsPage.qml`, `qml/PluginsPage.qml` |
| `.claude/rules/models.md` | models per job, backends and keys, the Antigravity Google sign-in, `local_backends.py` | `brain.py`, `local_backends.py`, `qml/ModelsPage.qml`, `qml/CostPage.qml`, `qml/HealthPage.qml` |
| `.claude/rules/system.md` | audio and the microphone choice, screenshots, input, idle, accessibility, echo cancelling, the wake word | `system.py`, `atspi_helper.py`, `evals/wake_eval.py`, `evals/wake_vector.py` |
| `.claude/rules/phone.md` | Telegram, the Android app's link and handshake, the relay | `phone.py`, `remote.py`, `android/**`, `relay/**` |
| `.claude/rules/messaging.md` | the WhatsApp helper and calls, Discord through Vesktop, people pages, promises, profiles, attention | `whatsapp.py`, `discord.py`, `people.py`, `whatsapp-helper/**`, `evals/whatsapp_eval.py`, `evals/proactive_eval.py`, `evals/people_eval.py`, `qml/PeoplePage.qml` |
| `.claude/rules/window.md` | Qt Quick and its gotchas, Settings, attachments, translations, what `serve_app` accepts | `window.py`, `qml/**`, `translations/**`, `docs/screens.py` |

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
