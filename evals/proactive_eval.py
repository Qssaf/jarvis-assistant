"""Does Jarvis notice what the user promised, and only that? Made-up messages the user "sent" go through the real
people.Tracker.extract (its prompt) on your configured models; nothing is saved, no reminder is set, no account is
touched. One model request per case:

    .venv/bin/python evals/proactive_eval.py                 # every case, your agent models
    EVAL_MODELS="aistudio gemini-3.8-flash low" .venv/bin/python evals/proactive_eval.py tomorrow arabic
"""
import os, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import brain, people  # noqa: E402

tomorrow = time.strftime("%Y-%m-%d", time.localtime(time.time() + 86400))
today = time.strftime("%Y-%m-%d")


def one(to, words, day=None):
    """A check: exactly one promise, to that person, mentioning one of words, due that day (or with no time: "")."""
    def check(found):
        if len(found) != 1:
            return f"{len(found)} promises, not 1"
        p = found[0]
        if p["to"].lower() != to.lower():
            return f"to {p['to']}"
        if not any(w in p["what"].lower() for w in words):
            return f"what: {p['what']}"
        when = str(p.get("when") or "")
        if day is not None and not when.startswith(day):
            return f"when: {when or 'none'}"
        return ""
    return check


def none(found):
    return f"invented {len(found)}: {found[0]['what']}" if found else ""


# name: (messages as (app, to, text), check(found) -> problem or "")
CASES = {
    "tomorrow": ([("whatsapp", "Sam", "ok I'll send you the notes tomorrow morning")], one("Sam", ["note"], tomorrow)),
    "tonight": ([("discord", "Maya", "I'll call you tonight, promise")], one("Maya", ["call"], today)),
    "later": ([("whatsapp", "Alex", "let me check and get back to you later")], one("Alex", ["check", "get back", "answer", "reply"], "")),
    "question": ([("discord", "Maya", "will you be at the party tomorrow?")], none),
    "done": ([("whatsapp", "Sam", "I sent it already lol, check your email")], none),
    "theirs": ([("whatsapp", "Sam", "you'll bring the charger tomorrow right? don't forget")], none),
    "vague_plan": ([("discord", "Alex", "we should hang out sometime next week")], none),
    "batch": ([("whatsapp", "Sam", "haha yeah"), ("whatsapp", "Omar", "I'll pay you back on friday, sorry"),
               ("discord", "Maya", "gonna sleep now, later")], one("Omar", ["pay", "money", "back"])),
    "arabic": ([("whatsapp", "Omar", "بكرة بجيبلك الكتاب ان شاء الله")], one("Omar", ["كتاب", "book"], tomorrow)),
}

if __name__ == "__main__":
    entries = [brain.entry(line) for line in os.environ["EVAL_MODELS"].split(",")] if os.environ.get("EVAL_MODELS") else brain.chain()
    b = brain.Brain.__new__(brain.Brain)
    b.backends, b.down_until, b.contents, b.cancel, b.notify = {}, {}, [], threading.Event(), (lambda text: None)
    generate = b._generate
    b._generate = lambda contents, **kw: generate(contents, entries=entries)
    tracker = people.Tracker(b, name=lambda: "Sam's friend")
    picked = [c for c in CASES if not sys.argv[1:] or c in sys.argv[1:]]
    passed = 0
    for name in picked:
        messages, check = CASES[name]
        started = time.time()
        try:
            found = tracker.extract(messages)
            problem = check(found)
        except Exception as e:
            found, problem = [], f"failed: {e}"
        passed += not problem
        print(f"{'PASS' if not problem else 'FAIL'} {name:12} {time.time() - started:4.1f}s  {found}", flush=True)
        if problem:
            print(f"     {problem}", flush=True)
    print(f"\n{passed}/{len(picked)}")
