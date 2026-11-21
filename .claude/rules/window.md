---
paths:
  - "**/window.py"
  - "**/qml/**"
  - "**/translations/**"
  - "**/docs/screens.py"
---

# The window and the local API

Part of this repository's architecture notes (the rest: `CLAUDE.md` and the other files here). Each paragraph is how
that part works and what broke before.

**Window and API.** Jarvis's own Qt platform (XWayland for the notch) goes in `qt_args`, never `os.environ` (launched
apps inherited it). The window is Qt Quick: `window.py` registers a `Backend` QObject as the QML singleton `Jarvis.Backend`
(`qml/*.qml`, theme tokens in `qml/Theme.qml`). QML calls `Api.get/post` → `Backend.request` (thread pool) → `get(path)`/`post(path,
data)`, which map to `api_get`/`api_post` in jarvis.py, and events from `emit()` reach it because `Backend` sits in `clients` (it has
`put()`). Polled values (state, mic level) refresh at 30 fps, only while the window is shown (`Backend.watch`); the notch ticks at 30 fps only while it shows. The look ("glass": tokens in `Theme.qml`, shared pieces
like `Glass`, `Section`, `Chip`, `StatusDot`, the arc reactor in `Orb.qml`) is shared with the phone app's `Theme.kt`.
QML gotchas: the engine loads local files only (`window.LocalOnly`): Qt fetches the pictures in rich text and Markdown by
itself, so a reply's image link could carry data out; a web picture is saved first (`system._web_art` for covers). File paths become URLs through `Backend.fileUrl`/`localPath` (`"file://" + path` broke on Windows); `AbstractButton` has a FINAL `icon` (ours is `symbol`); local
`Label.qml`/`Page.qml` get shadowed by QtQuick.Controls (ours are `Txt`, `ScrollPage`); `#AARRGGBB` colours; font sizes go
through `Theme.px(n)` (the text-size setting, rounded to whole pixels); QtSvg only reads `#rrggbb`; `window.py` forces the
Basic style (Windows' native one ignores custom backgrounds). A closed `ComboBox` with focus changes and emits
`activated` on a typed letter or an arrow (a stray "l" saved `whatsapp_calls: off` and calls went unanswered):
`Select.qml` swallows letters, opens the list on arrows and ignores the wheel. Buttons, switches and chips are `Qt.TabFocus` (Tab reaches
them, a click doesn't move the typing) with `Focus { keyboard: true }` on `visualFocus` and Enter as `click()`; a chip
that's only a label sets `Qt.NoFocus`; `ScrollPage` scrolls a control Tab reached into view. The first-run `SetupWizard` covers the window until
`setup_done`. Attaching lives in `Composer.qml` (file dialog, drop, Ctrl+V through `Backend.paste`: a clipboard picture is saved
into `store.PASTED_DIR`, tidied with the conversations); `window.with_attached`/`split_attached` build and parse the
"(attached: path)" notes the prompts rely on, and `Attachment.qml` draws a file in the box and in a sent message.
On Linux `qt_args` adds `-platformtheme xdgdesktopportal` when Qt has that plugin (`system.portal_theme`), so file
dialogs are the desktop's own. Deletes that can't be undone go through `ConfirmButton.qml` (two clicks), and a password is typed into
`PasswordField.qml` (an eye shows it: the first People password, typed blind and once, wasn't what its user meant). The Memory
page saves with the text it loaded (`store.save_memory(text, was)`: lines Jarvis added meanwhile are kept). Activity
lists the work log (`/api/work`, `work_entries`; `log_work` emits a live "work" event).
Settings (`SettingsPage.qml`) is tabs plus a search over every tab: each row has its own `showing` (its label, hint,
choices or its section's title holds every typed word), containers read their children's `showing`, never `visible` (an
invisible parent makes every child's `visible` false), and a test fails when a `DEFAULT_SETTINGS` key appears in no QML:
a new setting lands with its control. Home's "Working on" (`Today.qml`) polls `/api/jobs` (`brain.running`) and stops one task with
`/api/jobs/<n>/stop`. Every user-visible QML text goes through `qsTr()` (`.arg()` for values, `%n` plurals; Python's tray/notch
texts through `QCoreApplication.translate`); `window_languages` (priority list, `store.WINDOW_LANGUAGES`) installs
`translations/jarvis_<code>.qm` up to the first `en` (`Window.languages`, live `retranslate`). After changing texts run
the lupdate/lrelease commands in window.py's `TRANSLATIONS` comment: the tests check each `.qm` matches its `.ts`. Arabic
mirrors the layout, so place things with anchors, not `x:` (a mirrored anchor against an unmirrored `x` ends up off
screen); `Txt` aligns left by default so mirroring moves it. `docs/screens.py` takes `WINDOW_LANGUAGES="ar"` to render a
language. Never start apps on a private `dbus-run-session` here: its AT-SPI launcher takes over the
session's accessibility socket. Web fetches (`fetch`, the headless browser, `show_image`) go through the `Guard` proxy in brain.py. A picture
written into an answer is shown only when it's a file (`reply_pictures`, `OUTSIDE_PICTURE`): an address stays a link,
never fetched because an answer named it. Over real HTTP,
`serve_app` only accepts `/api/listen`, `/api/show`, `/api/region`, `/api/task` and `/api/say`, and only with the per-run token and a
matching Host header. `/api/task` (`jarvis --task`, `jarvis --mcp`) runs unattended, like a scheduled task.
