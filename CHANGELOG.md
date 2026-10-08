# Changelog

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
