# Changelog

## 1.11.0 — 2026-10-15

### Added
- **Lecture and meeting notes**: "take notes of this lecture" records what the PC plays (or the room's microphone, for a
  class in person), transcribes it every five minutes as it goes, and on "stop the notes" writes a summary, key points,
  dates and homework plus the full transcript to Documents/Jarvis Notes, then says it's ready. Silent stretches aren't
  sent (models invent words for silence). Linux (PipeWire).
- **Undo**: everything Jarvis changes (commands that change things, account actions) is logged and shown in Activity;
  "undo that" or "what did you change?" reads the log and reverses it. Files it deletes go to the trash (a plain `rm`
  becomes `gio trash`), so they come back; only "delete permanently" really deletes.
- **Plans**: a long task's steps show in the chat as it starts, so a wrong turn can be stopped early.
- **Text size** (Settings): the whole window's text, from 0.9 to 1.5 times the normal size.
- **A Windows build** for new releases: `Jarvis.exe` in a zip, attached to each GitHub release (built and started
  headless in CI first).

## 1.10.1 — 2026-10-15

### Added
- **A Windows build**: `Jarvis.exe` in a zip, attached to each GitHub release (built and started headless in CI).

### Fixed
- Listening, reminders, the calendar and Classroom checks and the phone link start again by themselves if they ever
  stop (they used to stay stopped until Jarvis was restarted).

## 1.10.0 — 2026-10-15

### Added
- **Personality** (Settings): classic Jarvis (refined, dry wit), friendly (warm and casual) or brief (just the answer).
  What Jarvis does doesn't change, only how it talks.
- **Smart home**: a Home Assistant quick pick on the Plugins page (its MCP address and where to paste a token).

## 1.9.1 — 2026-10-15

### Added
- `evals/agent_eval.py`: 15 real tasks (email, files, Discord, Classroom, Drive, a quiz, a prompt injection, reminders,
  routines...) run by the real agent on your models against simulated tools, checking the moves it makes. Nothing on the
  PC or in your accounts is touched. 15/15 on Gemini 3.8 Flash.

### Changed
- Asking for exactly an action is now the yes for it: "delete the .tmp files in Downloads" deletes them at once instead
  of asking "are you sure?" (and, with no one answering, doing nothing). Vague requests ("clean up my Downloads") still
  ask first. Found by the eval.

## 1.9.0 — 2026-10-15

### Added
- **Jarvis on your phone** (Settings): send tasks from anywhere through your own Telegram bot. Only the chat that sent
  the pairing code is answered (five wrong codes and a chat is ignored); `/stop` stops a task. The agent knows you're
  away: it doesn't ask out loud, and ends with its question instead.

### Changed
- Voice and phone tasks take turns: the agent runs one task at a time.

## 1.8.0 — 2026-10-15

### Added
- **Languages** (Settings): Jarvis speaks and listens for one of 19 languages (Arabic, French, Spanish, Hindi...),
  still expecting English names mixed in.
- **Recall**: "what was that site you told me about?", "what did I ask you yesterday?": past conversations are
  searched, with the lines around the match.
- **Your selection**: "summarise this", "translate what I selected", "explain what I copied" read the selected text
  (or the clipboard).
- **Music**: play/pause, next, previous and what's playing, by voice.
- **Calendar heads-up** (Settings, on): a reminder ten minutes before each Google Calendar event. Moved events move
  their reminder, cancelled ones lose it.
- **CI**: the tests and lint run on Linux and Windows for every push.
- **Delete my data** (Settings → Your data): memory, conversations, reminders, routines, voice clips and the log in
  one go (press twice). Keys, account sign-ins and settings stay.
- `PRIVACY.md` (what stays on the PC and what goes where) and `CONTRIBUTING.md`.

### Fixed
- On Windows, text fields, drop-downs and sliders lost Jarvis's look (Qt's native Windows style ignores it); the window
  now uses Qt's Basic style everywhere. Found by the new Windows CI.

## 1.7.0 — 2026-10-15

### Added
- **Repeating reminders**: "every morning at 8", "every weekday", "every week". Each moves on to its next time when it
  goes off; days Jarvis was off don't pile up.
- **Routines**: "when I say *study mode*, close Discord, open my notes and set a 50-minute timer". Say the name later
  and Jarvis runs the steps. They're listed on the Memory page, where you can delete them.
- **Copy a report** (Health page): version, system, the health checks, settings and the end of the log, with what was
  said, tool arguments, email addresses and link parameters taken out, ready to paste into a bug report. A *Report a
  problem* button opens a new GitHub issue.
- **Updates** (Settings): checks GitHub for a newer version; a clean git checkout updates itself (pull, packages) and
  restarts.

## 1.6.0 — 2026-10-14

### Added
- **First-run setup**: what leaves your PC, the Gemini key (a link to get a free one, checked as you paste it), a live
  microphone meter and wake word sensitivity, the voice, and how careful Jarvis should be. Skippable, and it can be run
  again from Settings. Installs that were already set up don't see it.
- **Health page**: checks the key, the voice model, the microphone, the speaker, screenshots, mouse and keyboard,
  window control, app controls by name, accounts, plugins and each job's models, with what to do about anything red and
  a button to the page that fixes it. Below: each model's requests today.
- **Ask before risky actions** (Settings, on by default): risky shell commands and account changes in *ask* mode wait
  for the user's yes (`confirmed: true`), enforced in code, not only in the prompt.
- **Daily quotas**: a free tier's used-up daily quota now pauses that model until the reset at midnight Pacific (it was
  retried every minute), with a notice; per-minute limits wait as long as Google says.

### Fixed
- Every switch and slider on the Settings page did nothing since 1.5.0 (its save function went with the model lists).
  A test now checks that each page's functions exist.

## 1.5.1 — 2026-10-14

### Fixed
- Saying "that's all" could get a late "Very good" ten seconds after the mic closed (sometimes "Gemini didn't answer
  that"): the goodbye's request stayed open, so the watchdog reconnected and asked again. Ending the conversation now
  closes it.
- A new request said over a screen action stopped the new action too ("act ... error: interrupted" right after "just type
  the message"): the old action's cancel arrived after the new one had started. Each voice action now has its own stop
  signal.
- Talking over Jarvis stopped the background task's screen work, and every screen step it tried after that failed until
  the voice used a tool again. Cutting the voice off now only stops the voice's own actions.
- Focusing or closing a window on KDE said it worked even when no window had that name.
- `forget` with an empty or one-letter text could wipe the whole memory; it now asks for a few words from the note.
- The microphone stream restarts on its own when PipeWire restarts (an update, a new device), instead of Jarvis going
  deaf until it's restarted.
- After a reconnect that dropped the account tools or an expired session, Jarvis kept listening only if it was told to
  again; it now goes on listening, keeping what was said meanwhile.
- Pressing app controls with no app named (the focused one unknown) could press them in another app; it now asks which.
- A Drive file with a long name made of underscores (`Lab_Report_Final_Version_2`) was taken for a file id; names are
  looked up first now.
- The voice picker no longer offers the extended-thinking Live models: their tool calls never reach Jarvis.
- After Stop, a later reminder that went unanswered switched off the voice watchdog for the rest of that session (no
  more idle hang-up or mic timeout); reminders now start fresh, and the watchdog keeps going.
- Stop pressed just as the background task asked you something could still ask it and reopen the mic.
- One network blip marked every model as not answering, so Jarvis refused everything ("no model could answer") until a
  background probe got through, up to minutes later. The first model is now tried anyway (rate limits are still kept).
- Closing a window with an empty name closed every window on X11 and Windows; it's refused now.

## 1.5.0 — 2026-10-14

### Changed
- **A Models page**: pick the models for each job (background tasks, reading the screen carefully, quick looks and clicks,
  the second try at finding a target, web search answers, making pictures), each as an ordered list of drop-downs that
  falls back down the list when one is busy. Jobs you haven't changed show Jarvis's own choice, and "Use Jarvis's choice"
  goes back to it. Providers and API keys moved here from Settings.

## 1.4.5 — 2026-10-14

### Fixed
- A chat message could be sent twice: the check after Return looked before the app had drawn the message, so the voice
  thought it hadn't gone and typed it again. The check now waits a second after a send, the result says the text was
  sent, and the voice never resends unless a careful look shows the text still in the box.

### Changed
- "Reply to this guy" looks at the open chat instead of asking who; without words it says what they wrote and the reply
  it would send, and sends it once you agree (or at once if you said to write whatever). After sending it always says the
  words it sent.

## 1.4.4 — 2026-10-14

### Changed
- **The agent can ask you mid-task.** When it needs something only you can tell it (which of two chats, the words for a
  reply, a yes before deleting), it calls `ask_user`: Jarvis says the question out loud (and in a notification), leaves the
  mic open, and passes your answer back with `answer_task`; the task carries on from where it was. No answer within two
  minutes, or Stop, and it ends with the question instead. In tests it asked in exactly the three tasks that needed it
  and in none of the thirteen that didn't.

## 1.4.3 — 2026-10-14

### Changed
- **A new agent prompt**, chosen by testing: four versions ran 15 whole tasks from real conversations against simulated
  tools and screens (marking 260 emails read through a rate limit, Classroom announcements, Drive notes, sending a
  dictated Discord message to the right one of two similar names, a misheard name, "reply to him" without words, a
  homework question, a prompt injection in an email, an unconnected account, deleting mail). The winner, with worked
  examples, passed all of them in half the time of the old one, which asked before sending dictated messages and went
  looking on screen for apps that weren't connected.
- Jarvis learns from corrections: "never press Check answer" is saved as a one-line lesson in memory that every later
  conversation reads. A fact remembered twice is kept once.
- The voice hands screen jobs it can't plan from one look (forms, several pages, multi-question quizzes, unknown apps)
  to the agent, which sees screenshots, and keeps one- or two-step clicks for itself.
- The voice prompt was checked on the real Gemini Live model with spoken requests: 25 of 25 (1.4.1's prompt: 22).

## 1.4.2 — 2026-10-14

### Changed
- **A new voice prompt**, chosen by testing: ten versions were scored on 27 requests taken from real conversations
  (tool choice, asking before sending invented words, not hanging up on a stray word, careful looks for quiz questions,
  no false "I'm watching your screen", remembering what to call you), on two models. The winner, organised by kind of
  request with short worked examples, passed every check on both; the old prompt failed 3 to 6 of them.
- New `drive_file` tool: reads a Google Drive file by name (Docs, Slides and Sheets as text, PDFs, pictures).
- The weather finds where you live in what Jarvis remembers ("The user lives in ...") before guessing from the network.
- Settings lists the full model catalogue of backends added in `local_backends.py` when they offer one.
- Web and input-permission messages said "Larry"; they say Jarvis.

## 1.4.1 — 2026-10-14

### Changed
- **Pick models instead of typing them**: Settings asks each provider which models your key can use. The agent's models
  are rows of drop-downs (provider, model, thinking) you can reorder, and the voice model is chosen from Gemini's
  real-time models.
- Smarter with accounts: direct tools to mark Gmail read or archive it in bulk, and to read Classroom announcements. The
  voice never says it can't do something an account can do: it hands it to the agent, which never clicks through a website
  for account work.
- Smarter on screen: `look` has a careful mode (the strong model) for solving a question, picking the right answer or
  reading a graph. On quizzes and forms Jarvis only fills in answers, never submits; in chats it only presses Enter after
  typing your words. It no longer claims to be watching the screen.
- Fewer false goodbyes (stray words no longer end the conversation), and banter is answered as banter, not with a lecture.
- `act` launches an app by its menu entry when that's the only match for the name.

### Fixed
- Jarvis called you "sir" when it remembered your name as "my name is ..." rather than "call me ...".
- An `act` step labelled with `type` (`{type: "keys", keys: "Return"}`) typed the label instead of pressing the key.
- Pressing Stop while Jarvis spoke could kill the thread that plays its voice.
- The briefing failed when the weather service returned an error; an image model that answered without a picture ended
  `make_image` instead of trying the next one; selected values in Settings' drop-downs could show the first entry.

## 1.4.0 — 2026-10-09

### Changed
- **A new window**, drawn on the GPU with Qt Quick (QML), in Jarvis's cyan and orange: a rounded frameless window with an
  orb that follows your voice while listening and spins while working, Markdown chat with clickable links and a copy
  button, a Today column, an Activity page with Jarvis's reply speed, and settings that save as you change them.
  Shortcuts: Ctrl+N new chat, Ctrl+1/2 Home/Chats, Ctrl+, Settings, Esc stop.
- Faster: Jarvis starts connecting while you're still saying "Hey Jarvis" (and hangs up if it wasn't a wake-up), keeps the
  line open five minutes after a conversation, reads the screen for the voice with the quickest model, lists windows in one
  call (0.6 s instead of 3.3 s) and has a direct `weather` tool (0.7 s instead of a 7 s shell call). The log is timed.
- New `classroom_due` tool: all courses in one call, with what's been turned in.

### Fixed (security)
- The page reader could be sent to this PC or the local network after six redirects, by DNS rebinding, or through the
  headless browser. Every fetch, redirects and the browser's own requests included, now goes through a guard that checks
  each address once and connects only to public ones.
- A model (talked into it by an email or web page) could lift an account's Read only / Paused limit or disconnect it.
  Models can now only make an account stricter; loosening and disconnecting are on the Accounts page.
- Reminders built from Classroom titles (written by teachers) are read out as quoted text, never as an instruction.
  `read_file` and `ui_controls` results are marked as outside content, and memory can no longer override the Safety rules.
- The data folder is always private (0700), and links in the window only open as http, https or mail.
- Input permission: when the desktop's permission prompt is still unanswered, mouse and keyboard fail fast with a clear
  message instead of hanging for minutes; a failed screenshot says so.
- The fast KDE screenshot helper works after install (the desktop's cache is rebuilt in full).

## 1.3.0 — 2026-10-08

### Changed
- Jarvis understands names better: it matches the name it heard against the names on screen by sound, uses them
  exactly as written there, and asks which one when none clearly fits instead of picking the top or newest chat.
- "Reply to him" without the words: Jarvis reads his newest messages, tells you what he wrote and suggests a reply,
  and sends it once you agree. Messages you dictate are still sent straight away; Jarvis never sends words you didn't
  say or approve.
- Before typing into a chat, Jarvis checks the right one is open: a new `expect` step stops the plan when the screen
  isn't as expected. Clicking a name now needs a clear match, not just the closest one.
- Jarvis uses the name you asked to be called (from what it remembers) instead of slipping back into "sir", and
  remembers names you correct it on.
- The pause that ends your turn is 0.6 s instead of 0.45 s, so pausing mid-sentence cuts you off less (Settings → Pause
  before Jarvis answers).
- When an account can do more than Jarvis's direct tools for it, the voice hands the job to the background agent
  instead of saying it can't.

### Fixed
- Classroom work you already turned in no longer shows up as due: the briefing and "what's due" skip it, deadline
  reminders aren't set for it, and ones set before you turned it in are cancelled. Jarvis can also check your
  submissions directly.
- The briefing said "nothing" for parts it couldn't check (an account that didn't answer): it now says it couldn't
  check, and why when a plugin is waiting for you to sign in again.
- Composio (and other remote plugins) could suddenly open a new sign-in page: an expiring login was handed to a
  connection that outlived it. Logins are now renewed half an hour early, one renewal at a time.

## 1.2.0 — 2026-10-08

### Added
- Browsers and Electron apps that Jarvis opens (Chrome, Brave, Discord, VS Code, Spotify...) now show
  their buttons and fields by name, so Jarvis presses them directly instead of reading the screen. It's about 0.2 s per
  step instead of several seconds.

### Changed
- Asking for the controls of an app that doesn't show them (a browser or Electron app you opened yourself) fails at
  once instead of after 3 seconds, and tells Jarvis to use the screen instead.
- Deleting a conversation, removing a plugin and disconnecting an account ask for a second click instead of a dialog.
- Cleaner window: suggestion cards with a dimmer hint line in equal columns, proper drop-down arrows, two-letter
  account badges, a music note when nothing is playing (and cover art from local players), headers on one line, and
  Chats opens on the newest conversation.

### Fixed
- Voice requests to change accounts named "Google Tasks", "Google Drive" and similar weren't recognised.
- The morning briefing could take a minute when an account didn't answer: each part waited its own 20 seconds.
- Windows: the Start Menu shortcut had an empty icon.
- Searching Chats read every saved conversation twice.
- Starting without a key put the same "add your key" message in the chat five times; now it's said once.

## 1.1.1 — 2026-10-08

### Fixed
- Voice stopped after the first "Hey Jarvis" of every start (the microphone loop crashed on a renamed speaker setting).

## 1.1.0 — 2026-10-08

### Added
- **Your own models**: keys for OpenAI, Anthropic, OpenRouter, Groq, DeepSeek, Mistral, xAI or any OpenAI-compatible
  service, set in **Settings → Models and keys** and kept in the system keychain. Any of them can run the background
  agent.
- **Ollama** for local models, with no key; Settings shows which models it has.
- **Per-account controls** on the Accounts page and by voice: ask before changes, full access, read only or paused,
  plus Reconnect and Disconnect. Paused accounts and changes to read-only ones are refused before anything is sent.
- MIT license.

### Changed
- The Gemini key can be added in Settings; Jarvis starts without one.

## 1.0.0 — 2026-10-08

First public release.

- "Hey Jarvis" wake word (local, learns your voice), real-time voice with Gemini Live, a notch at the top of the
  screen, a tray icon and a native dashboard window.
- Web search, page reading, YouTube, opening links; accounts through Composio; MCP plugins.
- Desktop control: apps and their buttons by name, screen reading, clicking by description, typing, shortcuts and
  windows; a shell for system tasks.
- A background agent for long jobs, plus memory, reminders, a morning briefing, Google Classroom deadline reminders,
  pictures and files.
- Runs on Windows 10/11 and Linux (X11 and Wayland; faster paths on KDE Plasma), with `install.ps1` and `install.sh`.
- Models from a Google AI Studio key, with optional extra backends in `local_backends.py`.
