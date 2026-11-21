"""Renders the window's pages to PNGs with made-up data, off screen (nothing of the real user's shows: own config
dirs, canned API answers). For design work and the README's pictures:

    .venv/bin/python docs/screens.py OUT_DIR [home home-empty home-new home-attach home-running chats people activity accounts
                                               plugins models memory cost cost-month settings health setup] [--size 1280x820]
                                               [--state idle|listening|thinking|speaking]

home-attach: files attached in the message box and in a sent message (a picture, a PDF, a recording, one that's gone).
people-locked: the People page with its password not given.
home-new: before anything is said, with no account connected yet. home-running: the tasks at work, opened from their
chip (a narrow window: --size 900x700).

WINDOW_LANGUAGES="ar" (or "ja de"...) renders it in those languages. Settings' tabs: settings-voice, settings-day,
settings-window, settings-messages, settings-phone, settings-data, settings-advanced; settings-search with
--search "words" (a tall --size, like 1280x2400, shows a whole tab).
"""
import json, os, sys, tempfile, time, types

tmp = tempfile.mkdtemp()
os.environ.update(XDG_CONFIG_HOME=tmp, XDG_DATA_HOME=tmp, APPDATA=tmp, PYTHON_KEYRING_BACKEND="keyring.backends.fail.Keyring")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # (software drawing: no blur or shadows; run it on a hidden
# compositor with QT_QPA_PLATFORM=wayland to see those)
os.makedirs(f"{tmp}/jarvis", exist_ok=True)
with open(f"{tmp}/jarvis/plugins.json", "w") as f:
    f.write('{"composio": {"url": "https://connect.composio.dev/mcp", "enabled": true}}')
if os.environ.get("WINDOW_LANGUAGES"):
    with open(f"{tmp}/jarvis/settings.json", "w") as f:
        json.dump({"window_languages": os.environ["WINDOW_LANGUAGES"].split()}, f)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jarvis, brain  # noqa: E402

# (the Models page reads these from outside Jarvis's own dirs: the user's Google sign-ins and keys)
brain.OPENCODE_ACCOUNTS = os.path.join(tmp, "accounts.json")
brain.PLUGIN_CONSTANTS = [os.path.join(tmp, "constants.js")]
brain.google_accounts = lambda: [{"email": "sam@example.com", "source": "jarvis"}]
brain.google_client = lambda: True
brain.api_key = lambda: "made-up"
jarvis.store.set_secret("aistudio", "made-up-key-one-4f2a\nmade-up-key-two-9c1e")  # (two keys: the Models page lists them)
brain.ollama_models = lambda: []

NOW = time.time()
CONVERSATION = [
    {"who": "you", "text": "What's due this week?", "time": NOW - 600},
    {"who": "tool", "text": "classroom_due", "time": NOW - 598},
    {"who": "jarvis", "text": "Two things: the Calculus problem set on Wednesday at 11:59 pm, and the History essay draft on "
                              "Friday. The problem set is the bigger one, about 12 questions.", "time": NOW - 590},
    {"who": "you", "text": "Remind me tomorrow at 6 to start the problem set", "time": NOW - 300},
    {"who": "system", "text": "⏰ Reminder set for tomorrow at 18:00", "time": NOW - 298},
    {"who": "jarvis", "text": "Done. I'll remind you tomorrow at six.", "time": NOW - 296},
    {"who": "you", "text": "Find me a good lo-fi playlist and play it", "time": NOW - 60},
    {"who": "tool", "text": "youtube_search", "time": NOW - 58},
    {"who": "jarvis", "text": "Playing **Lofi Girl, beats to study to** on YouTube. Say \"next\" if it isn't your vibe.",
     "time": NOW - 50},
]
SESSIONS = [{"id": f"2026100{i}-120000-abc{i}", "title": t, "updated": NOW - i * 86400, "count": n}
            for i, (t, n) in enumerate([("What's due this week?", 9), ("Planning the weekend trip", 14),
                                        ("Fixing the Wi-Fi printer", 22), ("Gift ideas for Sam", 6),
                                        ("Summarise the physics lecture", 11), ("Morning briefing", 4)])]
CANNED = {
    "/api/today": {"weather": {"place": "Springfield", "icon": "⛅", "condition": "Partly cloudy", "temp": "21°C", "feels": "20°C"},
                   "wake": "Hey Jarvis", "reminders": [{"id": "a1", "text": "Call the dentist", "when": "Today 15:30"},
                                                       {"id": "a2", "text": "Start the problem set", "when": "Tomorrow 18:00"}],
                   "remembered": 7, "tools": 41, "connected": ["github", "gmail", "google_classroom", "googlecalendar", "googledrive"]},
    "/api/media": {"player": "org.mpris.MediaPlayer2.spotify", "app": "Spotify", "status": "Playing", "title": "Neon Tides",
                   "artist": "The Arcs of Light", "art": "", "length": 214.0},
    "/api/jobs": [{"n": 3, "label": "Find flights to Lisbon for the first week of June", "since": NOW - 187, "now": "web_search", "coding": False},
                  {"n": 4, "label": "Fix the failing date test", "since": NOW - 1425, "now": "", "coding": True}],
    "/api/jobs/done": [{"n": 2, "label": "Summarise the three reports in Downloads", "at": NOW - 540, "ok": True, "coding": False,
                        "answer": "Done: the notes are in Documents/report-notes.md. The second report has no figures for March."}],
    "/api/system": {"cpu": 18.0, "mem_used": 9.1e9, "mem_total": 16e9, "disk_used": 300e9, "disk_total": 512e9, "uptime": 7200},
    "/api/sessions": {"current": SESSIONS[0]["id"], "sessions": SESSIONS},
    "/api/conversation": {"id": SESSIONS[0]["id"], "title": "What's due this week?", "created": NOW - 600, "updated": NOW - 50,
                          "messages": CONVERSATION, "agent": []},
    "/api/memory": {"memory": "- Prefers to be called Sam.\n- Lives in Springfield.\n- Studies computer science, second year.\n"
                              "- Likes lo-fi while studying.\n- Allergic to peanuts.\n- Has a cat named Pixel.\n"
                              "- Works at the campus library on Tuesday and Thursday evenings, so no calls between 6 and 10 then.\n"
                              "- Lesson: in Discord, check the open chat before sending.\n- Lesson: never press Check answer on homework sites.\n"
                              "- Lesson: say times in the 12-hour clock.\n"
                              "- How to: export a Canva design: Share, then Download, not File.\n"
                              "- How to: join the lab Wi-Fi: forget the network first, then sign in with the student account."},
    "/api/approvals": [{"tool": "GMAIL_BATCH_MODIFY_MESSAGES", "app": "gmail", "label": "Gmail: batch modify messages",
                        "said": "don't ask me before marking emails read", "at": NOW - 3 * 86400},
                       {"tool": "GOOGLECALENDAR_CREATE_EVENT", "app": "googlecalendar", "label": "Google Calendar: create event",
                        "said": "you don't have to ask before putting study blocks in my calendar", "at": NOW - 12 * 86400}],
    "/api/reminders": [{"id": "a1", "text": "Call the dentist", "when": "Today 15:30", "edit_at": "2026-10-28 15:30"},
                       {"id": "a2", "text": "Start the problem set", "when": "Tomorrow 18:00", "edit_at": "2026-10-29 18:00"},
                       {"id": "a3", "text": "Check my inbox and tell me what matters", "when": "Thu 29 Oct, 08:00 · weekdays",
                        "edit_at": "2026-10-29 08:00", "repeat": "weekdays", "task": True},
                       {"id": "a4", "text": "Water the plants", "when": "Sun 01 Nov, 10:00 · weekly · paused", "edit_at": "2026-11-01 10:00",
                        "repeat": "weekly", "off": True}],
    "/api/checks": {"checks": [{"text": "Tell me if a payment fails", "on": True},
                               {"text": "Tell me if my professor emails about the exam", "on": True},
                               {"text": "Watch for cheap flights home in December", "on": False}], "every": 60,
                    "last": {"at": NOW - 1260, "answered": NOW - 1260, "ok": True, "found": "", "next": NOW + 2340}},
    "/api/routines": [{"name": "study mode", "steps": "close Discord, open my notes, set a 50-minute timer"},
                      {"name": "good night", "steps": "lower the volume, lock the screen"}],
    "/api/workspaces": [{"slug": s, "name": n, "connected": c, "account": a, "mode": m} for s, n, c, a, m in [
        ("gmail", "Gmail", True, "sam@example.com", "ask"), ("googlecalendar", "Google Calendar", True, "sam@example.com", "full"),
        ("googledrive", "Google Drive", True, "sam@example.com", "read_only"), ("google_classroom", "Google Classroom", True, "sam@example.com", "ask"),
        ("github", "GitHub", True, "sam-dev", "ask"), ("spotify", "Spotify", False, "", "ask"), ("notion", "Notion", False, "", "ask"),
        ("discord", "Discord", False, "", "ask"), ("slack", "Slack", False, "", "ask"), ("todoist", "Todoist", False, "", "ask")]],
    "/api/phone": {"relay": "wss://jarvis-relay.example.workers.dev", "connected": True, "error": "", "pairing": None,
                   "devices": [{"id": "d1", "name": "Pixel 9"}]},
    "/api/remote": {"token": False, "paired": "", "code": "481516", "error": ""},
    "/api/health": {"checks": [{"name": "Microphone", "ok": True, "detail": "Blue Yeti, hearing you"},
                               {"name": "Voice model", "ok": True, "detail": "gemini-3.8-live answers in 0.6 s"},
                               {"name": "Screen", "ok": True, "detail": "screenshots and clicks work"},
                               {"name": "Accounts", "ok": False, "detail": "Spotify isn't connected", "fix": "Connect it", "page": "accounts"}],
                    "usage": {"aistudio gemini-3.8-flash": 12, "aistudio gemini-3.5-flash-lite": 31}},
    "/api/setup/key": {"ok": False, "detail": "no key yet"},
    "/api/update": {"update": False, "version": "test"},
    "/api/report": {"text": "Jarvis test · everything looks fine"},
    "/api/todo": {"couldnt_check": [], "items": [
        {"what": "Return the library books", "due": time.time() - 86400, "kind": "task", "place": "My Tasks", "source": "Google Tasks"},
        {"what": "Quiz 3", "due": time.time() + 26 * 3600, "kind": "classroom", "place": "Calculus 3", "source": "Classroom: Calculus 3",
         "link": "https://classroom.google.com/"},
        {"what": "Stretch", "due": time.time() + 20 * 60, "kind": "reminder", "place": "", "source": "reminder", "id": "r1"},
        {"what": "send Sam the trip photos", "due": None, "kind": "promise", "place": "Sam Lee", "source": "promise to Sam Lee"}]},
}
HOUR, DAY = 3600, 86400
PEOPLE = {  # (the People page: people.json as Jarvis keeps it, made up)
    "Maya Lee": {"aka": ["mayalee"], "seen": {"whatsapp": NOW - 25 * 60}, "wrote": {"whatsapp": NOW - 40 * 60, "discord": NOW - 2 * DAY},
                 "notes": [{"text": "My cousin, studies medicine in Lyon", "at": NOW - 30 * DAY},
                           {"text": "Anatomy exam on Friday", "at": NOW - 2 * DAY, "until": NOW + 3 * DAY}],
                 "promises": [{"what": "send Maya the trip photos", "at": NOW - 5 * HOUR, "due": NOW + 20 * HOUR, "app": "whatsapp"}],
                 "profile": {"gist": "cousin; warm and teasing, writes in French and English", "at": NOW - 3 * DAY, "upto": NOW - 3 * DAY, "count": 120,
                             "text": "Cousin, close in age; you talk most evenings\nWrites short bursts in French, switches to English for jokes\n"
                                     "Lots of emoji, rarely formal\nLately: her anatomy exam, and the summer trip to Porto\n"
                                     "Open: she asked for the trip photos; you said you'd send them\nCareful: exam stress, don't bring up grades"}},
    "Omar Haddad": {"seen": {"discord": NOW - 3 * HOUR}, "wrote": {"discord": NOW - 3 * HOUR},
                    "notes": [], "profile": {"gist": "classmate in Physics 2; brief, plans study sessions", "at": NOW - DAY, "upto": NOW - DAY,
                                             "count": 64, "text": "Classmate in Physics 2\nShort, practical messages in English\n"
                                                                  "Lately: the lab report and Thursday's study session\nOpen: waiting on your half of the lab data"}},
    "Sam Okafor": {"seen": {"whatsapp": NOW - 26 * HOUR}, "notes": [{"text": "Landlord", "at": NOW - 60 * DAY}], "no_profile": True},
    "Alex Rivera": {"aka": ["alexr"], "seen": {"discord": NOW - 4 * DAY}, "wrote": {"discord": NOW - 4 * DAY},
                    "profile": {"gist": "friend from the climbing gym; jokes a lot, long voice notes", "at": NOW - 6 * DAY, "upto": NOW - 6 * DAY,
                                "count": 88, "text": "Friend from the climbing gym\nJokes a lot, sends long voice notes\nLately: a weekend climbing trip"}},
    "Dr. Chen": {"notes": [{"text": "Dentist, Tuesdays and Thursdays", "at": NOW - 9 * DAY}]},
}
STUB = types.SimpleNamespace(
    plugin_status=lambda: [{"name": "composio", "config": {"url": "https://connect.composio.dev/mcp"}, "enabled": True, "status": "ready",
                            "error": "", "tools": ["COMPOSIO_SEARCH_TOOLS", "COMPOSIO_MULTI_EXECUTE_TOOL"]},
                           {"name": "filesystem", "config": {"command": "npx -y @modelcontextprotocol/server-filesystem ~"},
                            "enabled": False, "status": "off", "error": "", "tools": []}],
    workspaces=lambda: CANNED["/api/workspaces"], app_tools={}, model_jobs=brain.Brain.model_jobs,
    available_models=lambda: {"backends": [{"name": "aistudio", "models": ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash-lite"]}],
                              "live": ["gemini-3.8-live"]})


def cost(days):
    """A made-up Cost page: a day's use of each model (requests, tokens in, out, USD or None), spread over the period."""
    day = [("aistudio gemini-3.8-live", 38, 160_000, 52_000, 1.014), ("antigravity gemini-3.8-flash", 46, 420_000, 11_000, 0.356),
           ("aistudio gemini-4-hydrogen", 4, 38_000, 3_000, 0.08), ("aistudio gemini-3.5-flash-lite", 63, 210_000, 6_000, 0.078),
           ("aistudio gemini-3.7-flash", 2, 12_000, 1_000, None)]
    spread = [0.6, 1.1, 0.4, 0.9, 1.3, 0.2, 1.0, 0.8, 1.2, 0.5][:days] * 3 if days > 1 else [1.0]
    spread = spread[:days]
    stamps = [time.strftime("%Y-%m-%d", time.localtime(time.time() - i * 86400)) for i in range(days - 1, -1, -1)]
    total = sum(sum(c or 0 for *_, c in day) * f for f in spread)
    return {"total": round(total, 6), "tokens": int(sum((i + o) for _, _, i, o, _ in day) * sum(spread)), "unpriced": 1, "unmeasured": 0,
            "days": [{"day": d, "cost": round(sum(c or 0 for *_, c in day) * f, 6)} for d, f in zip(stamps, spread)],
            "models": [{"key": k, "requests": int(r * sum(spread)), "input": int(i * sum(spread)), "output": int(o * sum(spread)),
                        "cost": None if c is None else round(c * sum(spread), 6)} for k, r, i, o, c in day]}


def made_up_files():
    """A photo, a report, a recording and a file that's gone, in the temp dir: what home-attach shows attached."""
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath
    folder = os.path.join(tmp, "files")
    os.makedirs(folder, exist_ok=True)
    photo = QImage(1200, 800, QImage.Format.Format_RGB32)
    p = QPainter(photo)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    sky = QLinearGradient(0, 0, 0, 800)
    for at, colour in ((0, "#2b2d6e"), (0.55, "#e9677a"), (0.8, "#ffb36b")):
        sky.setColorAt(at, QColor(colour))
    p.fillRect(photo.rect(), sky)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#ffe0a3"))
    p.drawEllipse(QPointF(760, 560), 90, 90)
    for colour, top in (("#3a2f5b", 520), ("#1d1a33", 610)):
        hills = QPainterPath(QPointF(0, 800))
        hills.lineTo(0, top)
        hills.cubicTo(300, top - 120, 700, top + 90, 1200, top - 40)
        hills.lineTo(1200, 800)
        p.setBrush(QColor(colour))
        p.drawPath(hills)
    p.end()
    paths = [os.path.join(folder, n) for n in ("sunset-at-the-lake.png", "Lab report - final draft (v3).pdf", "Physics lecture 14.m4a",
                                                "Pasted screenshot.png")]
    photo.save(paths[0])
    for path, size in ((paths[1], 248_000), (paths[2], 31_400_000)):
        with open(path, "wb") as f:
            f.truncate(size)
    return paths  # (the last one is never made)


def get(path):
    if path in CANNED:
        return CANNED[path]
    if path.startswith("/api/cost"):
        return cost(int(path.partition("days=")[2] or 1))
    if path.startswith("/api/sessions/"):
        return CANNED["/api/conversation"]
    if path.startswith("/api/search"):
        return [{"id": s["id"], "title": s["title"], "match": "…what's due this week…", "updated": s["updated"]} for s in SESSIONS[:2]]
    return jarvis.api_get(path, STUB)


def main():
    args = sys.argv[1:]
    options = {"--size": "1280x820", "--state": "idle", "--search": "wake"}
    for name in options:
        if name in args:
            options[name] = args.pop(args.index(name) + 1)
            args.remove(name)
    if not args or any(a.startswith("-") for a in args):
        sys.exit(__doc__)
    out = args.pop(0)
    size, state, query = options["--size"], options["--state"], options["--search"]
    pages = args or ["home", "home-empty", "chats", "activity", "accounts", "plugins", "models", "memory", "cost", "cost-month", "settings",
                     "health", "setup"]
    os.makedirs(out, exist_ok=True)
    if len(pages) > 1:  # (one window per process: Qt allows only one)
        import subprocess
        for page in pages:
            subprocess.run([sys.executable, __file__, out, page, "--size", size, "--state", state, "--search", query])
        return
    page = pages[0]
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtWidgets import QApplication
    QQuickWindow.setDefaultAlphaBuffer(True)
    qt = QApplication([])
    import window
    w, h = (int(n) for n in size.split("x"))
    live = types.SimpleNamespace(mic=state == "listening", level=0.6 if state in ("listening", "speaking") else 0.0, raw_level=0.3)
    if page in ("home-empty", "home-new"):
        CANNED["/api/conversation"] = {**CANNED["/api/conversation"], "messages": []}
    if page == "home-new":
        CANNED["/api/today"] = {**CANNED["/api/today"], "connected": []}
    if page in ("people", "people-locked"):  # (locked: the page has a password, and nobody gave it)
        jarvis.store.write_json(os.path.join(jarvis.store.DATA, "people.json"), PEOPLE, private=True)
        jarvis.people_lock.close()
        jarvis.store.set_secret(jarvis.store.PEOPLE_LOCK, "")
        if page == "people-locked":
            jarvis.store.set_people_lock("made up")
    if page == "home-attach":
        files = made_up_files()
        sent = {"who": "you", "time": NOW - 20, "text": window.with_attached("Summarise the report, and where was this taken?",
                                                                             [files[0], files[1], files[3]])}
        CANNED["/api/conversation"] = {**CANNED["/api/conversation"], "messages": CONVERSATION[3:] + [sent]}
    win = window.Window(get=get, post=lambda p, d: {"ok": True}, tool_label=jarvis.tool_label, live=live,
                        shown_state=[state, False], version="2.5.0", show=True)
    root = win.engine.rootObjects()[0]
    root.setProperty("width", w)
    root.setProperty("height", h)
    root.setProperty("needsSetup", page == "setup")
    root.setProperty("page", "home" if page in ("home-empty", "home-new", "home-attach", "home-running", "setup") else "cost" if page == "cost-month"
                     else "settings" if page.startswith("settings") else "people" if page == "people-locked" else page)
    settle = time.time() + 2.0
    while time.time() < settle:
        qt.processEvents()
        time.sleep(0.02)
    from PySide6.QtCore import QObject
    if page == "cost-month":  # (the 30 days chip, pressed)
        root.findChild(QObject, "costPage").setProperty("days", 30)
    if page == "home-attach":  # (a picture, a report and a recording waiting in the message box)
        root.findChild(QObject, "composer").setProperty("files", files[:3])
    if page == "home-running":  # (its chip, clicked)
        from PySide6.QtCore import QMetaObject
        QMetaObject.invokeMethod(root.findChild(QObject, "runningChip"), "click")
    if page == "settings-search":
        root.findChild(QObject, "settingsSearch").setProperty("text", query)
    elif page.startswith("settings-"):
        root.findChild(QObject, "settingsPage").setProperty("tab", page.partition("-")[2])
    root.setProperty("needsSetup", page == "setup")  # (the window asks the settings once it's up)
    settle = time.time() + 0.5
    while time.time() < settle:
        qt.processEvents()
        time.sleep(0.02)
    root.grabWindow().save(os.path.join(out, f"{page}.png"))
    print(os.path.join(out, f"{page}.png"), flush=True)


if __name__ == "__main__":
    main()
