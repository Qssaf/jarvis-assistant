# Changelog

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
