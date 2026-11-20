# Changelog

## Unreleased

### Added
- **Picks up where you left off:** after a restart Jarvis carries on the conversation you were in (if you or Jarvis
  spoke in it in the last 6 hours and you didn't start a new one), voice and background tasks alike. It used to start
  empty every time, twelve times on a busy day.
- **The voice and background tasks see each other's work:** a short line per finished tool call from the last 30
  minutes goes with the conversation to both, so a follow-up knows what was just found or done.
- **Tasks take stock:** a long background task looks back at its goal (and the plan it showed) every few steps, and
  sooner when it looks stuck (every call failing, the same click doing nothing again, command after command); the next
  step thinks harder. A stuck task says what's in its way instead of trying thirty commands.
- **Learns from your corrections:** *"no, the slides are under materials"* or *"always save lectures to Desktop/Uni"*
  is kept in memory as a lesson, and a task that only worked after some wrong turns keeps the way that worked as a
  *"How to:"* line when it wasn't obvious.
- **Quicker screen checks:** watching the screen (*"tell me when the download finishes"*) and the check before typing
  into a chat ask Gemini's Decisions API first (about half a second, no output tokens) when your clicking models are
  Google AI Studio's. When it isn't sure, or can't answer, the vision model decides as before.
- **One to-do list:** *"what do I have to do this week?"* answers from everywhere things to do are kept: your Google
  Tasks, your reminders, the promises Jarvis noticed in your messages and Classroom work not turned in, overdue first.
  Home's *To do* card shows the same list (it used to show reminders only). A source that can't be reached is named, so
  it's never taken for "nothing to do".
- **Word and PowerPoint files:** `.docx` and `.pptx` files (a lecture's slides, a report) are read like PDFs, slide by
  slide (they were turned down as "a binary file").
- **Screen time from QHealth:** "how long was I on my PC today?", "how much did I game this week?", "what did I use most
  yesterday?" are answered from QHealth's own records (time per category and app, active time only). Jarvis only reads
  QHealth's database, never changes it, and says so when QHealth isn't installed, has no records that far back or
  seems to have stopped.
- **A Cost page:** what Jarvis's model use would cost at Google's paid-tier prices, for today, the last 7 or 30 days:
  the total, a bar per day, and each model's requests, tokens and cost (the voice's audio priced as audio). Nothing is
  billed on the free tier or through a Google sign-in; the page shows what the same use would cost with billing on.
- **The window works from the keyboard:** Tab reaches every button, switch, chip and the side rail (a ring shows where
  you are), Enter or Space presses it, a control further down the page scrolls into view, and Tab leaves the message
  box instead of typing a tab. Switches without a label of their own are named for screen readers.
- **Several API keys for one provider:** paste more than one key for Gemini, OpenAI or any other provider on the Models
  page and they take over from each other: when one is rate limited, out of its daily quota or refused, the next
  answers, and the voice (Gemini Live) moves to the next key too. Each saved key shows by its last four characters and
  can be removed on its own. A key Gemini calls invalid no longer ends the whole request: the next key or model takes it.
- **Search everything Jarvis keeps:** *"what did Sam send me about the trip?"* looks through past conversations (with
  the WhatsApp and Discord messages shown in them), your lecture and meeting notes, every WhatsApp chat, people's pages
  and memory at once, newest first.
- **Read a recording:** point Jarvis at a voice recorder's file (*"read my conference recording"*): a short one's words
  come back at once, a long one is written up as notes (a summary and the whole transcript) like live notes. Needs
  ffmpeg.
- **"Don't ask me before marking emails read":** saying so lifts the yes for that one account action (*"ask me again
  before that"* brings it back). Only your own words count, they must name the app, and with a spoken passphrase set
  it has to be said too; an email or a page can't do it.
- **Learns from conversations:** when a conversation is over, Jarvis adds lasting things you said about yourself to its
  memory (at most three, never other people's messages or a video in the background) and shows each in the chat.
  Settings → Your data → *Learn from conversations*.

- **The phone app, rebuilt as a voice remote:** say *"Hey Jarvis"* to your phone (or the wake word you chose on the PC),
  tap the orb, or use Android's assistant gesture, and you're talking with the Jarvis on your PC: its own voice, every
  tool, the same conversation, from wherever you are. The wake word is recognised on the phone itself (the PC's own
  models, sent over once), and listens with the app closed. Tap while Jarvis talks to cut in.
  - **The PC's chat, live:** what you and Jarvis say at the PC or on the phone shows in the app as it happens, with
    what it's doing right now (*"Reading your screen…"*).
  - **Notifications:** reminders, finished tasks and what Jarvis tells you on its own arrive on the phone with the app
    closed (Settings → *Stay in touch when closed*).
  - **Today** (the weather, what's coming up, one-tap asks) and **PC** (the tasks Jarvis is working on, each with its
    own Stop, what's playing with play, pause and skip, a look at the screen, processor, memory and disk, lock, mute,
    new conversation, stop everything).
  - **Share to Jarvis** from any app: the text or link waits in the box for what to do with it.
  - **With the PC off:** with your own Gemini key the app talks and answers by itself (Gemini Live, the PC's voice),
    and says what it can't do without the PC.
- **No relay needed at home:** on the same Wi-Fi, or a VPN like Tailscale, the app connects straight to the PC, and
  pairing works without a Cloudflare account. The relay is still there for everywhere else, and the app picks whichever
  answers (direct first). Settings → The Jarvis app → *Connect directly on your own network* (on by default; the PC only
  listens while a phone is paired or a pairing code is showing, and your firewall may need to allow port 47800).
- **Take a message back:** *"delete the last thing I sent Sam on WhatsApp"*, *"unsend that"* deletes your own message
  for everyone, on WhatsApp (within two days of sending) or Discord, after your yes.
- **Working on, in the window:** Home lists every task that's running with what it's doing right now and how long it
  has been at it, and a Stop for that one only.
- **Settings has an index:** its sections are listed beside the page; click one to jump there.
- **Files kept on your PC:** *"download my physics lectures from Classroom into a folder on my desktop"* saves the
  files themselves from Drive (PDFs, slides, anything), and a document someone sent you on WhatsApp is saved to
  Downloads and read (*"when's the opening in the schedule Dana sent?"*).
- **Several things at once:** a second request no longer waits for the first. Voice, typed, phone and scheduled tasks
  run side by side; screen work takes turns, and waits while you're using the keyboard or mouse. *"What are you working
  on?"* lists them, *"stop the flight search"* stops one, and Stop stops them all and says what it stopped.
- **Coding jobs:** *"fix the login bug in my jarvis project"* becomes a session in your OpenChamber (started if it
  isn't open), working on its own in a copy of the project (a git worktree on its own branch): watch it and answer its
  questions there. Jarvis tells you when it's done and what changed; nothing is merged until you say so. *"Also add
  tests"* continues the same session. Without OpenChamber, Claude Code does it (only editing files while safety is on
  "ask"), and *"do it in Antigravity"* hands it to Google Antigravity's `agy` (Jarvis said it wasn't available).
- **News waits for you:** while you're away from the PC, finished tasks and their questions wait, and are said when
  you're back (*"While you were away: ..."*). Long answers (research) are shown in full in the chat; the voice says the
  gist.
- **The evening list remembers:** who was on the last one and still waits on you is said apart (*"Still waiting since
  the last list: Sam on WhatsApp"*), and *"leave Sam off the list"* keeps them off until they write again.
- **Who you're meeting:** each meeting in the briefing and the evening list says who's coming and what Jarvis knows
  about them (*"13:00 Lunch, with Sam (my cousin)"*), so *"who am I seeing today?"* has an answer; *"what's up with
  Sam?"* lists your meetings with them in the next two weeks.
- **Quiet over games and films:** while a full-screen app has focus, what Jarvis would say on its own (task results,
  updates, the morning briefing) goes to the chat and notifications instead; your reminders still speak. Settings →
  *Quiet over full-screen apps* (on by default; KDE Plasma on Wayland and Windows).
- **Calendar heads-ups bring the meeting:** the reminder before an event carries its Meet, Zoom or Teams link and its
  attached files, so *"open it"* joins or opens the doc. Links are shown, never read out.
- **Discord, through Vesktop:** *"what's new on Discord?"*, *"what did Sam say?"*, *"what's happening in the study
  server?"*, *"tell Sam I'm on my way"*, *"post 'gg' in Gaming #general"*, *"reply to his last message"*, *"react 😂"*,
  *"what's in the picture he sent?"*: Jarvis reads, sends, replies and reacts inside your own Vesktop, with no bot and
  nothing on screen; *"@name"* pings. New DMs and pings show in Jarvis's chat. Settings → *Discord* → *Restart
  Vesktop* turns it on once. Optional: Jarvis answers your friends' DMs that don't need you (off by default: Discord
  may ban accounts that act like bots).
- **People pages:** *"what's up with Sam?"* brings what Jarvis knows about them (*"Sam is my cousin"*, notes that end
  on a date), when you last wrote to each other, what you promised them, and your latest messages and emails.
- **Promises kept:** *"I'll send it tomorrow"* in a chat or email gets a reminder (or goes on the evening list).
- **The evening list** at 20:00 (Settings → *Your day*): who's waiting on your reply, unread emails from people, and
  what's on tomorrow. Ask any time: *"who's waiting on me?"*
- **Jarvis learns when to speak up:** kinds of news you keep letting pass are only shown, not said, for a while.
- **Jarvis gets quicker at your apps:** the way a screen task worked is kept and reused, and dropped if it stops working.
- **Screen history** (opt-in): window titles only, on your PC, for *"what was that site I had open yesterday?"*
- **"Don't answer Sam"**, *"tell me when Alex messages me"*: say it, and Jarvis keeps it in Settings' *Never answer* /
  *Always let through* lists for WhatsApp, Discord or both (*"answer her again"* undoes it).
- **WhatsApp voice messages are understood:** a voice message someone sends you is transcribed as it arrives, so
  Jarvis's auto-reply answers what they said, and the chat log, *"read my WhatsApp"* and Jarvis's history show its words
  instead of "[a voice message]".
- **Jarvis talks with the people who message and call you:** it holds a real back-and-forth on WhatsApp (answers
  follow-ups, asks what they need, passes things on) instead of one "he'll get back to you", and on calls it chats,
  answers and checks it got their message right, answering as quickly as its own voice. Limits keep anyone from using
  up your models: 8 replies an hour to one chat (20 in all), 3 picked-up calls an hour from one person, 20 voice
  messages transcribed an hour, and only from your contacts; it won't write essays or homework for them. Settings →
  WhatsApp → *Tell people when I'm busy* lets it share your Google Calendar's busy times (never what they are).

### Changed
- **Gemini 4 Hydrogen leads background tasks.** It guesses less than the Flash models. On a free key it's often slow or
  busy, so after 8 seconds the next model is asked too, and once its daily quota is used up it's skipped until it resets.
- **Notes hear the room and the PC together:** live notes record the microphone and what the PC plays at once, so a
  meeting in the room or on a call is caught either way (notes of "the conference" once recorded only the PC's sound,
  which held nothing but Jarvis's own voice). The notes file is written as they go, so a restart keeps the transcript,
  and a PC that can't record says so instead of taking notes of nothing.
- **Your saved keys never leave in a tool call:** a tool call carrying one of your API keys or sign-in tokens is
  refused, and any that turn up in a file or command output are hidden before a model sees them, so a page or an email
  can't talk Jarvis into sending them.
- **Faster when a model stalls:** a model that doesn't answer within a few seconds no longer holds a look at the screen
  or a task's step for its whole timeout (up to 20 s): the next model on the Models page is asked as well, and the first
  answer wins.
- **Missed WhatsApp calls are in the chat:** a number that only rang shows up in your chats, so *"who called me?"* and
  *"reply to the number that just called"* work.
- **Easier to read:** the faintest text in the window and the phone app is lighter (it was below the contrast screen
  readers' guidelines ask for), and buttons that are only a picture say what they do to screen readers.
- Asked how much memory or processor it's using, Jarvis measures itself instead of guessing.
- **Jarvis doesn't give up as easily:** a failed tool or a way that doesn't work is a reason to try the next way, and
  what it doesn't know how to do on your system (bind a shortcut, change a setting) it finds out and does, instead of
  saying it can't. Long jobs get twice the steps (60), and at the limit it says what's done and what's left, so
  *"continue"* carries on.
- **WhatsApp without a browser: about 1 GB less memory.** WhatsApp ran as WhatsApp Web in a hidden Chromium (~950 MB);
  it's now a small helper, `jarvis-wa` (~30 MB, Go: whatsmeow for messages, WaCalls' code for calls), with the same
  replies, calls, reading, sending, voice messages and photos. Link WhatsApp again once in Settings (and remove the old
  "Chrome" device from your phone's Linked devices). Building it needs Go on Linux (Jarvis does it by itself; the
  Windows app and the AUR package come with it). Older messages than the ones seen since linking are fetched from your
  phone when asked for.
- **Learning your voice no longer keeps ~200 MB:** the voice check is trained in a short-lived process, so
  scikit-learn, SciPy and the training's peak don't stay in Jarvis's memory after every few wake-ups.

### Fixed
- **Deleting through a script asks first:** a command that hands code to Python, Node, Perl, Ruby or PHP to delete, move
  or overwrite files (`python3 -c "import shutil; shutil.rmtree(...)"`) ran without your yes, a way round the check on
  `rm`. It waits for a yes now, on one line or many; code that only reads or works something out still runs.
- **Gemini 4 Hydrogen stops "timing out":** on an AI Studio key it takes 17 to 40 seconds for any answer, and Jarvis cut
  replies off at 20, so about half were thrown away and it was reported as not answering. It gets a minute there now,
  and the same model through a Google sign-in (3 seconds a step) is in the built-in list for background tasks.
- **A typed message always gets its answer:** typed while Jarvis was about to say something on its own (a reminder,
  the evening list), the answer was left out of the chat, and with spoken replies off for typed text nothing came back
  at all.
- **Messages still show when Jarvis's own answer couldn't be sent:** with Vesktop slow or WhatsApp's link gone, the
  person's message was dropped without a word. It's shown now, with a note that the answer may not have been sent.
- **A send that failed isn't reported as sent:** when an account action failed inside the service's reply, the second
  try was refused as "already done" and Jarvis said it had gone. It's tried once more, and after two failures Jarvis
  says it didn't go.
- **Long tasks survive an empty reply:** only three empty model replies in a row end a task (they were counted over
  the whole task, so the third ended it wherever it came).
- **Tool results stay in view in long conversations:** the newest tool calls keep a quarter of the context the models
  get; a long conversation used to leave room for one of them or none.
- **Smaller ones:** the weather where your network gives coordinates and no town; WhatsApp just after start-up (a tool
  waits a few seconds for the link instead of failing); a chat found by its own id; the list of running tasks after
  one was stopped; what you asked Jarvis to learn isn't lost to an offline moment (it's tried again); a question about
  a picked part of the screen no longer finds the voice's tools used up by the request before it. Background tasks
  get clearer errors: an account action that isn't a direct tool, a Drive file's id given as a path, a slow command
  stopped at its timeout.
- **Your name in messages:** a memory like *"Call the user Kai instead of sir"* made auto-replies and the voice call you
  *"Kai instead of sir"*, also in messages to other people. Only the name is used now, and a note about someone else
  (*"the professor wants to be addressed as Dr. Karam"*) is no longer taken for yours.
- **Your words win over the voice's summary:** a background task reads what you said first and the voice's summary
  after it, so *"half past six"* isn't sent as *"at 5"* when the summary got it wrong.
- **Background tasks use the stronger models:** lite models answer a task's step only when the stronger ones fail, one
  at a time (raced alongside, they carried whole tasks, which then gave up), and Jarvis tells you once a day when that
  happens. Gemini 4 Hydrogen is no longer first in the built-in list: it answered none of 191 steps there, and each
  step waited 8 seconds for it.
- **No more asking the same thing over and over:** the voice no longer repeats the same lookup, failing read or change
  within one request (it looks again after anything that may have changed the answer), and after 12 tools it hands
  the job to a background task instead of asking you where to look.
- **"yea" is a yes** when Jarvis asks you to confirm.
- **A message on screen checks the chat first:** a background task that types a message and presses Enter in a chat
  app without checking whose chat is open is stopped before anything is typed.
- **Decorated names:** WhatsApp and Discord chats with fancy or fullwidth letters, emoji, accents or Arabic vowel marks
  are found by their plain name; a near miss still picks nothing.
- **"What's on my screen" means yours:** looking at the screen no longer describes Jarvis's own window.
- **Messages passed on sound like you:** *"tell him yes, but I'll give it to him tomorrow"* sends *"Yes, but I'll give it
  to you tomorrow"* to him (it went word for word), *"tell him yes"* goes to the person you're talking with (it went to
  someone who had written an hour before), and one request sends one message. Jarvis now sees what people wrote, not
  only its summary, including messages that arrive while you're talking with it.
- **Typed requests are never taken for noise:** a typed *"say yes"* got no answer at all, and a typed *"go now"* ended
  the conversation in silence.
- **Lecture files from Classroom:** slides and notes a teacher posts as a course's materials are found (Jarvis looked
  through the work and announcements over and over, then said no files were posted), and one is read or saved under
  its own name, as the kind of file it is. *"The latest lecture"* and *"my calculus class"* (a course whose name is
  only its code) are found too.
- **Long lists from your accounts:** a list too long to come back whole (a course's 25 lectures, a busy course's
  announcements) arrived as a sample and a file Jarvis can't reach: the voice went looking for that file on your PC,
  then said the slides were downloaded, and announcements said "couldn't check". Jarvis now reads such lists page by
  page, and a result that was cut says so instead of passing for the whole of it.
- **"Continue" after a long job** carries on from where it stopped: it used to start over, because the request and
  everything done so far had been dropped from what Jarvis remembers of the conversation.
- **No more silent digging by voice:** asked *"when did I unplug my charger?"*, the voice ran 13 commands in a row
  while you waited, then said the logs didn't say. After 4 commands it hands the digging to the agent, which finds it.
- **Knows when it has the answer:** a file that isn't there, or one whose owner turned off downloading, is reported
  after a couple of tries, with the rest of the job done. Jarvis used to hunt for it through every tool it has (20
  steps for one missing file), and once wrote scripts to fetch a refused file anyway. Setting something up (a keyboard
  shortcut) takes about a third of the steps, and what was changed only to try it out (a muted microphone) is put back.
- **Looking at your PC takes no yes:** *"why isn't Bluetooth working?"* and *"which version of ffmpeg do I have?"*
  are answered from a look (`systemctl status`, `pacman -Q`, `pip list`, `crontab -l` and the like). Jarvis treated
  those as commands that change things, so it asked first, or passed the yes itself. Starting, stopping, installing
  and removing still wait for your yes.
- **Small edits in a project go to the coding agent too:** *"fix the typo in my project's README"* was edited in place
  with `sed`, then handed to the coding agent as well. Any change to a project's files now goes to the coding agent,
  in its own copy.
- A coding job whose OpenChamber was closed says so, instead of "failed: no output".
- A reminder set *"at 10:00"* on the day before the clocks change rang an hour off.
- More commands that change things wait for a yes: `\rm`, `X=1 rm`, `xargs -I {} rm {}`, `timeout -s INT 5 rm`,
  `find -execdir rm`, `python -m pip`, `busybox rm`. `command -v npm` ("is it installed?") no longer asks.
- KDE: with windows that have no title (the desktop's own), listing the open windows took seconds, or gave apps each
  other's titles.
- **Tasks keep your words:** a task handed to the agent carries what you actually said, so "use commands, not my
  screen" isn't lost in the voice's summary of it.
- **Things going out twice:** a voice send cut off by a noise is no longer reported as "cancelled" (it had gone, and was
  sent again), an email or event isn't re-sent when the plugin's answer is lost on the way back, a slow WhatsApp send
  isn't called failed while it's still going out, and a task that fails partway keeps what it already did, so "try
  again" doesn't repeat it.
- **"Done." for nothing:** an empty reply from a model is asked again, and a task that never got an answer says so.
  A reply that asks you something ("Shall I go ahead?") is no longer answered for you with "do it".
- **Typing into the wrong place:** an act step naming an app that can't be brought up types nothing; the window Jarvis
  launched only gets the keyboard back just after the launch; a plan whose look or screenshot fails still says what ran.
- **Voice:** the reply after one cut off with Stop was silent; a lookup's answer ("let me check"...) or a failed send
  was never spoken; Stop pressed while the backup voice writes a request down now stops it. When the connection
  drops while Jarvis is looking something up or sending, it reconnects and tells you how it went (it used to go
  silent). A request Gemini lets drop is asked again even while a background task is working. *"Now type it again in
  the other box"* types it (it only clicked the box).
- **Notes:** a recorder no longer outlives Jarvis (one filled the temp folder for a day); a piece that can't be written
  down is tried again, and its recording kept beside the notes if it still can't.
- **Remembering:** two facts remembered at once are both kept (one was lost, sometimes the whole memory with it).
- **Accounts:** results over 20,000 characters are read whole (Classroom said "nothing due"), a course that can't be
  read is an error, not an empty one, and accounts without direct tools stay connected after the Accounts page refreshes.
- **WhatsApp:** no auto-reply after a restart in a chat you were just writing in; an answered call is still reported
  when its summary fails, and one where nothing was said is mentioned. Jarvis picks a call up only once its voice is
  ready (callers were cut off or left in silence when it wasn't), and never two calls at once.
- **Background checks:** one that failed or was stopped no longer skips what arrived meanwhile.
- A command that times out stops with everything it started; the selection is read only when the read worked.
- Apps Jarvis opens on Wayland are no longer forced through XWayland (blurry or the wrong size on a scaled screen).
- **"Listen to the conference with me" takes notes now:** asking Jarvis to keep listening through a meeting, class or
  conference without talking got *"I'll remain active and keep listening"*, though its microphone closes after a few
  seconds of quiet, and words from the meeting could end the conversation. It now starts its notes (from the microphone
  when it's in the room) and goes quiet; *"stop the notes"* at the end gives the summary and transcript.
- **Google accounts (Models page) are no longer hammered when they're rate-limited:** a limited account was asked twice
  per request and again a minute later for as long as the limit lasted, every other account got the same request the
  same second, and an account Google had disabled was asked again for good. Each account is now asked once, rests as
  long as Google says (or as long as the opencode plugin already knows), a full model isn't retried on the other
  accounts, and a disabled or refused account is left alone, with a notice when none is left.
- **One Google account at a time:** Jarvis keeps to the account that answered last for every model, and with accounts
  shared from the opencode plugin it uses the one the plugin is on now (it used to start on the first one whichever
  opencode was using: two accounts at once from one PC). An account signed in from Jarvis still comes first.
- **No "hi" probes on Google accounts:** when Google had no capacity for a model (503), didn't answer in time, couldn't
  be reached or didn't serve the model (404), Jarvis sent "hi" to it every few minutes until it answered, requests the
  Antigravity app never sends. It now waits (30 s after a timeout or a lost connection, an hour after a 404) and tries
  again with the next real request.
- **Google accounts are paced like the Antigravity app:** after a 429 or 503 Jarvis waits as the app does, 4 s, then
  up to 8, 16 and 30 s while refusals continue (never sooner than Google asks), instead of its own 30 s to 5 min, and
  like the app it puts no cap of its own on how many requests it sends.
- **Privacy:** the window fetched any web picture written into the text it shows (a reply, a message, a song's title)
  by itself, so a page or email that tricked the model into writing an image link with your data in it could send that
  data out with no tool call or safety check. The window now only loads files from this PC; a player's cover on the
  web (Spotify's) is saved by Jarvis first, so Home still shows it.
- Notes you'd typed on the Memory page but not saved were wiped when you went to another page and came back.
- The Models page's hint for another service's address is translated now.
- **Phone app:** with the PC out of reach, Today said *"No reminders set."* and the PC page *"Nothing is playing."*
  without having asked; they say the PC can't be reached.
- **Arch package:** building it needed Go, which the AUR package didn't list (AUR helpers stopped at the build).
- **Safety (Windows):** a picture Jarvis showed from a web address was saved under a name the website chose, which on
  Windows could put a file anywhere, the Startup folder included. It's always a picture file in Pictures/Jarvis now.
- **Safety:** commands that change things wait for your yes however they're written: by their path (`/bin/rm`), inside
  `bash -c "…"` or `eval`, or behind `env`, `nice`, `timeout` and the like.
- One voice request that went wrong (a tool call that failed) left Jarvis silent until it gave up and asked you to say
  it again; the other calls' answers are given now. A screen action that ran too long kept clicking after Jarvis had
  moved on: it stops.
- Notifications on Linux that started with a dash (a list) never appeared.
- A WhatsApp or Discord message could go unmentioned when the reply model answered with nothing.
- The weather no longer names your town as a number ("in 33.83") where the weather service can't tell the town's name.
- *Set up my relay* works when your Cloudflare sign-in has more than one account (it stopped with "More than one
  account available"): it uses your own, and tries the deploy once more when Cloudflare didn't answer.
- No more error in the log when Jarvis quits with its window open.
- A long task no longer fails because every model was busy for one moment: the step is asked again after a short wait
  (a 64-step download once ended on a single "no model could answer").
- A WhatsApp or Discord message that came while no model could answer was never mentioned: it's shown now.
- **Safety:** opening an app could run any command, so *"rm -rf ~/Documents"* through *launch* skipped the yes that
  run_command asks for; it no longer does. More commands that change things wait for a yes (`sed -i`, `tee`, `rsync`,
  `ln`, `git branch -D`, `docker rm`, piping into Python...). The agent can no longer disconnect your accounts through
  Composio (only the Accounts page does), and a paused WhatsApp or Discord isn't read either.
- **Backups:** importing one no longer resets paused or read-only accounts to "ask" (each keeps the stricter mode).
- **Privacy:** a Telegram reply that couldn't be sent offline put your bot's token in the log and in bug reports; the
  bug report also leaves out your checks, what WhatsApp tells people, names in errors and your home folder now.
  "Delete my data" and unlinking WhatsApp also delete the WhatsApp messages Jarvis saved.
- **Windows:** pictures in the chat never showed, and dropped or attached files had broken paths. A click on a picture
  only ever opens a picture.
- **Phone app:** a broken pairing link no longer makes the app crash at every start; replies are no longer lost after
  the phone changes networks; and *"Working on it…"* goes away when the PC goes offline instead of staying for good.
- A WhatsApp call that comes in while Jarvis is calling someone is left to ring (their audio crossed); meetings are said
  in your time zone, not the one they were made in.
- Stopping tasks: *"stop"* without saying which no longer stops all of them, *"stop the flight search"* sent from the
  phone no longer stops itself, and *"stop number 2"* still means the same task after another one has finished.
- A request the voice repeats while it's being worked on isn't done twice (a message could go twice).
- A task waiting for your answer while you're away no longer keeps the screen from other tasks.
- Coding jobs: starting one by voice answers at once (a slow start was taken for a failure and the job started twice),
  two at once get their own numbers, a moment when OpenChamber is slow to answer no longer ends the job as "failed"
  (or with no news at all), and on Windows a task with quotes, `&` or several lines reaches Claude Code whole.
- Using the mouse while Jarvis works on the screen no longer counts as being away (its news was held back).
- The Accounts page says which account each app is connected to: Google Calendar and Drive showed only "Connected",
  and Notion "Composio", instead of the email.
- Discord stopped working after every reboot when Vesktop starts with the system: its login entry skipped the setting
  Jarvis needs. *Restart Vesktop* (Settings → Discord) now adds it there too, once.
- **Lighter:** about 60 MB less memory and half the idle CPU. The wake word's model rests while the room is quiet (it
  still hears a soft "Hey") and does a quarter less work when it runs; the window is built when you first open it and
  freed after ten minutes closed; freed memory goes back to the system after tasks and voice sessions.
- A message or account change Jarvis made by voice (WhatsApp, Discord, an email...) sometimes went twice: the voice
  model called it again right after it worked. The same change now waits until you speak again.
- **Windows: settings and other files no longer fail to save** now and then when something else (an antivirus, the
  search indexer) had them open for a moment: the save is tried again.

## 2.1.0 — 2026-10-29

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
