"""Renders the window's pages to PNGs with made-up data, off screen (nothing of the real user's shows: own config
dirs, canned API answers). For design work and the README's pictures:

    .venv/bin/python docs/screens.py OUT_DIR [home home-empty chats activity accounts plugins models memory settings
                                               health setup] [--size 1280x820] [--state idle|listening|thinking|speaking]

WINDOW_LANGUAGES="ar" (or "ja de"...) renders it in those languages.
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
                   "remembered": 7, "tools": 41},
    "/api/media": {"player": "org.mpris.MediaPlayer2.spotify", "app": "Spotify", "status": "Playing", "title": "Neon Tides",
                   "artist": "The Arcs of Light", "art": "", "length": 214.0},
    "/api/system": {"cpu": 18.0, "mem_used": 9.1e9, "mem_total": 16e9, "disk_used": 300e9, "disk_total": 512e9, "uptime": 7200},
    "/api/sessions": {"current": SESSIONS[0]["id"], "sessions": SESSIONS},
    "/api/conversation": {"id": SESSIONS[0]["id"], "title": "What's due this week?", "created": NOW - 600, "updated": NOW - 50,
                          "messages": CONVERSATION, "agent": []},
    "/api/memory": {"memory": "- Prefers to be called Sam.\n- Lives in Springfield.\n- Studies computer science, second year.\n"
                              "- Likes lo-fi while studying.\n- Lesson: in Discord, check the open chat before sending."},
    "/api/reminders": [{"id": "a1", "text": "Call the dentist", "when": "Today 15:30", "edit_at": "2026-10-28 15:30"},
                       {"id": "a2", "text": "Start the problem set", "when": "Tomorrow 18:00", "edit_at": "2026-10-29 18:00"},
                       {"id": "a3", "text": "Check my inbox and tell me what matters", "when": "Thu 29 Oct, 08:00 · weekdays",
                        "edit_at": "2026-10-29 08:00", "repeat": "weekdays", "task": True},
                       {"id": "a4", "text": "Water the plants", "when": "Sun 01 Nov, 10:00 · weekly · paused", "edit_at": "2026-11-01 10:00",
                        "repeat": "weekly", "off": True}],
    "/api/checks": {"checks": [{"text": "Tell me if a payment fails", "on": True},
                               {"text": "Tell me if my professor emails about the exam", "on": True},
                               {"text": "Watch for cheap flights home in December", "on": False}], "every": 60},
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
}
STUB = types.SimpleNamespace(
    plugin_status=lambda: [{"name": "composio", "config": {"url": "https://connect.composio.dev/mcp"}, "enabled": True, "status": "ready",
                            "error": "", "tools": ["COMPOSIO_SEARCH_TOOLS", "COMPOSIO_MULTI_EXECUTE_TOOL"]},
                           {"name": "filesystem", "config": {"command": "npx -y @modelcontextprotocol/server-filesystem ~"},
                            "enabled": False, "status": "off", "error": "", "tools": []}],
    workspaces=lambda: CANNED["/api/workspaces"], app_tools={}, model_jobs=brain.Brain.model_jobs,
    available_models=lambda: {"backends": [{"name": "aistudio", "models": ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash-lite"]}],
                              "live": ["gemini-3.8-live"]})


def get(path):
    if path in CANNED:
        return CANNED[path]
    if path.startswith("/api/sessions/"):
        return CANNED["/api/conversation"]
    if path.startswith("/api/search"):
        return [{"id": s["id"], "title": s["title"], "match": "…what's due this week…", "updated": s["updated"]} for s in SESSIONS[:2]]
    return jarvis.api_get(path, STUB)


def main():
    args = sys.argv[1:]
    if not args or any(a.startswith("-") and a not in ("--size", "--state") for a in args):
        sys.exit(__doc__)
    out = args.pop(0)
    size, state = "1280x820", "idle"
    if "--size" in args:
        size = args.pop(args.index("--size") + 1)
        args.remove("--size")
    if "--state" in args:
        state = args.pop(args.index("--state") + 1)
        args.remove("--state")
    pages = args or ["home", "home-empty", "chats", "activity", "accounts", "plugins", "models", "memory", "settings", "health", "setup"]
    os.makedirs(out, exist_ok=True)
    if len(pages) > 1:  # (one window per process: Qt allows only one)
        import subprocess
        for page in pages:
            subprocess.run([sys.executable, __file__, out, page, "--size", size, "--state", state])
        return
    page = pages[0]
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtWidgets import QApplication
    QQuickWindow.setDefaultAlphaBuffer(True)
    qt = QApplication([])
    import window
    w, h = (int(n) for n in size.split("x"))
    live = types.SimpleNamespace(mic=state == "listening", level=0.6 if state in ("listening", "speaking") else 0.0, raw_level=0.3)
    if page == "home-empty":
        CANNED["/api/conversation"] = {**CANNED["/api/conversation"], "messages": []}
    win = window.Window(get=get, post=lambda p, d: {"ok": True}, tool_label=jarvis.tool_label, live=live,
                        shown_state=[state, False], version="2.1.0", show=True)
    root = win.engine.rootObjects()[0]
    root.setProperty("width", w)
    root.setProperty("height", h)
    root.setProperty("needsSetup", page == "setup")
    root.setProperty("page", "home" if page in ("home-empty", "setup") else page)
    settle = time.time() + 2.0
    while time.time() < settle:
        qt.processEvents()
        time.sleep(0.02)
    root.setProperty("needsSetup", page == "setup")  # (the window asks the settings once it's up)
    settle = time.time() + 0.5
    while time.time() < settle:
        qt.processEvents()
        time.sleep(0.02)
    root.grabWindow().save(os.path.join(out, f"{page}.png"))
    print(os.path.join(out, f"{page}.png"), flush=True)


if __name__ == "__main__":
    main()
