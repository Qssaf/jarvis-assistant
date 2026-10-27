# Privacy

Jarvis runs on your computer. It has no server of its own and collects nothing for its authors. This page says what it
keeps, and what it sends to the services it uses.

## What stays on your computer

In Jarvis's data folder (`~/.local/share/jarvis` on Linux, `%APPDATA%\Jarvis\data` on Windows), readable only by your
user:

- **Memory**: the facts you asked it to remember (editable on the Memory page).
- **Conversations**: what you and Jarvis said, and the agent's working history (the Chats page).
- **Reminders and routines.**
- **Wake word clips**: a few seconds of audio around each "Hey Jarvis", used only on this computer to learn your voice
  (Settings → *Learn my voice*).
- **A log** of what Jarvis did, for troubleshooting.

API keys are kept in your system keychain (or, without one, a file only your user can read). Settings → *Delete
everything Jarvis keeps about me* removes memory, conversations, reminders, routines, voice clips and the log.

## What leaves your computer

- **Google Gemini** (with your Google AI Studio key, under Google's terms): what you say after the wake word (or type),
  your memory and recent conversation as context, screenshots when a task needs the screen, files you ask Jarvis to
  read, and web search questions. Audio before the wake word never leaves your computer.
- **Composio** (only for accounts you connect): the account actions Jarvis runs for you, like reading or sending email.
- **Telegram** (only if you set up *Jarvis on Telegram*): the tasks you send your bot and Jarvis's replies. Only the
  chat you paired is answered.
- **The Jarvis app** (only if you pair a phone): tasks and replies pass through the relay you deploy on your own
  Cloudflare account, end-to-end encrypted: the relay only forwards ciphertext and can't read them.
- **WhatsApp** (only if you link it in Settings): Jarvis runs WhatsApp Web in a hidden browser on this computer, with
  its own profile in the data folder (`whatsapp`). To answer a message it sends that chat's recent messages to the
  agent's models (not your memory or other chats); voice messages and photos you ask about go to the models too. A call
  it picks up or places goes to Gemini Live, which is told only your name and what you want people told; a summary is
  shown to you, and the transcript is kept with the conversation so you can ask about it. The names you put in its
  *Always let through* and *Never answer* lists stay in your settings on this computer (and out of bug reports). Unlink
  in Settings, or from your phone's *Linked devices*.
- **Lecture and meeting notes** (only when you ask for them): what the PC plays, or the room's sound for a class in
  person, is recorded in five-minute pieces, sent to Gemini to be written down, and deleted; the notes are saved in
  `Documents/Jarvis Notes`.
- **Your Google account** (only if you *Sign in with Google* on the Models page): the same as Gemini, through Google's
  Antigravity service. The sign-in is kept in Jarvis's data folder (`google.json`, readable only by your user).
- **Other model providers** you add on the Models page: the same as Gemini, for the jobs you give them.
- **The web**: pages Jarvis reads for you, the weather (Open-Meteo, wttr.in), YouTube and DuckDuckGo searches, and an
  update check that reads Jarvis's version from GitHub.
- **Bug reports** are never sent by themselves: *Copy a report* puts one on your clipboard, with what you said, tool
  arguments, WhatsApp messages, names and numbers, tasks from your phone, email addresses and link parameters removed,
  for you to look over and paste.

## Safety

Jarvis treats web pages, emails and the screen as information, never as instructions. With *Ask before risky actions*
on (the default), commands that delete, install or shut down, and changes to your accounts, wait for your yes.
