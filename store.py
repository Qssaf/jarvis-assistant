"""Jarvis's saved state: settings, plugins (MCP servers) and conversation sessions."""
import json, os, re, sys, threading, time, uuid

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

# openWakeWord's own pretrained wake phrases (it also ships "timer" and "weather", which aren't wake words)
WAKE_WORDS = {"hey_jarvis": "Hey Jarvis", "alexa": "Alexa", "hey_mycroft": "Hey Mycroft", "hey_rhasspy": "Hey Rhasspy"}

DEFAULT_SETTINGS = {
    "voice": "Charon",
    "language": "en-US",           # what Jarvis speaks and expects to hear (store.LANGUAGES)
    "languages": [],               # others it may speak and understand, when the user (or a WhatsApp contact) speaks them
    "text_size": 1.0,              # the window's text, 0.9-1.5 times the normal size
    "personality": "jarvis",       # how it talks: jarvis (British, dry wit), friendly or brief
    "live_model": "gemini-3.8-live",
    "follow_up_seconds": 8,
    "keep_session_seconds": 300,   # after that, the voice session stays connected (mic off) for an instant next "Hey Jarvis"
    "wake_threshold": 0.5,
    "wake_word": "hey_jarvis",     # one of WAKE_WORDS, or the full path of the user's own openWakeWord .onnx model
    "extra_instructions": "",
    "home_city": "",               # for the weather on the Chat page; empty = guess from your network
    "speak_typed_replies": True,   # off: typed messages get text-only answers
    "always_backup_voice": False,  # on: the backup voice (the hear and speak models) answers instead of Gemini Live
    "fast_voice": False,           # on: the voice model answers without thinking first (~0.3 s quicker, but less sharp)
    "end_of_speech_ms": 600,       # pause that counts as "finished talking"; lower = snappier, higher = fewer cut-offs
    "start_at_login": False,
    "show_thinking": False,        # the chat shows the agent's thinking and the voice model's decisions (never the notch)
    "morning_briefing": True,      # the first time Jarvis starts in a morning, it gives the day's briefing out loud
    "do_not_disturb": False,       # on: Jarvis never speaks up on its own (see quiet_now); it still answers the user
    "quiet_from": "", "quiet_until": "",  # quiet hours, "22:00" to "07:00" (crossing midnight); empty = none
    "deadline_reminders": True,    # reminders a day and two hours before Google Classroom work is due
    "calendar_reminders": True,    # a reminder ten minutes before each Google Calendar event
    "checks": [],                  # things Jarvis keeps an eye on in the background ("tell me if a payment fails"), one per line
    "checks_every": 60,            # minutes between those checks (each one is a few agent requests)
    "checks_paused": [],           # checks switched off in the window (kept, but not looked into)
    "whatsapp_replies": "contacts",  # contacts: Jarvis answers saved contacts' messages that don't need you; off: just shows them
    "whatsapp_calls": "answer",    # answer: picks up contacts' calls you don't and takes a message; decline; off: lets them ring
    "whatsapp_note": "",           # what Jarvis tells people on WhatsApp ("I'm in class until 5")
    "whatsapp_always": [],         # names Jarvis never answers for and always tells the user about out loud (even in quiet hours)
    "whatsapp_never": [],          # names Jarvis never answers for or speaks about: only shown in the chat
    "echo_cancel": False,          # echo cancelling (PipeWire on Linux, WebRTC + a speaker loopback on Windows): talk over Jarvis on speakers (experimental)
    "learn_my_voice": True,        # learn from real wake-ups to ignore things that aren't you saying the wake word
    "only_my_voice": False,        # on (once learned): the wake word wakes Jarvis only when the learned verifier is sure it's you
    "safety": "ask",               # ask: risky commands and account changes wait for your yes; full: Jarvis just does them
    "setup_done": False,           # the first-run setup has been gone through (or skipped)
    # "backend model thinking-level", tried top to bottom; busy or rate-limited ones are skipped
    # the same for the other jobs (see brain.MODEL_JOBS); empty = Jarvis's built-in choice
    "look_models": [], "point_models": [], "point_strong_models": [], "search_models": [], "image_models": [],
    "hear_models": [], "speak_models": [],
    "agent_models": [
        "antigravity gemini-3.8-flash low",  # (only when signed in with Google, on the Models page)
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
    tmp = f"{path}.{threading.get_ident()}.tmp"  # (its own: two threads saving one file at once never mix their writes)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600 if private else 0o644)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, path)  # atomic: a crash never leaves half a file


# ---------------------------------------------------------------- settings
SETTINGS_FILE = os.path.join(CONFIG, "settings.json")


def settings():
    saved = read_json(SETTINGS_FILE, {})
    if saved.get("call_language") in LANGUAGES and "languages" not in saved:  # (2.0's one extra language for calls)
        saved["languages"] = [saved["call_language"]]
    return {**DEFAULT_SETTINGS, **{k: v for k, v in saved.items() if k in DEFAULT_SETTINGS}}  # (minus retired ones)


def spoken(cfg):
    """The languages Jarvis speaks and understands, by name, the main one first (English and English (UK) are one)."""
    return list(dict.fromkeys(LANGUAGES[c].split(" (")[0] for c in [cfg["language"], *cfg["languages"]]))


def wake_phrase(cfg=None):
    """What the user says to wake Jarvis: a built-in phrase, or what their own model's file is called
    ("hey_computer_v0.1.onnx": "Hey Computer")."""
    word = (cfg or settings())["wake_word"]
    stem = re.sub(r"_v\d[\w.]*$", "", os.path.splitext(os.path.basename(word))[0])
    return WAKE_WORDS.get(word) or " ".join(stem.replace("-", "_").split("_")).title()


def quiet_now(cfg=None, now=None):
    """Do not disturb, or within quiet hours: Jarvis doesn't speak up on its own (what the user asks is still answered)."""
    cfg = cfg or settings()
    start, end = cfg["quiet_from"], cfg["quiet_until"]
    if cfg["do_not_disturb"]:
        return True
    if not start or not end:
        return False
    t = time.strftime("%H:%M", time.localtime(now))
    return start <= t < end if start <= end else t >= start or t < end  # ("22:00" to "07:00" crosses midnight)


def update_settings(changes):
    """Validate and save; returns the new settings. Raises ValueError on bad input."""
    with _lock:  # (read and written together: two changes at once, from the window and a tool, both stick)
        return _update_settings(changes)


def _update_settings(changes):
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
        if key == "wake_word" and value not in WAKE_WORDS:
            value = os.path.abspath(os.path.expanduser(value.strip()))
            if not (value.lower().endswith(".onnx") and os.path.isfile(value)):
                raise ValueError("the wake word is one of the list, or the full path of your own openWakeWord .onnx model")
        if key == "follow_up_seconds" and not 0 <= value <= 120:
            raise ValueError("follow-up must be 0-120 seconds")
        if key == "keep_session_seconds" and not 0 <= value <= 600:
            raise ValueError("keep the session 0-600 seconds")
        if key == "text_size" and not 0.9 <= value <= 1.5:
            raise ValueError("text size must be 0.9-1.5")
        if key == "personality" and value not in ("jarvis", "friendly", "brief"):
            raise ValueError("personality is jarvis, friendly or brief")
        if key == "language" and value not in LANGUAGES:
            raise ValueError(f"language is one of {', '.join(LANGUAGES)}")
        if key == "safety" and value not in ("ask", "full"):
            raise ValueError("safety is ask or full")
        if key == "end_of_speech_ms" and not 200 <= value <= 2000:
            raise ValueError("the pause must be 200-2000 ms")
        if key == "checks_every" and not 15 <= value <= 1440:
            raise ValueError("check every 15-1440 minutes")
        if key == "whatsapp_replies" and value not in ("contacts", "off"):
            raise ValueError("WhatsApp replies are contacts or off")
        if key == "languages":
            if any(v not in LANGUAGES for v in value):
                raise ValueError(f"languages are from {', '.join(LANGUAGES)}")
            value = list(dict.fromkeys(value))
        if key in ("quiet_from", "quiet_until") and value:
            hm = re.fullmatch(r"(\d{1,2})[:.](\d{2})", value.strip())
            if not hm or int(hm[1]) > 23 or int(hm[2]) > 59:
                raise ValueError("quiet hours are times like 22:00, or empty")
            value = f"{int(hm[1]):02d}:{hm[2]}"  # (so they compare as text)
        if key == "whatsapp_calls" and value not in ("answer", "decline", "off"):
            raise ValueError("WhatsApp calls are answer, decline or off")
        s[key] = value
    if {n.lower() for n in s["whatsapp_always"]} & {n.lower() for n in s["whatsapp_never"]}:
        raise ValueError("a name can't be both always let through and never answered")
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


def add_reminder(at, text, repeat="", task=False, on=True, rid=""):
    """task: at that time the agent does what text says (instead of Jarvis just saying it). on=False: paused (its times
    pass without it; only a repeating one, or a one-off would just be lost). rid: change that reminder instead of adding one."""
    text = " ".join(str(text).split())
    if not text:
        raise ValueError("say what the reminder is for")
    if repeat and repeat not in REPEATS:
        raise ValueError(f"repeat is one of {', '.join(REPEATS)}")
    r = {"id": rid or uuid.uuid4().hex[:8], "at": float(at), "text": text, **({"repeat": repeat} if repeat else {}),
         **({"task": True} if task else {}), **({"off": True} if not on and repeat else {})}
    with _lock:
        rs = read_json(REMINDERS_FILE, [])
        if rid and not any(x["id"] == rid for x in rs):
            raise ValueError("that reminder has already gone off or been cancelled")
        write_json(REMINDERS_FILE, [x for x in rs if x["id"] != rid] + [r], private=True)
    return r


def cancel_reminder(rid):
    with _lock:
        rs = read_json(REMINDERS_FILE, [])
        write_json(REMINDERS_FILE, [r for r in rs if r["id"] != rid], private=True)
    return len(rs) != len(reminders())


def pop_due(now=None):
    """Remove and return reminders whose time has come (repeating ones move on to their next time instead; paused ones
    aren't returned)."""
    now = now or time.time()
    with _lock:
        rs = read_json(REMINDERS_FILE, [])
        due = [r for r in rs if r["at"] <= now]
        if due:
            later = [r for r in rs if r["at"] > now] + [{**r, "at": next_time(r["at"], r["repeat"], now)} for r in due if r.get("repeat")]
            write_json(REMINDERS_FILE, later, private=True)
    return [r for r in due if not r.get("off")]


# ---------------------------------------------------------------- routines: named sets of steps ("study mode")
ROUTINES_FILE = os.path.join(DATA, "routines.json")


def routines():
    return read_json(ROUTINES_FILE, {})


def save_routine(name, steps, old="", new=False):
    """old: the name it had (renamed in the window). new: added in the window (not over one with that name)."""
    name, steps, old = " ".join(str(name).lower().split()), str(steps).strip(), " ".join(str(old).lower().split())
    if not name or not steps:
        raise ValueError("a routine needs a name and its steps")
    with _lock:
        rs = routines()
        if (new or old and old != name) and name in rs:
            raise ValueError(f"there's already a routine called {name}")
        rs.pop(old, None)
        write_json(ROUTINES_FILE, {**rs, name: steps}, private=True)
    return name


def delete_routine(name):
    name = " ".join(str(name).lower().split())
    with _lock:
        rs = routines()
        found = rs.pop(name, None) is not None
        write_json(ROUTINES_FILE, rs, private=True)
    return found


# ---------------------------------------------------------------- checks: what Jarvis keeps an eye on (in the settings)
def save_check(text, old="", on=True):
    """Add a check, or change the one that now says old (in its place); on=False pauses it, no text deletes it."""
    text, old = " ".join(str(text).split()), " ".join(str(old).split())
    if not text and not old:
        raise ValueError("say what to keep an eye on")
    with _lock:  # (read and written together, like update_settings)
        s = settings()
        lists = {True: s["checks"], False: s["checks_paused"]}
        at = len(lists[on])
        if old:
            was = next((k for k, l in lists.items() if old in l), None)
            if was is None:
                raise ValueError("that check is gone already")
            if was == on:
                at = lists[on].index(old)
            lists[was].remove(old)
        if text and text not in lists[True] + lists[False]:
            lists[on].insert(at, text)
        return _update_settings({"checks": lists[True], "checks_paused": lists[False]})


# ---------------------------------------------------------------- what Jarvis changed (for "undo that")
CHANGES_FILE = os.path.join(DATA, "changes.json")


def log_change(what):
    with _lock:
        write_json(CHANGES_FILE, (read_json(CHANGES_FILE, []) + [{"at": time.time(), "what": str(what)[:500]}])[-200:], private=True)


def changes(limit=15):
    """The latest changes Jarvis made, newest first."""
    return [{"when": time.strftime("%a %d %b %H:%M", time.localtime(c["at"])), "what": c["what"]}
            for c in reversed(read_json(CHANGES_FILE, [])[-limit:])]


# ---------------------------------------------------------------- deleting what Jarvis keeps
def delete_data():
    """Delete everything Jarvis keeps about the user on this PC: memory, conversations, reminders, routines, voice clips
    and the files behind Classroom and calendar reminders, model use and the log. Keys, account sign-ins and settings stay
    (they're removed on their own pages)."""
    import shutil
    with _lock:
        for path in (MEMORY_FILE, REMINDERS_FILE, ROUTINES_FILE, CHANGES_FILE, *(os.path.join(DATA, name) for name in (
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


PASSPHRASE = "voice_passphrase"  # (a secret like a key: the keychain, never settings.json or the log)


def _passphrase():
    """The spoken passphrase as a pattern that forgives case, punctuation and spacing ("Blue-bird" is "bluebird"), or None."""
    chars = re.sub(r"[\W_]", "", secret(PASSPHRASE).lower())
    return re.compile(r"(?<!\w)" + r"[\W_]*".join(map(re.escape, chars)) + r"(?!\w)", re.I) if chars else None


def said_passphrase(text):
    p = _passphrase()
    return bool(p and p.search(text or ""))


def hide_passphrase(text):
    p = _passphrase()
    return p.sub("•••", text) if p and text else text


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


def recall(query="", limit=5, day=""):
    """Past conversations about something, newest first: when, the title, and the lines that mention it (with what was
    said just before and after, so a reply makes sense). day ("YYYY-MM-DD"): only that day's, and without a query, how
    each of them started."""
    words = [w for w in query.lower().split() if len(w) > 2] or ([query.lower().strip()] if query.strip() else [])
    found = []
    for name in os.listdir(SESSIONS_DIR) if os.path.isdir(SESSIONS_DIR) else []:
        s = read_json(os.path.join(SESSIONS_DIR, name), None) if name.endswith(".json") else None
        if not s:
            continue
        if day and day not in {time.strftime("%Y-%m-%d", time.localtime(s.get(k) or 0)) for k in ("created", "updated")}:
            continue
        talk = [m for m in s.get("messages", []) if m.get("who") in ("you", "jarvis")]
        hits = [i for i, m in enumerate(talk) if all(w in str(m.get("text", "")).lower() for w in words)] if words else \
            list(range(min(len(talk), 2)))
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

    def sent(self, limit=15):
        """What Jarvis said it typed and sent lately (its "Sent: ..." lines) in the newest conversations, oldest first: a
        new voice session sees them, so it doesn't send the same joke again."""
        names = sorted(n for n in os.listdir(self.dir) if n.endswith(".json"))[-10:]  # (ids start with the date)
        out = [m["text"][5:].strip() for n in names for m in (read_json(os.path.join(self.dir, n), None) or {}).get("messages", [])
               if m.get("who") == "jarvis" and str(m.get("text", "")).startswith("Sent:")]
        return out[-limit:]

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


# ---------------------------------------------------------------- moving to another computer: one .zip, never a secret
BACKUP_FORMAT = 1
BACKUP_LIMIT = 512 << 20  # unpacked bytes (years of chats and every wake-word clip are far less)
# conversations, and the wake-word clips (not the verifier: it's a pickle, so loading one from a file would run its code)
BACKUP_FOLDERS = re.compile(r'sessions/[A-Za-z0-9-]{1,80}\.json|wake/(?:(?!\.\.?/)[^/\\:*?"<>|\x00-\x1f]{1,100}/)?(?:yes|no)/\d{1,12}(?:\.\d{1,6})?\.wav')


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


BACKUP_CHECKS = {  # what a sound file looks like, so a bad one can't break a loop after the restart
    "settings.json": lambda d: isinstance(d, dict),
    "reminders.json": lambda d: isinstance(d, list) and all(
        isinstance(r, dict) and isinstance(r.get("id"), str) and _number(r.get("at")) and isinstance(r.get("text"), str)
        and r.get("repeat", "") in ("", *REPEATS) for r in d),
    "routines.json": lambda d: isinstance(d, dict) and all(isinstance(v, str) for v in d.values()),
    "changes.json": lambda d: isinstance(d, list) and all(isinstance(c, dict) and _number(c.get("at")) and isinstance(c.get("what"), str) for c in d),
    "plugins.json": lambda d: isinstance(d, dict) and all(  # (headers and env may hold API keys: a backup never has them)
        re.fullmatch(r"[a-z0-9_-]{1,32}", n) and isinstance(p, dict) and isinstance(p.get("url") or p.get("command"), str)
        and not {"headers", "env"} & set(p) for n, p in d.items()),
    "connectors.json": lambda d: isinstance(d, dict) and all(v in CONNECTOR_MODES for v in d.values()),
    "providers.json": lambda d: isinstance(d, dict) and all(
        re.fullmatch(r"[a-z0-9_]{1,24}", n) and isinstance(v, str) and v.startswith(("https://", "http://")) for n, v in d.items()),
}


def _backup_files():
    """Name in the backup -> the file on this PC (looked up each time: tests point them elsewhere)."""
    return {"settings.json": SETTINGS_FILE, "memory.md": MEMORY_FILE, "reminders.json": REMINDERS_FILE, "routines.json": ROUTINES_FILE,
            "changes.json": CHANGES_FILE, "plugins.json": PLUGINS_FILE, "connectors.json": CONNECTORS_FILE, "providers.json": PROVIDERS_FILE}


def export_data(path, version):
    """Save settings (with the checks), memory, reminders and scheduled tasks, routines, plugins, account modes, providers,
    the change log, conversations and wake-word clips to a .zip; returns how many files it holds. Never keys, sign-ins,
    WhatsApp or the phone's pairing: they're in the keychain or in files this leaves out."""
    import zipfile
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_BINARY", 0), 0o600)  # (it's as private as what it holds)
    with os.fdopen(fd, "wb") as f, zipfile.ZipFile(f, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps({"format": BACKUP_FORMAT, "jarvis": version, "made": time.time()}))
        for name, file in _backup_files().items():
            if not os.path.exists(file):
                continue
            if name == "plugins.json":
                z.writestr(name, json.dumps({n: {k: v for k, v in p.items() if k not in ("headers", "env")} for n, p in plugins().items()}, indent=1))
            elif name == "settings.json":  # (as read: a 2.0 call_language comes as languages)
                z.writestr(name, json.dumps({k: v for k, v in settings().items() if v != DEFAULT_SETTINGS[k]}, indent=1))
            else:
                z.write(file, name)
        for inside, folder in (("sessions", SESSIONS_DIR), ("wake", os.path.join(DATA, "wake"))):
            for root, _, files in os.walk(folder):
                for f in files:
                    name = f"{inside}/{os.path.relpath(os.path.join(root, f), folder).replace(os.sep, '/')}"
                    if BACKUP_FOLDERS.fullmatch(name):
                        z.write(os.path.join(root, f), name)
        return len(z.namelist()) - 1


def import_data(path, taken=()):
    """Replace this PC's settings, memory, reminders, routines, plugins, account modes, providers, change log and wake-word
    clips with a backup's, and add its conversations. All of it is checked first: anything that isn't a sound Jarvis
    backup raises ValueError with nothing changed. taken: the built-in providers' names (a backup's can't replace them).
    Returns the settings this PC couldn't take (e.g. a wake-word file not here)."""
    import shutil, zipfile
    try:
        z = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile):
        raise ValueError("that isn't a Jarvis backup (a .zip)")
    with z:
        infos = z.infolist()
        if len(infos) > 20000 or sum(i.file_size for i in infos) > BACKUP_LIMIT:
            raise ValueError("that's too big to be a Jarvis backup")
        if "manifest.json" not in z.namelist():
            raise ValueError("that isn't a Jarvis backup (it has no manifest)")
        for i in infos:  # only the names Jarvis writes: no ../, no absolute paths, no keys or sign-ins
            if i.filename not in ("manifest.json", *_backup_files()) and not BACKUP_FOLDERS.fullmatch(i.filename):
                raise ValueError(f"the backup holds {i.filename[:80]}, which a Jarvis backup never does")
        try:
            files = {i.filename: z.read(i) for i in infos}
        except Exception as e:  # (a bad checksum, an odd compression or a password)
            raise ValueError(f"the backup is damaged ({e})")

    def parsed(name):
        try:
            return json.loads(files[name])
        except ValueError:
            raise ValueError(f"the backup's {name} is damaged")
    made = parsed("manifest.json")
    made = made.get("format") if isinstance(made, dict) else None
    if made != BACKUP_FORMAT:
        raise ValueError("that backup is from a newer Jarvis: update this one first" if _number(made) and made > BACKUP_FORMAT
                         else "that isn't a Jarvis backup")
    data = {n: parsed(n) for n in files if n.endswith(".json") and n != "manifest.json"}
    for n, d in data.items():
        ok = BACKUP_CHECKS[n](d) if n in BACKUP_CHECKS else isinstance(d, dict) and d.get("id") == n[9:-5] and \
            isinstance(d.get("title"), str) and _number(d.get("updated")) and isinstance(d.get("messages"), list)
        if not ok:
            raise ValueError(f"the backup's {n} isn't right")
    if set(data.get("providers.json", {})) & set(taken):  # (it would get this PC's key for that provider)
        raise ValueError("the backup's providers.json replaces a built-in provider")
    try:
        notes = files.get("memory.md", b"").decode()
    except UnicodeDecodeError:
        raise ValueError("the backup's memory.md is damaged")
    if any(n.endswith(".wav") and not b.startswith(b"RIFF") for n, b in files.items()):
        raise ValueError("the backup's wake-word clips are damaged")

    for name, file in _backup_files().items():  # (one the backup hasn't: that PC had none either)
        if name in ("settings.json", "memory.md"):
            continue
        if name == "plugins.json" and name in data:  # this PC's keys and sign-ins only go where they went before
            here = plugins()
            for n, p in data[name].items():
                h, token = here.get(n, {}), os.path.join(DATA, "mcp", f"{n}.json")
                if (p.get("url"), p.get("command")) == (h.get("url"), h.get("command")):
                    p.update({k: h[k] for k in ("headers", "env") if k in h})
                elif h and os.path.exists(token):  # (signed in here: the backup's address would get that sign-in)
                    data[name][n] = h
                else:
                    if os.path.exists(token):  # (a sign-in left by a plugin removed here)
                        os.remove(token)
                    if p.get("command"):  # a command from a backup runs only once the user turns it on (Plugins page)
                        p["enabled"] = False
        if name in data:
            write_json(file, data[name], private=True)
        elif os.path.exists(file):
            os.remove(file)
    set_memory(notes)
    for n, d in data.items():
        if n.startswith("sessions/"):
            write_json(os.path.join(SESSIONS_DIR, n[9:]), d, private=True)
    shutil.rmtree(os.path.join(DATA, "wake"), ignore_errors=True)  # (the voice is learned again from these clips)
    for n, b in files.items():
        if n.endswith(".wav"):
            os.makedirs(os.path.dirname(os.path.join(DATA, *n.split("/"))), exist_ok=True)
            with open(os.path.join(DATA, *n.split("/")), "wb") as f:
                f.write(b)
    if os.path.exists(SETTINGS_FILE):  # settings last, each through the Settings page's checks
        os.remove(SETTINGS_FILE)
    skipped = []
    for k, v in data.get("settings.json", {}).items():
        try:
            update_settings({k: v})
        except Exception:  # (any value the checks refuse, e.g. 1e999 for a number)
            skipped.append(k)
    return skipped
