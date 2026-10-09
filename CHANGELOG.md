# Changelog

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
