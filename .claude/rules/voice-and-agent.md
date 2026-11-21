---
paths:
  - "**/jarvis.py"
  - "**/brain.py"
  - "**/prompt.md"
  - "**/evals/agent_eval.py"
  - "**/evals/voice_eval.py"
  - "**/evals/learn_eval.py"
---

# The voice and the agent

Part of this repository's architecture notes (the rest: `CLAUDE.md` and the other files here). Each paragraph is how
that part works and what broke before.

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
- What both prompts are told beyond the conversation (`Live._config`, `Brain._system`): memory, `people.index` (people
  with notes, then the ones talked with in the last `ACTIVE_DAYS`, with their apps: with notes only, the list was empty
  and a misheard name had nothing to match), and `brain.about()` (Jarvis itself: version from `app_version`, the
  window's pages, the models of each job by name, what it does on its own from settings, `system.projects()`: git
  folders up to three levels below home, cached ten minutes). Tests and `agent_eval` stub `system.projects`. The voice's
  honesty gates are code, mirrored in voice_eval: `empty_promise` (after a turn that promises to act later, `PROMISE`,
  with no change that went and no task at work, `_check_promise` sends `EMPTY_PROMISE` once per request and the voice
  puts it right itself) and `tool_limit`'s `VOICE_READ_LIMIT` (`DIGGING`: chat reads and searches past it go to do_task).
  `jobs` with nothing running says what finished lately (`clear` empties it); `backup` is `store.export_data` into home.
  `settings` changes only `OWN_SETTINGS` (never safety, models, the wake word, people's lists), and a `DOES_MORE` value
  waits for `confirmed`. `stand_in` (`whatsapp.stand_ins`, memory only, `STAND_IN_MAX` minutes): one one-to-one chat is
  answered whatever the reply settings, rules and `QUIET` say, as Jarvis (`stand_note` goes under `REPLY_PROMPT`'s own
  rules), `too_many` with `STAND_IN_LIMIT`. A `whatsapp_send` while the link is coming back (`reconnecting`) goes into
  `WhatsApp.outbox` (saved in whatsapp.json, sent by `_flush_outbox` on "connected", dropped and said after
  `OUTBOX_KEEP`; `waiting_or_went` keeps "try now" from sending it twice). A `code` job in a folder with no commit to
  branch from works in place after `small_folder` copied it to `DATA/worktrees/<name>-before-<stamp>` (`KEEP_COPY_DAYS`).
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
`learned.json` is stamped first (`evals/learn_eval.py` checks the prompt: nothing only passed on, taken back, or read off a contact's name), so a failing model isn't asked again (a transient `NoModel`, offline for a moment,
puts the stamp back for `LEARN_TRIES` passes and doesn't stop the loop); each pass logs one `[learn]` line;
`learn_from_talk` turns it off. `brain.pick` matches names as written, then exactly one `plain_name` match (decorated
letters, emoji, accents and marks dropped; "Sam & Lee" isn't "Sam Lee"); near matches are listed, never picked. Looks
leave Jarvis's own window out: `own_window` (window.on_screen) makes `own_note` add `OWN_WINDOW` to `tool_look` and
`screen_yes` (`tool_look(whole=False)` for a dragged region).
