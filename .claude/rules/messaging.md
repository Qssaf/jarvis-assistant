---
paths:
  - "**/whatsapp.py"
  - "**/discord.py"
  - "**/people.py"
  - "**/whatsapp-helper/**"
  - "**/evals/whatsapp_eval.py"
  - "**/evals/proactive_eval.py"
  - "**/evals/people_eval.py"
  - "**/qml/PeoplePage.qml"
---

# WhatsApp, Discord and people

Part of this repository's architecture notes (the rest: `CLAUDE.md` and the other files here). Each paragraph is how
that part works and what broke before.

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
drops it; `a.v` is the JS's hash). How a message reads is `TEXT_JS` (`text`, `files`), which the tests run in Qt's JS
engine (so no `flatMap` there): a forward has no words of its own, its content is in `message_snapshots[].message`
(read as empty, forwards never reached Jarvis). People rules (`<app>_always`/`<app>_never`, `whatsapp.contact_rule`, the
`people_rules` tool) are shared with WhatsApp, and so are `whatsapp.decide` and its limits for the opt-in
`discord_replies` ("friends": friends' one-to-one DMs only). `unsend` (one tool for both apps: the helper's `unsend`
sends whatsmeow's `BuildRevoke`, Discord's JS deletes through `RestAPI`) only takes back the user's own message, the
newest in the chat or the one holding `text`, and is in `ONCE_TOOLS`: a second call would delete the one before it. Jarvis's own replies are known by `(channel, text)` in
`mine` (memory only).

**People, promises, attention.** `people.py`: `people.json` holds a page per person (notes with an optional `until`,
`seen`/`wrote` per app from one-to-one WhatsApp and Discord messages via `talked`, which writes at most every 5 min per
person, and `promises`). `Tracker` (`people.tracker[0]`, made in `main()`) takes the user's own outgoing messages (and
WhatsApp sends Jarvis made for them; Discord's come back through `Listener`), keeps only ones `HINT` says talk about
later, and after `wait` seconds asks the agent's models once per burst (`PROMPT`); a promise with a time gets a
reminder, the rest go on the evening list. `evals/proactive_eval.py` checks the prompt. `Brain.person` and
`Brain.waiting_on_me` are the tools (dispatched in `_dispatch`); `evening_digest` (jarvis.py) scans the day's sent
mail, then tells `digest_text(waiting_on_me(listing=True))` once a day; `waiting.json` remembers that list's chats
(`listed`: said apart next time if still waiting) and `skip`'s names (`leave_off`: hidden until a newer message or
promise). Profiles (`Brain.profile`, `profile_of`: one request with `people.PROFILE_PROMPT`; the People page,
`PeoplePage.qml`, `/api/people`): `people_pass` (hourly, `people_profiles`) writes `PROFILES_PER_PASS` of
`due_profiles` (talked with in `ACTIVE_DAYS`, no profile or one older than `people_refresh_days` with messages since)
from one-to-one chats only (`_chat_with`: never a group), nothing under `PROFILE_MIN` messages of theirs (`looked`:
"few"/"empty" a day later, "forgot" never by itself); `scrub` and `hide_secrets` clean what's kept, the gist goes into
`people.index`, and `evals/people_eval.py` checks the prompt. The user's say per person (`people.set_flag`):
`no_profile` (never due, a refresh refused before any chat is read, what Jarvis made of them dropped) and `hidden`
(below); `edit_profile` keeps the user's own words unscrubbed with `edited`, which the pass never writes over (only
Refresh). The page's password (`store.PEOPLE_LOCK`, a salted PBKDF2 hash with the keys, never in backups;
`jarvis.PageLock`): locked, `/api/people` gives no name and `people_post` takes only the lock's own routes; it opens
for `PEOPLE_OPEN` s after its last use, `LOCK_TRIES` wrong passwords (the change route counts too) make the next
wait, and the page asks `/api/people/lock` now and then (asking isn't using). It guards the screen, not `people.json`
(encrypting the whole file with it was built halfway and dropped on the user's say: Jarvis would know nobody after
each start). Hidden people are the encrypted part, under a second password of their own (`store.PEOPLE_SECRET`,
hashed like the page's; the user asked for the two to be apart, so the page's opens the page and no key): their pages
sit under `people.HIDDEN` (AES-GCM, key = scrypt(secret password, salt), `ids`: salted hashes of their names),
`everyone()` gives them back marked `hidden` while the key is held (`hold`, called each time the secret password is
checked: Settings' row through `PageLock.change_secret`, and the search box), and every write goes
through `_save`, which seals them and carries a part it can't open (no key, another password's, damaged) along
untouched: Jarvis knowing nobody hidden must never be written as nobody being hidden. With no key, `_update` for a
hidden name (`_is_hidden`) waits in `_waiting` instead of making a page in the open, and a page marked hidden in the
open (one day's build did that) stays until `hold` seals it. They're listed only while `PageLock.revealed`: Enter in
the page's search box posts its text to `/api/people/reveal` (`REVEAL_EVERY`: one look a second, never an error, never
logged), and nothing in the API or page says anyone is hidden (no count: the user asked for that). `jarvis --reset-people-lock`
takes both hashes off and leaves the part encrypted; a later secret password adopts it when the old one is typed once
(`hold(current=True)`),
and nobody new is hidden meanwhile (`EARLIER`). `people_pass` logs "someone hidden", never the name. One person had two pages: Discord's own-message event gave only the
chat's title (a display name, which changes), so `listen` sends `peer` (the DM partner's username) and a message that
names both makes the pages one (`_update` with `aka`: `_same`, `_merged`); hiding merges every page sharing a name with
the one hidden; and a page of a hidden person left in the open isn't listed, told or looked up with no key (`_shown`:
`listing`, `index`, `page`), takes nothing new (`_update` waits), and `hold` folds it in. `people.meeting` writes a calendar event with its guests matched to pages (`Brain.events` reads them). `Attention` (jarvis.py, `attention.json`): `announce(...,
kind=)` of a kind the user let pass three times in a row (no speech within `HEEDED` s) is only shown for a backoff;
`loud` and `asked` (reminders, scheduled tasks) are never held back. Skills (`store.skills`, the `skill` tool): ways
a screen task worked, offered in `_ask` through `matching_skills`; a task of 3+ screen steps that saved none gets one
`SKILL_NUDGE` (its answer is kept). `activity.py` (opt-in `screen_history`): `system.focused()` every `POLL` s, a line
per change in `DATA/activity/<day>.jsonl`, never in backups.
