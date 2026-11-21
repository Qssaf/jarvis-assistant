---
paths:
  - "**/brain.py"
  - "**/jarvis.py"
  - "**/store.py"
  - "**/qml/AccountsPage.qml"
  - "**/qml/PluginsPage.qml"
---

# Safety gates, accounts and plugins

Part of this repository's architecture notes (the rest: `CLAUDE.md` and the other files here). Each paragraph is how
that part works and what broke before.

**Safety in code, not only prompts.** With the `safety` setting on "ask" (the default), risky shell commands
(`RISKY_COMMAND`) and account changes in "ask" mode (`needs_yes`: not `is_read_action`) are refused until the model
passes `confirmed: true` (`with_confirmed` adds it to those schemas; it's stripped before Composio sees it). A tool
that changes things isn't risky in its reading forms (`RISKY_BUT_READING`: `systemctl status`, `pacman -Q`, `pip list`,
`crontab -l`; only options that take no value may come before the reading word, so `systemctl -p status stop x` still
asks): a look that needs a yes teaches the model to pass `confirmed` itself. Code handed to an interpreter that deletes, moves or overwrites is risky too (`INLINE_CODE` and `CODE_CHANGES`, two one-pass
patterns over the whole command: `python3 -c "import shutil; shutil.rmtree(...)"` ran unasked, on one line, several, or
in a here-document); code that only reads or works something out still runs. A plain
`rm` is rewritten to `gio trash` unless `permanent: true`. `launch` (and `act`'s launch step) runs in a shell too, so it
refuses risky commands in "ask" mode (use `run_command`). Every change that runs is logged (`brain.changed` →
`store.log_change`) for `recent_changes` / "undo that".
With a spoken passphrase set (`store.PASSPHRASE`, a secret), a voice `confirmed: true` also needs it in `last_heard`
(`Live._tool`; typed text counts), and an agent task's needs an `ask_user` answer that carried it (`passphrase_ok`;
phone tasks are exempt). `emit` and `ask_user` replace it with `•••`, so it's never in the chat, sessions or log.
`Brain._run_tool` (the real dispatcher is `_dispatch`) refuses a call whose arguments hold a saved key or sign-in token
(`saved_secrets`: keychain provider keys and Telegram, the Google, opencode, plugin and `DATA/mcp` token files; 16+
characters, read again every 30 s) and hides them in every result (`hide_secrets`), for the voice and the agent alike.
An agent `act` plan that types and then presses Return in a chat app (`CHAT_APP`: the window in front or the plan's
`app`/`launch`) with no `expect` step before the Return is refused with `CHECK_CHAT` (`chat_unchecked`, in `_ask`'s
`run`, whatever the safety setting; the voice has its own checks in `Live._type_once`). Remembered approvals (`store.approvals`, `approvals.json` in CONFIG, never in backups): `needs_yes` skips a slug the user
lifted, and `approvals allow` passes only `may_stop_asking`: the user's latest own words (`user_said`, the app's
`live.last_heard`; a phone task's label; never an unattended task's) say not to ask (`NO_ASK`), name the app
(`APP_WORDS`), and hold the passphrase when one is set (not needed from the phone).

**Account modes.** `store.connector_modes()` (connectors.json) holds ask/full/read_only/paused per Composio toolkit.
`account_block` enforces paused and read-only in `run_app_tool`, on `COMPOSIO_MULTI_EXECUTE_TOOL` calls and on WhatsApp
and Discord reads (`WA_READ`, `DC_READ`); `COMPOSIO_MANAGE_CONNECTIONS` may only list or add (disconnecting is the
Accounts page's); a backup's import keeps each account's stricter mode;
`is_read_action` is a verb heuristic on the slug, and unknown verbs count as changes. `account_policy()` feeds both
prompts.

**Accounts and plugins.** Plugins are MCP servers (`McpServer`: streamable HTTP with OAuth, or a stdio command). Each
keeps one connection, and concurrent calls open their own. A call that fails is sent again once after reconnecting,
but a change (`call(again=False)`: not `is_read_action`) only when it surely never arrived (`unsent`). `app_data` reads
results whole (`limit=None`; the model's copy is capped at 20,000 characters, and says where it was cut). A list too
long for Composio comes back as a sample plus a file in its own sandbox (`remote_file_info`): nothing here can read it,
so `whole` turns that into an error saying what works (`TOO_LARGE`: less at a time), and `app_data` reads `pageSize`
lists page by page instead. Composio is the default plugin. For connected toolkits,
`APP_TOOLS` slugs are loaded as direct tools via `COMPOSIO_GET_TOOL_SCHEMAS` and run through
`COMPOSIO_MULTI_EXECUTE_TOOL`; `app_data` unwraps Composio's double-wrapped results (None when a call failed: keep
that distinct from "nothing there", as `briefing` and `classroom_work` do). Remote logins are renewed `REFRESH_EARLY`
before they expire: the MCP SDK counts a stored token's lifetime from when it's loaded, and a token refused
mid-connection makes it start a whole new browser sign-in. Only a refresh the server refuses (`rejected`: 400/401/403) may lead to a sign-in tab;
when it's out of reach the old token is kept, and a plugin that couldn't connect for that reason (`unreachable`) is
retried with backoff (it used to stay broken until a restart).
