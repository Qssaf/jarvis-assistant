"""The people in the user's life: a page per person (notes, some with an end date; when they last wrote to each other on
WhatsApp or Discord; what the user promised them), and the promises spotted in what the user sends (Tracker).

people.json (DATA, owner-only): {"Sam Lee": {"aka": ["sam_"], "notes": [{"text", "at", "until"?}], "seen": {app: when
they last wrote}, "wrote": {app: when the user last wrote}, "promises": [{"what", "at", "due", "app", "reminder"}]}}."""
import json, os, re, threading, time

import store

FILE = os.path.join(store.DATA, "people.json")
PROMISE_DAYS = 7  # a promise with no time is on the evening list this long
_lock = threading.Lock()
tracker = [None]  # the app's Tracker (promises in what the user sends), filled in main()
_stamped = {}  # (name, app, me) -> when talked() last wrote it (a chatty DM doesn't rewrite the file every message)


def everyone():
    book = store.read_json(FILE, {})
    return book if isinstance(book, dict) else {}


def _key(book, name):
    """The page whose name or other name (a username) is name, case aside."""
    want = (name or "").strip().lower()
    return next((k for k, p in book.items() if want and (k.lower() == want or want in (a.lower() for a in p.get("aka", [])))), None)


def _update(name, change, aka=""):
    """Change a person's page (made if it's new) under the lock; returns the name it's kept under."""
    with _lock:
        book = everyone()
        key = _key(book, name) or _key(book, aka) or " ".join(name.split())
        page = book.setdefault(key, {})
        if aka and aka.lower() != key.lower() and aka.lower() not in (a.lower() for a in page.get("aka", [])):
            page.setdefault("aka", []).append(aka)
        change(page)
        store.write_json(FILE, book, private=True)
        return key


def talked(name, app, me, aka=""):
    """Someone wrote to the user (me=False) or the user to them, in a one-to-one chat."""
    if not name:
        return
    now, field = time.time(), "wrote" if me else "seen"
    if now - _stamped.get((name, app, me), 0) < 300:
        return
    _stamped[(name, app, me)] = now
    _update(name, lambda p: p.setdefault(field, {}).__setitem__(app, now), aka)


def add_note(name, text, until=0):
    text = " ".join(str(text).split())
    if not text:
        raise ValueError("say what to note about them")
    def add(p):
        notes = [n for n in p.get("notes", []) if n["text"].lower() != text.lower()]
        p["notes"] = notes + [{"text": text, "at": time.time(), **({"until": float(until)} if until else {})}]
    return _update(name, add)


def drop(name, text):
    """Forget a person's notes and promises containing text (all of the page with no text); returns how many went."""
    gone = [0]
    with _lock:
        book = everyone()
        key = _key(book, name)
        if not key:
            return 0
        if not text.strip():
            del book[key]
            gone[0] = 1
        else:
            p = book[key]
            for field in ("notes", "promises"):
                kept = [x for x in p.get(field, []) if text.lower() not in (x.get("text") or x.get("what", "")).lower()]
                gone[0] += len(p.get(field, [])) - len(kept)
                if field == "promises":
                    for x in p.get(field, []):
                        if x not in kept and x.get("reminder"):
                            store.cancel_reminder(x["reminder"])
                p[field] = kept
        store.write_json(FILE, book, private=True)
    return gone[0]


def _ago(t, now):
    s = now - t
    return "just now" if s < 120 else f"{int(s // 60)} min ago" if s < 3600 else f"{int(s // 3600)} h ago" if s < 86400 else f"{int(s // 86400)} days ago"


def page(name, now=None):
    """What Jarvis knows about someone: notes still true, when they last wrote each way, promises; None if nobody's page."""
    now = now or time.time()
    book = everyone()
    key = _key(book, name)
    if not key:
        return None
    p = book[key]
    out = {"name": key, **({"also": p["aka"]} if p.get("aka") else {}),
           "notes": [n["text"] + (f" (until {time.strftime('%d %b', time.localtime(n['until']))})" if n.get("until") else "")
                     for n in p.get("notes", []) if not n.get("until") or n["until"] > now]}
    for field, label in (("seen", "they last wrote"), ("wrote", "the user last wrote")):
        if p.get(field):
            out[label] = {app: _ago(t, now) for app, t in p[field].items()}
    promises = [x for x in p.get("promises", []) if _open(x, now)]
    if promises:
        out["promised"] = [x["what"] + (f" (due {time.strftime('%a %d %b %H:%M', time.localtime(x['due']))})" if x.get("due") else "")
                           for x in promises]
    return out


def _open(x, now):
    return (x.get("due") or x["at"] + PROMISE_DAYS * 86400) > now - 86400


def promises(now=None):
    """The user's open promises: [{"to", "what", "due"}], soonest first."""
    now = now or time.time()
    return sorted(({"to": k, "what": x["what"], "due": x.get("due", 0)} for k, p in everyone().items()
                   for x in p.get("promises", []) if _open(x, now)), key=lambda x: x["due"] or 9e9)


def index(now=None, limit=40):
    """One line per person with notes, for the prompts ("- Sam Lee: my cousin; exam on Friday")."""
    now = now or time.time()
    lines = []
    for k, p in sorted(everyone().items(), key=lambda kp: -max([n["at"] for n in kp[1].get("notes", [])] or [0])):
        notes = [n["text"] for n in p.get("notes", []) if not n.get("until") or n["until"] > now]
        if notes:
            lines.append(f"- {k}: {'; '.join(notes)}"[:200])
    return "\n".join(lines[:limit])


def tidy(now=None):
    """Notes past their end date and promises long past go (tidy_loop, once a day)."""
    now = now or time.time()
    with _lock:
        book = everyone()
        for p in book.values():
            p["notes"] = [n for n in p.get("notes", []) if not n.get("until") or n["until"] > now]
            p["promises"] = [x for x in p.get("promises", []) if _open(x, now)]
        store.write_json(FILE, book, private=True)


# ---------------------------------------------------------------- promises in what the user sends
# a message worth asking the model about: it speaks of later (most messages don't: "ok", "lol", a photo)
# ponytail: words for "later" in the languages Jarvis speaks most; a promise in other words is missed, never invented
HINT = re.compile(r"\b(?:i'?ll|i will|i'?m going to|i'?m gonna|gonna|let me|i promise|i owe|will (?:send|call|pay|do|finish|bring|check|get)"
                  r"|tomorrow|tmrw|tonight|later|next (?:week|time)|this (?:evening|weekend)|(?:on|by|before) (?:mon|tues|wednes|thurs|fri|satur|sun)day"
                  r"|by \d|after (?:class|school|work)|in an hour|in \d+ (?:min|hour))\b"
                  r"|سوف|سأ|بكرة|بكره|غدا|غداً|راح|رح |بعدين|demain|je vais|mañana|voy a|morgen|ich werde|domani", re.I)
PROMPT = """Below are messages {NAME} just sent to people. Find the ones where {NAME} commits to doing something later \
for that person (send, bring, call back, pay, finish, check, come over...). Ignore plans with no commitment, questions, \
jokes, things already done and things the other person will do. It is now {NOW}.

Answer with JSON only: a list of {{"to": the person's name exactly as written after "to", "what": what {NAME} will do, \
a few words in the message's language, as a reminder to {NAME} that names the person instead of "you" ("send Sam the \
notes"), "when": "YYYY-MM-DD HH:MM" when a day or time is said \
or clearly meant (a day with no time: 09:00 that day; "tonight": 20:00; "in an hour": that time), else ""}}, or [] if \
there are none.

The messages:
{LINES}"""


class Tracker:
    """Promises in the user's own messages (and ones Jarvis sent for them): a short wait gathers a burst into one
    model request, then each promise goes on the person's page, with a reminder when it has a time (the evening list has
    the rest). Only messages with a word for "later" (HINT) are asked about."""

    def __init__(self, brain, notify=print, name=lambda: "the user", wait=90):
        self.brain, self.notify, self.name, self.wait = brain, notify, name, wait
        self.queue, self.lock, self.timer = [], threading.Lock(), None

    def heard(self, app, who, text):
        if not who or not text or not store.settings()["track_promises"] or not HINT.search(text):
            return
        with self.lock:
            self.queue.append((app, who, " ".join(text.split())[:500]))
            if self.timer:
                self.timer.cancel()
            self.timer = threading.Timer(self.wait, self.flush)
            self.timer.daemon = True
            self.timer.start()

    def flush(self):
        with self.lock:
            if self.timer:
                self.timer.cancel()
            batch, self.queue, self.timer = self.queue, [], None
        if not batch:
            return []
        try:
            found = self.extract(batch)
        except Exception as e:  # (no model answering: these messages just aren't looked at)
            print(f"[people] couldn't look for promises: {e}", flush=True)
            return []
        return [kept for p in found if (kept := self._keep(p, batch))]

    def extract(self, batch):
        prompt = (PROMPT.replace("{NAME}", self.name()).replace("{NOW}", time.strftime("%A %d %B %Y, %H:%M"))
                  .replace("{LINES}", "\n".join(f"- on {app}, to {who}: {text}" for app, who, text in batch)))
        parts = self.brain._generate([{"role": "user", "parts": [{"text": prompt}]}])
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        m = re.search(r"\[.*\]", text, re.S)
        try:
            found = json.loads(m.group(0)) if m else []
        except ValueError:
            return []
        return [p for p in found if isinstance(p, dict) and isinstance(p.get("to"), str) and isinstance(p.get("what"), str)]

    def _keep(self, p, batch):
        said = re.sub(r"\s*\((?:whatsapp|discord|email)\)$", "", p["to"].strip(), flags=re.I).lower()  # (a model may copy the label)
        who = next((w for _, w, _ in batch if w.lower() == said), None)
        what = " ".join(p["what"].split())[:200]
        if not who or not what:
            return None
        app = next(a for a, w, _ in batch if w == who)
        due = 0.0
        try:
            due = time.mktime(time.strptime(str(p.get("when") or "").strip(), "%Y-%m-%d %H:%M"))
        except ValueError:
            pass
        now = time.time()
        due = due if due > now else 0.0
        book = everyone()
        page_now = book.get(_key(book, who) or "", {})
        if any(x["what"].lower() == what.lower() and now - x["at"] < 2 * 86400 for x in page_now.get("promises", [])):
            return None  # (said twice, or asked about twice)
        rid = store.add_reminder(due, f"🤝 You promised {who}: {what}")["id"] if due else ""
        _update(who, lambda pg: pg.setdefault("promises", []).append(
            {"what": what, "at": now, **({"due": due} if due else {}), "app": app, **({"reminder": rid} if rid else {})}))
        self.notify(f"🤝 Noted: you promised {who} to {what}" + (
            f". I'll remind you {time.strftime('%a %H:%M', time.localtime(due))}." if due else ". It's on your evening list.")
                    + " (Say \"forget that promise\" if it isn't one.)")
        return {"to": who, "what": what, "due": due}
