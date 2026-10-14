"""Jarvis's saved state: settings, plugins (MCP servers) and conversation sessions."""
import json, os, sys, threading, time, uuid

import system

CONFIG, DATA = system.CONFIG, system.DATA
APP_PORT = int(os.environ.get("JARVIS_HUD_PORT", 4849))  # the app's local server

VOICES = ["Charon", "Orus", "Fenrir", "Puck", "Kore", "Zephyr", "Aoede", "Leda", "Enceladus", "Iapetus", "Umbriel",
          "Algieba", "Algenib", "Rasalgethi", "Alnilam", "Schedar", "Gacrux", "Achird", "Sadaltager", "Sulafat"]

# languages Gemini Live speaks (code -> name)
LANGUAGES = {"en-US": "English", "en-GB": "English (UK)", "ar-XA": "Arabic", "fr-FR": "French", "de-DE": "German",
             "es-US": "Spanish", "it-IT": "Italian", "pt-BR": "Portuguese", "tr-TR": "Turkish", "hi-IN": "Hindi",
             "ja-JP": "Japanese", "ko-KR": "Korean", "cmn-CN": "Chinese (Mandarin)", "ru-RU": "Russian", "nl-NL": "Dutch",
             "pl-PL": "Polish", "id-ID": "Indonesian", "vi-VN": "Vietnamese", "th-TH": "Thai"}

DEFAULT_SETTINGS = {
    "voice": "Charon",
    "language": "en-US",           # what Jarvis speaks and expects to hear (store.LANGUAGES)
    "personality": "jarvis",       # how it talks: jarvis (British, dry wit), friendly or brief
    "live_model": "gemini-3.8-live",
    "follow_up_seconds": 8,
    "keep_session_seconds": 300,   # after that, the voice session stays connected (mic off) for an instant next "Hey Jarvis"
    "wake_threshold": 0.5,
    "extra_instructions": "",
    "home_city": "",               # for the weather on the Chat page; empty = guess from your network
    "speak_typed_replies": True,   # off: typed messages get text-only answers
    "fast_voice": False,           # on: the voice model answers without thinking first (~0.3 s quicker, but less sharp)
    "end_of_speech_ms": 600,       # pause that counts as "finished talking"; lower = snappier, higher = fewer cut-offs
    "start_at_login": False,
    "show_thinking": False,        # the chat shows the agent's thinking and the voice model's decisions (never the notch)
    "morning_briefing": True,      # the first time Jarvis starts in a morning, it gives the day's briefing out loud
    "deadline_reminders": True,    # reminders a day and two hours before Google Classroom work is due
    "calendar_reminders": True,    # a reminder ten minutes before each Google Calendar event
    "echo_cancel": False,          # PipeWire echo cancelling (Linux): talk over Jarvis on speakers (experimental)
    "learn_my_voice": True,        # learn from real wake-ups to ignore things that aren't you saying "Hey Jarvis"
    "safety": "ask",               # ask: risky commands and account changes wait for your yes; full: Jarvis just does them
    "setup_done": False,           # the first-run setup has been gone through (or skipped)
    # "backend model thinking-level", tried top to bottom; busy or rate-limited ones are skipped
    # the same for the other jobs (see brain.MODEL_JOBS); empty = Jarvis's built-in choice
    "look_models": [], "point_models": [], "point_strong_models": [], "search_models": [], "image_models": [],
    "agent_models": [
        "aistudio gemini-3.8-flash medium",
        "aistudio gemini-3.7-flash low",
        "aistudio gemini-3.5-flash-lite minimal",
        "aistudio gemini-3.1-flash-lite minimal",
    ],
}

DEFAULT_PLUGINS = {
    "composio": {"url": "https://connect.composio.dev/mcp", "enabled": True,
                 "tools": ["COMPOSIO_SEARCH_TOOLS", "COMPOSIO_MANAGE_CONNECTIONS", "COMPOSIO_MULTI_EXECUTE_TOOL", "COMPOSIO_GET_TOOL_SCHEMAS"]},
}

_lock = threading.Lock()


def read_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, data, private=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600 if private else 0o644)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, path)  # atomic: a crash never leaves half a file


# ---------------------------------------------------------------- settings
SETTINGS_FILE = os.path.join(CONFIG, "settings.json")


def settings():
    return {**DEFAULT_SETTINGS, **{k: v for k, v in read_json(SETTINGS_FILE, {}).items() if k in DEFAULT_SETTINGS}}  # (minus retired ones)


def update_settings(changes):
    """Validate and save; returns the new settings. Raises ValueError on bad input."""
    s = settings()
    for key, value in changes.items():
        if key not in DEFAULT_SETTINGS:
            raise ValueError(f"unknown setting {key}")
        default = DEFAULT_SETTINGS[key]
        if isinstance(default, bool):  # before int: bool is an int in Python
            value = value is True or str(value).lower() in ("true", "on", "1", "yes")
        elif isinstance(default, list):
            value = [l.strip() for l in (value.splitlines() if isinstance(value, str) else value) if l.strip()]
            if key.endswith("_models"):
                for line in value:
                    parts = line.split()
                    if len(parts) != 3 or not parts[0].isidentifier():
                        raise ValueError(f"model line '{line}' should be: <backend> <model> <thinking>, e.g. aistudio gemini-3.8-flash low")
                if not value and key == "agent_models":
                    raise ValueError("keep at least one agent model")
        elif isinstance(default, (int, float)):
            value = type(default)(value)
        else:
            value = str(value)
        if key == "wake_threshold" and not 0.05 <= value <= 0.99:
            raise ValueError("wake threshold must be between 0.05 and 0.99")
        if key == "follow_up_seconds" and not 0 <= value <= 120:
            raise ValueError("follow-up must be 0-120 seconds")
        if key == "keep_session_seconds" and not 0 <= value <= 600:
            raise ValueError("keep the session 0-600 seconds")
        if key == "personality" and value not in ("jarvis", "friendly", "brief"):
            raise ValueError("personality is jarvis, friendly or brief")
        if key == "language" and value not in LANGUAGES:
            raise ValueError(f"language is one of {', '.join(LANGUAGES)}")
        if key == "safety" and value not in ("ask", "full"):
            raise ValueError("safety is ask or full")
        if key == "end_of_speech_ms" and not 200 <= value <= 2000:
            raise ValueError("the pause must be 200-2000 ms")
        s[key] = value
    with _lock:
        write_json(SETTINGS_FILE, {k: v for k, v in s.items() if v != DEFAULT_SETTINGS[k]})
    return s


# ---------------------------------------------------------------- memory: things the user asked Jarvis to remember
MEMORY_FILE = os.path.join(DATA, "memory.md")


def memory():
    try:
        with open(MEMORY_FILE) as f:
            return f.read().strip()
    except OSError:
        return ""


def set_memory(text):
    with _lock:
        os.makedirs(DATA, exist_ok=True)
        fd = os.open(MEMORY_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(text.strip() + "\n" if text.strip() else "")


def remember(fact):
    fact = " ".join(fact.split())
    if fact and f"- {fact}".lower() not in (l.strip().lower() for l in memory().splitlines()):  # (said twice: kept once)
        set_memory(f"{memory()}\n- {fact}")
    return fact


def forget(text):
    """Drop remembered lines containing text; returns how many."""
    text = text.strip()
    if len(text) < 3:  # "" or a letter is in nearly every line: that would wipe the memory
        raise ValueError("give a few words from the note to forget")
    lines = memory().splitlines()
    keep = [l for l in lines if text.lower() not in l.lower()]
    set_memory("\n".join(keep))
    return len(lines) - len(keep)


# ---------------------------------------------------------------- reminders
REMINDERS_FILE = os.path.join(DATA, "reminders.json")


def reminders():
    return sorted(read_json(REMINDERS_FILE, []), key=lambda r: r["at"])


REPEATS = ("daily", "weekdays", "weekly")


def next_time(at, repeat, now=None):
    """The next time a repeating reminder is due after now (the same clock time, whatever daylight saving does)."""
    now, t = now or time.time(), time.localtime(at)
    days = 0
    while True:
        days += 7 if repeat == "weekly" else 1
        when = time.mktime((t.tm_year, t.tm_mon, t.tm_mday + days, t.tm_hour, t.tm_min, t.tm_sec, 0, 0, -1))
        if when > now and not (repeat == "weekdays" and time.localtime(when).tm_wday >= 5):
            return when


def add_reminder(at, text, repeat=""):
    if repeat and repeat not in REPEATS:
        raise ValueError(f"repeat is one of {', '.join(REPEATS)}")
    r = {"id": uuid.uuid4().hex[:8], "at": float(at), "text": " ".join(str(text).split()), **({"repeat": repeat} if repeat else {})}
    with _lock:
        write_json(REMINDERS_FILE, read_json(REMINDERS_FILE, []) + [r], private=True)
    return r


def cancel_reminder(rid):
    with _lock:
        rs = read_json(REMINDERS_FILE, [])
        write_json(REMINDERS_FILE, [r for r in rs if r["id"] != rid], private=True)
    return len(rs) != len(reminders())


def pop_due(now=None):
    """Remove and return reminders whose time has come (repeating ones move on to their next time instead)."""
    now = now or time.time()
    with _lock:
        rs = read_json(REMINDERS_FILE, [])
        due = [r for r in rs if r["at"] <= now]
        if due:
            later = [r for r in rs if r["at"] > now] + [{**r, "at": next_time(r["at"], r["repeat"], now)} for r in due if r.get("repeat")]
            write_json(REMINDERS_FILE, later, private=True)
    return due


# ---------------------------------------------------------------- routines: named sets of steps ("study mode")
ROUTINES_FILE = os.path.join(DATA, "routines.json")


def routines():
    return read_json(ROUTINES_FILE, {})


def save_routine(name, steps):
    name, steps = " ".join(str(name).lower().split()), str(steps).strip()
    if not name or not steps:
        raise ValueError("a routine needs a name and its steps")
    with _lock:
        write_json(ROUTINES_FILE, {**routines(), name: steps}, private=True)
    return name


def delete_routine(name):
    name = " ".join(str(name).lower().split())
    with _lock:
        rs = routines()
        found = rs.pop(name, None) is not None
        write_json(ROUTINES_FILE, rs, private=True)
    return found


# ---------------------------------------------------------------- deleting what Jarvis keeps
def delete_data():
    """Delete everything Jarvis keeps about the user on this PC: memory, conversations, reminders, routines, voice clips
    and the files behind Classroom and calendar reminders, model use and the log. Keys, account sign-ins and settings stay
    (they're removed on their own pages)."""
    import shutil
    with _lock:
        for path in (MEMORY_FILE, REMINDERS_FILE, ROUTINES_FILE, *(os.path.join(DATA, name) for name in (
                "usage.json", "deadlines.json", "calendar.json", "briefing.json", "jarvis.log.old"))):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
        for folder in ("sessions", "wake"):
            shutil.rmtree(os.path.join(DATA, folder), ignore_errors=True)
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        try:
            open(os.path.join(DATA, "jarvis.log"), "w").close()  # (emptied, not removed: it's open for writing)
        except OSError:
            pass


# ---------------------------------------------------------------- start at login
def sync_autostart(enabled):
    here = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, "frozen", False):  # the packaged app (Jarvis.exe): it starts itself
        command = f'"{sys.executable}"'
    elif system.IS_WINDOWS:  # pythonw: no console window
        command = f'"{os.path.join(os.path.dirname(sys.executable), "pythonw.exe")}" "{os.path.join(here, "jarvis.py")}"'
    else:
        command = os.path.expanduser("~/.local/bin/jarvis")  # made by install.sh
    system.set_autostart(enabled, command)


# ---------------------------------------------------------------- API keys: the OS keychain, or a private file without one
KEYS_FILE = os.path.join(CONFIG, "keys.json")  # only used when there's no keychain (e.g. no Secret Service on Linux)


def _keyring():
    try:
        import keyring
        from keyring.backends import fail
        return None if isinstance(keyring.get_keyring(), fail.Keyring) else keyring
    except Exception:
        return None


def key_storage():
    return "your system keychain" if _keyring() else f"a private file ({KEYS_FILE})"


def secret(name):
    """The API key saved for a provider, or ''."""
    kr = _keyring()
    try:
        value = kr.get_password("jarvis", name) if kr else None
    except Exception:  # keychain locked or unavailable right now
        value = None
    return value or read_json(KEYS_FILE, {}).get(name, "")


def set_secret(name, value):
    """Save (or with '' delete) a provider's key; never in settings.json."""
    kr = _keyring()
    with _lock:
        if kr:
            try:
                kr.delete_password("jarvis", name)
            except Exception:
                pass
            if value:
                kr.set_password("jarvis", name, value)
        keys = read_json(KEYS_FILE, {})
        keys.pop(name, None)
        if value and not kr:
            keys[name] = value
        if keys or os.path.exists(KEYS_FILE):
            write_json(KEYS_FILE, keys, private=True)


# ---------------------------------------------------------------- your own OpenAI-compatible providers (name -> base URL)
PROVIDERS_FILE = os.path.join(CONFIG, "providers.json")


def custom_providers():
    return read_json(PROVIDERS_FILE, {})


def save_custom_provider(name, url):
    """Add a provider (or with url '' remove it)."""
    with _lock:
        p = custom_providers()
        p.pop(name, None) if not url else p.update({name: url})
        write_json(PROVIDERS_FILE, p)


# ---------------------------------------------------------------- what Jarvis may do with each connected account
CONNECTOR_MODES = ("ask", "full", "read_only", "paused")  # ask: confirm before changes (the default)
CONNECTORS_FILE = os.path.join(CONFIG, "connectors.json")


def connector_modes():
    return read_json(CONNECTORS_FILE, {})


def set_connector_mode(slug, mode):
    if mode not in CONNECTOR_MODES:
        raise ValueError(f"mode must be one of {', '.join(CONNECTOR_MODES)}")
    with _lock:
        modes = connector_modes()
        modes.pop(slug, None) if mode == "ask" else modes.update({slug: mode})
        write_json(CONNECTORS_FILE, modes)


# ---------------------------------------------------------------- plugins (MCP servers)
PLUGINS_FILE = os.path.join(CONFIG, "plugins.json")


def plugins():
    return read_json(PLUGINS_FILE, DEFAULT_PLUGINS)


def save_plugins(p):
    with _lock:
        write_json(PLUGINS_FILE, p, private=True)  # may hold API keys in headers/env


# ---------------------------------------------------------------- sessions
SESSIONS_DIR = os.path.join(DATA, "sessions")


def recall(query, limit=5):
    """Past conversations about something, newest first: when, the title, and the lines that mention it (with what was
    said just before and after, so a reply makes sense)."""
    words = [w for w in query.lower().split() if len(w) > 2] or [query.lower().strip()]
    found = []
    for name in os.listdir(SESSIONS_DIR) if os.path.isdir(SESSIONS_DIR) else []:
        s = read_json(os.path.join(SESSIONS_DIR, name), None) if name.endswith(".json") else None
        if not s:
            continue
        talk = [m for m in s.get("messages", []) if m.get("who") in ("you", "jarvis")]
        hits = [i for i, m in enumerate(talk) if all(w in str(m.get("text", "")).lower() for w in words)]
        if hits:
            near = sorted({j for i in hits[:3] for j in (i - 1, i, i + 1) if 0 <= j < len(talk)})
            found.append({"when": time.strftime("%a %d %b %Y, %H:%M", time.localtime(s.get("updated", 0))), "updated": s.get("updated", 0),
                          "title": s.get("title", ""), "lines": [f"{talk[j]['who']}: {str(talk[j]['text'])[:300]}" for j in near]})
    found.sort(key=lambda f: -f["updated"])
    return [{k: v for k, v in f.items() if k != "updated"} for f in found[:limit]]


class Sessions:
    """Each conversation is a JSON file: what was said (for the app) plus the agent's own history."""

    def __init__(self):
        os.makedirs(DATA, mode=0o700, exist_ok=True)
        os.chmod(DATA, 0o700)  # conversations, logs, voice clips and tokens: this user only
        self.dir = SESSIONS_DIR
        os.makedirs(self.dir, exist_ok=True)
        self.new()

    def _path(self, sid):
        if not sid.replace("-", "").isalnum():  # ids come from the app's URLs
            raise ValueError("bad session id")
        return os.path.join(self.dir, f"{sid}.json")

    def new(self):
        self.current = {"id": time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6], "title": "New conversation",
                        "created": time.time(), "updated": time.time(), "messages": [], "agent": []}

    @property
    def messages(self):
        return self.current["messages"]

    def add(self, msg):
        with _lock:
            s = self.current
            s["messages"].append({**msg, "time": time.time()})
            if msg.get("who") == "you" and s["title"] == "New conversation":
                s["title"] = msg["text"][:60]
        self.save()

    def save(self, agent=None):
        with _lock:  # voice, agent and app threads all write to the current session
            s = self.current
            if agent is not None:  # the agent's Gemini history, minus screenshots (big, and stale anyway)
                s["agent"] = [{**m, "parts": [p for p in m["parts"] if "inlineData" not in p]} for m in agent]
            if not any(m.get("who") in ("you", "jarvis") for m in s["messages"]):
                return  # notices alone don't make a conversation worth listing
            s["updated"] = time.time()
            write_json(self._path(s["id"]), s, private=True)

    def _all(self):
        """Every saved conversation, as (its summary for the list, the whole thing)."""
        for name in os.listdir(self.dir):
            s = read_json(os.path.join(self.dir, name), None) if name.endswith(".json") else None
            if s:
                yield {"id": s["id"], "title": s["title"], "updated": s["updated"],
                       "count": sum(m.get("who") in ("you", "jarvis") for m in s["messages"])}, s

    def list(self):
        return sorted((summary for summary, _ in self._all()), key=lambda s: -s["updated"])

    def search(self, query):
        """Saved conversations whose title or messages contain the query (case-insensitive), newest first."""
        q, out = query.lower().strip(), []
        for summary, s in self._all():
            hits = [m["text"] for m in s["messages"] if q in str(m.get("text", "")).lower()]
            if q in s["title"].lower() or hits:
                out.append({**summary, "match": (hits[0] if hits else s["title"])[:160]})
        return sorted(out, key=lambda s: -s["updated"])

    def get(self, sid):
        s = read_json(self._path(sid), None)
        if not s:
            raise KeyError(sid)
        return s

    def open(self, sid):
        self.current = self.get(sid)
        return self.current

    def delete(self, sid):
        os.remove(self._path(sid))
        if self.current["id"] == sid:
            self.new()
