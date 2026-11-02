"""Screen history (Settings → screen_history, off by default): which window was in front and when, so "what was that site
I had open yesterday?" has an answer. Only the app and the window's title, read every POLL seconds (a few milliseconds
each: no screenshots, no text recognition), kept on this PC in DATA/activity/<day>.jsonl and never in backups. Private
browsing and password managers are skipped; days go after keep_days (14 when that keeps everything)."""
import json, os, re, time

import store
import system

FOLDER = os.path.join(store.DATA, "activity")
POLL = 10
KEEP_DAYS = 14
PRIVATE = re.compile(r"private browsing|incognito|inprivate|keepass|bitwarden|1password|password manager|kwallet|seahorse", re.I)


def _day(t):
    return time.strftime("%Y-%m-%d", time.localtime(t))


def loop():
    """Write a line when the focused window changes (and every five minutes on the same one, so spans have an end)."""
    last, written = None, 0.0
    while True:
        if not store.settings()["screen_history"]:
            last = None
            time.sleep(60)
            continue
        try:
            app, title = system.focused()
        except Exception:
            app = title = ""
        now = time.time()
        if PRIVATE.search(f"{app} {title}") or app.lower() == "jarvis":
            app, title = "", ""
        if (app, title) != last or (title and now - written > 300):
            last, written = (app, title), now
            os.makedirs(FOLDER, mode=0o700, exist_ok=True)
            fd = os.open(os.path.join(FOLDER, f"{_day(now)}.jsonl"), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            with os.fdopen(fd, "a", encoding="utf-8") as f:
                f.write(json.dumps({"t": round(now), "app": app, "title": title[:300]}, ensure_ascii=False) + "\n")
        time.sleep(POLL)


def _read(day):
    try:
        with open(os.path.join(FOLDER, f"{day}.jsonl"), encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except (OSError, ValueError):
        return []


def spans(day):
    """A day as [(from, to, app, title)]: one per stretch on the same window (gaps: nothing in front, or Jarvis off)."""
    rows, out = _read(day), []
    for i, r in enumerate(rows):
        end = rows[i + 1]["t"] if i + 1 < len(rows) else r["t"] + 60
        end = min(end, r["t"] + 360)  # (no line for longer than that: Jarvis or the PC was off)
        if out and out[-1][2:] == (r["app"], r["title"]) and r["t"] - out[-1][1] < 30:
            out[-1] = (out[-1][0], end, r["app"], r["title"])
        elif r["title"]:
            out.append((r["t"], end, r["app"], r["title"]))
    return out


def search(query="", day="", limit=40):
    """Windows whose title or app has all of query's words (the last KEEP_DAYS days, newest first), or one day's timeline."""
    if not store.settings()["screen_history"] and not os.path.isdir(FOLDER):
        return {"error": "screen history is off: the user can turn it on in Settings → Privacy (it keeps window titles only)"}
    days = [day] if day else sorted((n[:-6] for n in os.listdir(FOLDER) if n.endswith(".jsonl")), reverse=True)[:KEEP_DAYS] \
        if os.path.isdir(FOLDER) else []
    words = [w.lower() for w in query.split()]
    found, seen = [], set()
    for d in days:
        for start, end, app, title in reversed(spans(d)):
            if words and not all(w in f"{app} {title}".lower() for w in words):
                continue
            if not day and (app, title) in seen:  # (a search: each window once, its latest time)
                continue
            seen.add((app, title))
            found.append(f"{time.strftime('%a %d %b %H:%M', time.localtime(start))}–{time.strftime('%H:%M', time.localtime(end))} "
                         f"{app}: {title}")
            if len(found) >= limit:
                return {"windows": found, "note": "more matched: ask with more words or a day"}
    return {"windows": found} if found else {"windows": [], "note": "nothing matched in the screen history"}


def tidy(now=None):
    """Days older than keep_days go (KEEP_DAYS when keep_days keeps everything)."""
    now = now or time.time()
    days = store.settings()["keep_days"] or KEEP_DAYS
    if not os.path.isdir(FOLDER):
        return
    for name in os.listdir(FOLDER):
        if name.endswith(".jsonl") and name[:-6] < _day(now - days * 86400):
            try:
                os.remove(os.path.join(FOLDER, name))
            except OSError:
                pass
