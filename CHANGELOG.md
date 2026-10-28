# Changelog

## Unreleased

### Added
- **A backup voice:** when Gemini Live can't be used (no key with Live, its quota used up, Google down), Jarvis still
  answers out loud instead of going silent. A model writes down what you said, the agent answers with every tool, and
  a speaking model says it (Gemini's text-to-speech in Jarvis's voice, OpenAI's, or the computer's own voice as a last
  resort). The chat says why it switched, and Gemini Live is tried again five minutes later. Pick the models on the
  Models page (*Hearing you*, *Speaking*); Settings → *Always use the backup voice* is for keys without Live. Health
  says what it would hear and speak with. With `--offline-voice` (`-OfflineVoice` on Windows) at install it can also
  hear with faster-whisper and speak with Piper on your PC, with no service at all. A Speaking line on OpenAI lets you
  pick its voice, and the notch, Home and the tray say when the backup voice is answering.
- **Windows catches up:** *"what's playing?"*, the Today page's music and the play/next/previous buttons work through
  Windows' own media controls; typing sends the whole text at once (fast, with emoji and accents) instead of key by
  key; and **Echo cancelling** now works there too (WebRTC's canceller fed with what the speakers play; experimental,
  and Health says whether it's really on).
- **Move to another computer:** Settings → *Save a backup* puts settings, memory, reminders, routines, checks,
  plugins, account modes, conversations and wake-word clips in one .zip; *Bring one in* restores it and restarts.
  Keys, sign-ins, WhatsApp and paired phones never go in a backup.
- **Edit reminders, scheduled tasks, routines and checks in the window** (Memory page): change, pause, delete or add
  them. The checks list and how often they run moved there from Settings.
- **Keep conversations and logs for…** (Settings → Your data): a week to a year, or forever (the default). Older ones
  are deleted once a day, and the log starts a new file past 5 MB.
- **Update now:** Settings installs a new version for you: a source copy pulls from git and reinstalls its packages
  (it refuses if you changed files or are on another branch); `Jarvis.exe` downloads the release, checks it against
  GitHub's checksum and swaps itself after it closes.
- **Installers:** a Windows installer (`Jarvis-Setup-<version>.exe`, no admin rights; unsigned), the Android app's
  `.apk` attached to every release, and an AUR package for Arch and CachyOS in `packaging/aur`.
- **Set up my relay:** one button in Settings → *The Jarvis app* signs in to Cloudflare, deploys your relay and saves
  its address (needs Node.js).
- **The window in your language:** Settings → *Window language* lists the languages the window, tray and notch use,
  in order of preference: each text comes from the first that has it, and English ends the list. 17 languages besides
  English (machine-translated and checked; corrections welcome), with Arabic laid out right to left and dates in the
  window's language. It changes at once, no restart; English stays the default.
- **Notes say who's talking:** lecture and meeting notes label each speaker (*Speaker 1*, or a name when it comes up)
  consistently across the recording, and the summary says who made each point. One speaker stays unlabelled.

### Fixed
- A spoken passphrase said in the same breath as a request is no longer kept in the saved conversation.

## 2.1.0 — 2026-10-27

### Added
- **Jarvis phones people for you:** *"call dad and tell him I'll be late"* rings them on your WhatsApp; Jarvis waits
  for their hello, gives the message in its own voice, takes their answer and tells you how it went. It never hangs up
  before they've answered.
- **Voice messages and photos on WhatsApp:** *"what did Sam's voice note say?"* transcribes it (with a translation);
  photos are described. Groups can be listed and read too.
- **More than one language:** Settings → Voice → *Also speaks and understands* lets you pick other languages besides
  your main one. Jarvis answers in whichever of them you speak to it in, and never switches to one it only thinks it
  heard. WhatsApp calls and replies keep to the same list (the old *Also speak on calls* choice carries over).
- **Quiet hours and Do not disturb:** set quiet hours (*22:00* to *07:00*) in Settings → Your day, or switch on *Do not
  disturb* there or from the tray menu. Jarvis then doesn't speak up on its own: reminders, scheduled tasks, checks,
  WhatsApp news and *"jarvis --say"* still reach the chat, a notification and your phone, but aren't said out loud. It
  still answers when you talk to it, and the morning briefing waits until quiet hours end. The tray tooltip says when
  it's quiet.
- **WhatsApp people you choose:** Settings → WhatsApp has two lists. *Always let through*: Jarvis never answers their
  messages or picks up their calls, and always tells you about them out loud, even in quiet hours. *Never answer*:
  Jarvis never replies or picks up, and their messages are only shown in the chat.
- **Plugins try again by themselves:** one that can't be reached shows *"Can't reach <host> · trying again in 2 min"*
  and a *Try now* button, instead of staying broken until a restart.
- **Choose the wake word:** Settings → Listening → *Wake word* picks *Hey Jarvis*, *Alexa*, *Hey Mycroft* or *Hey
  Rhasspy*, or *Your own model* (the path of an openWakeWord `.onnx` file you trained; its file name is the phrase Jarvis
  tells you to say). It switches over within seconds, no restart. What Jarvis learns of your voice is kept for each wake
  word on its own, so one never judges another.
- **Only wake for my voice:** a Settings switch that, once *Learn my voice* has learned how you say the wake word, wakes
  Jarvis only when it's sure it's you. Until something is learned, it says so and wakes as before. Talk and push to talk
  always work.
- **A spoken passphrase:** set one in Settings → Listening, and everything Jarvis asks your yes for out loud (sending
  messages, calls, account changes, risky commands) also needs you to say it, so someone else in the room can't. It's
  kept in your keychain, never shown or said back, and hidden in the chat. Tasks from your phone don't need it.

### Fixed
- **Bug reports keep your WhatsApp private:** *Copy a report* left in WhatsApp messages, contacts' names and phone
  numbers, tasks sent from your phone, and every line after the first of a longer reply. They're all taken out now.
- **A signed-out Google account no longer stops everything:** when a Google sign-in (Models page) was revoked or had
  expired, every background task, look and search failed instead of moving on to your AI Studio key. Jarvis now uses
  the next account or model, and tells you to sign in again.
- **Answers to your phone show at the PC too:** tasks sent from the Jarvis app or Telegram showed only the question in
  the chat, never Jarvis's answer, and a conversation held only from the phone was never kept in Chats. Both are in
  the conversation now, marked 📱.
- **WhatsApp rings don't crowd out the conversation:** every "X is calling" was kept in the agent's memory, and a
  dozen of them pushed a whole earlier task out of it. Only what came of a call is kept now, with its transcript, so
  *"did you tell him my address?"* is answered from what was really said instead of a guess.
- **Stray noise isn't answered:** a stray word or another language gets silence instead of *"Yes?"*, but *"huh?"* right
  after Jarvis spoke gets the answer said again.
- **A real yes for things that need one:** after *"Shall I send it?"*, only a clear yes sends it (noise once did), and
  *"sure, no problem"* counts as one.
- **Account outages are called outages:** while Composio is out of reach, Jarvis says your accounts are still connected
  and it keeps trying, instead of telling you to connect Gmail again; a login refresh during an outage no longer opens
  a sign-in tab.
- **"Q" is said as the letter**, not as a word.
- WhatsApp: a page reload no longer takes the link down for three minutes; a call to someone who never picks up gives
  up cleanly; *"call him back"* calls the right person.
- Several saves at once no longer lose a settings change or corrupt a file; copying a picture no longer breaks
  *"summarise what I copied"*; a script interrupting `jarvis --task` no longer fills the log with a traceback, and a
  failed task says it failed instead of *"Jarvis isn't running"*.

## 2.0.0 — 2026-10-24

The first published release since 1.13.3, so it also brings everything from 1.13.4 to 1.14.0 below: the glass
redesign, the Jarvis app for Android, scheduled tasks, keeping an eye on things, Jarvis for scripts and AI agents, and
Jarvis learning the way. New in 2.0:

### Added
- **Jarvis looks after your WhatsApp:** link your own WhatsApp in Settings (like WhatsApp Web, by scanning a code).
  Jarvis answers your contacts' messages that don't need you, saying it's your assistant, and tells you about anything
  urgent; it picks up calls you miss after 20 seconds, talks with the caller in its own voice, takes a message and
  tells you what they wanted. It also reads and sends WhatsApp messages when you ask, without touching the screen.
  It never answers groups or strangers, stays out of chats you're writing in, and sends at most 20 replies an hour.
- **Your mic slider is yours:** Jarvis evens out your voice by itself, so the slider can sit wherever your calls need
  it. Quiet or loud, the wake word and Gemini hear you at the same level (it adapts within a few seconds of talking,
  and never to its own voice).

### Fixed
- **Jarvis hears you again with the mic turned up:** since PipeWire 1.6.10 the microphone arrived with its bytes
  swapped, so only very quiet speech got through, and at a volume loud enough for calls Jarvis heard nothing. It now
  asks PipeWire for plain samples.
- **Echo cancelling holds:** the system's "follow the default mic" could move Jarvis off the echo-cancelled mic onto
  the raw one, and Jarvis heard and answered itself. It now stays put, and if it ever isn't on it, the mic is off while
  Jarvis talks. After a restart it no longer catches the last run's canceller on its way out, a "mute all mics" from an
  earlier run no longer comes back, and a click just before a reply no longer lets Jarvis's own voice through.

## 1.14.0 — 2026-10-22

### Changed
- **A new look, everywhere:** the window is redesigned from the ground up in a "glass" style: a deep navy canvas lit
  by Jarvis's colour, frosted cards, a floating sidebar, larger type, and an arc reactor at the heart of Home that
  turns faster while Jarvis listens and glows orange while it works. Every page, the chat and the first-run setup
  were redone to match, and the setup screen can now be moved and closed like the rest of the window.

### Added
- **Scheduled tasks:** *"every weekday at 8, check my inbox and tell me what matters"* now does it at 8, instead of
  just saying the words. The outcome is said, shown, and sent to your phone (Telegram or the app).
- **Keep an eye on things:** a list in Settings (or *"keep an eye on failed payments"*) that Jarvis checks every hour
  or so, through your accounts and the web, telling you only when something needs you. These run on their own: changes
  that need your yes are never made, Jarvis says what it would do instead. Each check is a few model requests.
  What it found joins the conversation, so you can answer *"yes, do it"* from your phone or out loud.
- **Jarvis for scripts and AI agents:** `jarvis --task "..."` prints Jarvis's reply, `jarvis --say "..."` says it out
  loud, and `jarvis --mcp` is an MCP server, so Claude Code, Codex and other agents can hand Jarvis tasks on the PC.
- **Jarvis learns the way:** when a task only worked after several tries, it remembers how ("How to: ...") and goes
  straight there next time.
- **The Jarvis app for Android:** type or speak tasks to Jarvis from anywhere. It connects through your own private
  relay (a small Cloudflare Worker you deploy for free from the `relay` folder), the way OpenChamber's phone link does:
  the PC and the phone both dial out, so nothing on the PC is open to the internet, and everything is end-to-end
  encrypted, so the relay only ever sees ciphertext. It shares the window's new design. Pair by scanning the code in
  Settings. Replies that finish while
  the app is closed arrive when you open it, and with your own Gemini key it still answers when the PC is off.

### Fixed
- **Reminders said out loud:** when Gemini was slow to say one, Jarvis reconnected after 12 s and then showed "please
  say it again" (you hadn't said anything). Announcements now get 25 s, and never ask you to repeat yourself.
- **One message per request:** asked for "another joke", Jarvis sent four in a row, and a C++ game went out eight
  times. Once a message is sent, another one for the same request is refused (several go in one go when you ask).
- **"Can you see my screen?":** Jarvis said it couldn't, three times, before looking. It looks now.
- **Clicking and typing in one step:** when a step both clicked the message box and held the text, the text was
  dropped and an empty Return was "sent". It now clicks, then types.
- **Long text is pasted:** a page of code typed key by key took up to a minute and the virtual keyboard dropped
  mid-way. Text over 200 characters goes in through the clipboard (and the clipboard is put back after).
- **Text starting with a dash** (like "-1, 0, 1" in homework) failed to type; scrolling up failed the same way.
- **The virtual keyboard dropping** on Wayland: typing tries the uinput backend before giving up.
- **Long sends aren't read out:** a sent message is said back word for word only when it's short; code, digits and
  long jokes are named, not recited. No placeholder text ("...") is ever typed.
- **"My days"** no longer starts the morning briefing.
- **Crisis lines:** asked about suicide, Jarvis gave a US number to someone outside the US. It now gives the line for
  the country you live in.
- **Agent tool errors are logged** with what went wrong, not only the tool's name.

## 1.13.7 — 2026-10-18

### Fixed
- **No more runaway tool loops:** looking for an app that wasn't open, the voice once checked the windows and the
  screen over 100 times in a minute without a word. After 12 tools for one request it now stops and tells you what's in
  the way.

## 1.13.6 — 2026-10-18

### Fixed
- **"Keep watching my screen" works:** an old example in the voice prompt made Jarvis answer "I can only look when you
  ask" instead of watching. "Do you see my screen?" now looks.
- **No more repeated jokes:** a new voice session sees what Jarvis sent lately, so it doesn't send the same joke
  again after a restart. Asked to type a joke, it types it instead of saying it.
- **No sarcasm at your expense:** the wit is about things, never a jab at you or your questions.
- Jarvis no longer says it "can't access" your own sites: going through your saved posts on a site you're signed in
  to goes to a background task.
- Switching to a window whose title has a quote in it (some Discord servers) took 5 s and then claimed it worked; it's
  instant now.
- A stray word Jarvis rightly ignored no longer makes it reconnect 12 s later.
- In Electron apps (Discord, OpenCode, VS Code) Jarvis clicks the exact field, checks with a look in the same step, and
  skips the accessibility lookup that always failed there.
- "Mark my emails as done" marks them read; they're archived only when you say archive.
- Network checks say the numbers (ping in ms, packet loss in %).
- "Lesson:" notes are only about how Jarvis acts, not facts; "you don't need to know that" forgets it.

### Added
- **Classroom announcements in one step**, from every course at once, named by course instead of code.

### Changed
- The log no longer has progress bars mixed into its lines (they hid whole conversations).
- A connection opened early for a wake word that didn't come logs its score, to tune that later.

## 1.13.5 — 2026-10-16

### Fixed
- **Jarvis no longer hears and answers itself** with echo cancelling on. The canceller leaves a faint copy of Jarvis's
  voice in the mic (about 1/200 as loud as you); Gemini heard it as you talking, cut itself off and replied to its own
  words, over and over. While Jarvis talks, the mic now sends silence unless you're clearly talking, so you can still
  interrupt it.

## 1.13.4 — 2026-10-15

### Fixed
- **Careful looks are fast again** (5 s instead of 25-60 s): with a Google account signed in they used Gemini Flash on
  "medium" thinking, which took 27 s just to read a Sudoku grid. They're back on "low", like before 1.13.
- Puzzles are read, then solved with code: asking a look to solve a whole Sudoku timed out on every model and thinking
  level. A look now only reads the grid, a short Python script solves it, and a background task fills it in.
- One request that times out no longer benches its model for a minute or more with "isn't answering": Jarvis checks it
  again after 5 s and only says it's down if that fails too.

## 1.13.3 — 2026-10-15

### Fixed
- **A message is never sent twice.** The voice model sometimes called the same send again right after it worked (one
  Discord message went out three times), or a second "yes" cut the first send off halfway and typed it all again.
  Text that was already sent isn't sent again until you ask again, and text a cancelled send left in the message box
  isn't typed over it.
- Typing several lines (five jokes) puts them in one message: line breaks go in as Shift+Enter, where a typed newline
  sent each line as its own message.
- **Faster with a Google account signed in:** background tasks and careful looks used Gemini Flash on "high"
  thinking, 10-35 s per agent step and over a minute for a hard screen (a careful look ran past the voice's 60 s
  limit). Background tasks now use "low" (same answers in our tests, 2-3x faster: 3-4 s a step), careful looks
  "medium" and the second try at finding a click target "low". A Models page list you set yourself keeps its
  settings.
- Learning your voice stops at 120 clips of each kind: every few wake-ups it retrained on all of them, minutes of
  full CPU in the middle of a conversation or a game.
- "Type five jokes" makes them up and types them, without reading them out or asking first; "why is my internet
  slow?" checks with a command instead of giving general advice.
- The agent no longer reads other apps' private files (a browser's saved site data) to work out what's on screen.

### Changed
- GitHub releases carry their version's changelog as release notes.

## 1.13.2 — 2026-10-15

### Fixed
- **Echo cancelling covers everything the PC plays** (games, videos, calls), not only Jarvis's voice: PipeWire's echo
  canceller now uses the speakers' output as its reference, so game sound isn't taken for the user talking.
- "How many unread emails?" was refused in read-only mode and logged as a change: an action's own verb now decides
  (GMAIL_GET_LABEL reads a label).
- The voice no longer says an email was sent when the safety check held it back: the refusal reads "NOT DONE", and a
  tool that returned an error never counts as done.
- "Type hello world" types it instead of saying it; "mute my mic" mutes the PC's microphone instead of ending the
  conversation; locking the screen and other quick PC actions run without "shall I?"; "take notes" starts at once
  (asking first lost the lecture's start); "download X" downloads it instead of opening the page.
- "What did we talk about yesterday?" looks up that day's conversations (`recall` takes a day).
- Jarvis on your phone: `/stop` works while a task runs (tasks no longer block reading new messages).
- Account changes made through Composio's general tool are in the change log for "undo that".
- A screen watch whose looks keep failing (a used-up quota) stops and says why instead of trying for an hour.
- Shared voice answers are reused only while the first is still running, never a finished one (a stale screen).
- `find ... -delete` asks first like `rm`; a reminder for a date that's already passed is refused, not fired at once.
- A self-update restart cleans up like a normal exit (the echo canceller was left loaded twice).
- Today's calendar range uses a real UTC offset on Windows too.

### Added
- `evals/voice_eval.py`: ~110 real-life requests typed to the real voice model, with real reads from connected accounts
  and simulated changes behind the real safety gates.

## 1.13.1 — 2026-10-15

### Added
- **Watch the screen**: "tell me when the download finishes", "watch for an enemy plane": Jarvis looks every few
  seconds (up to an hour) and says it out loud when it shows up. "Stop watching" ends it.

### Fixed
- Game or video sound picked up as speech no longer restarts a screen check over and over: the same question asked
  again while it's being answered waits for that answer, so it's spoken once instead of being cut off each time.
- "Did I turn it in?" says when it was turned in (from Classroom's history) instead of guessing "earlier today".
- No more "anything else I can help with?" after a stray word; words from a game or call aren't taken as the user's.
- The agent no longer tries to take and analyse screenshots with shell commands when a click or paste seems not to
  work: it looks and tries another way.

## 1.13.0 — 2026-10-15

### Added
- **Sign in with Google** (Models page, opt-in): Gemini and Claude models through a Google account's Antigravity quota,
  far more than a free AI Studio key. Several accounts take turns when one is rate-limited, and accounts signed in with
  the opencode Antigravity plugin are used too. When signed in, these models come first for every job; without a
  sign-in they're skipped. It signs in the way Google's Antigravity app does, which Google doesn't offer other apps:
  Google may limit or suspend accounts used like this, and the page says so. The voice still uses an AI Studio key.
  Antigravity's sign-in details aren't in Jarvis: they're read from an installed opencode-antigravity-auth plugin, or
  `ANTIGRAVITY_CLIENT_ID` / `ANTIGRAVITY_CLIENT_SECRET` in the env file.

## 1.12.0 — 2026-10-15

### Added
- **Lecture and meeting notes**: "take notes of this lecture" records what the PC plays (or the room's microphone, for a
  class in person), transcribes it every five minutes as it goes, and on "stop the notes" writes a summary, key points,
  dates and homework plus the full transcript to Documents/Jarvis Notes, then says it's ready. Silent stretches aren't
  sent (models invent words for silence). Linux (PipeWire).
- **Undo**: everything Jarvis changes (commands that change things, account actions) is logged and shown in Activity;
  "undo that" or "what did you change?" reads the log and reverses it. Files it deletes go to the trash (a plain `rm`
  becomes `gio trash`), so they come back; only "delete permanently" really deletes.
- **Plans**: a long task's steps show in the chat as it starts, so a wrong turn can be stopped early.
- **Ask about part of the screen**: `jarvis --region` (bind it to a key) lets you drag over a chart, an error or a
  question; Jarvis reads it carefully, shows it in the chat and listens for your question.
- **Calendar by voice**: "add the dentist tomorrow at 2" (quick add), "move my physics lab to 4", "cancel tomorrow's
  meeting" (asks first) and "when am I free on Friday?".
- README: the new features, and Health and Settings screenshots.

## 1.11.0 — 2026-10-15

### Added
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
