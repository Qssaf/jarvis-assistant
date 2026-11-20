"""Does Jarvis keep the right things from a conversation, and only those? Made-up talks go through the real Brain.learn
(its LEARN prompt) on your configured models; nothing is saved (the memory is a stand-in). One model request per case:

    .venv/bin/python evals/learn_eval.py                 # every case, your agent models
    EVAL_MODELS="aistudio gemini-3.8-flash low" .venv/bin/python evals/learn_eval.py took_back lasting
"""
import os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import brain, store  # noqa: E402

MEMORY = "- Call the user Sam instead of sir."
store.memory = lambda: MEMORY  # (never yours)
store.remember = lambda fact: fact  # (nothing is saved)


def nothing(kept):
    return f"kept {kept}" if kept else ""


def has(*words, never=()):
    """A check: something kept mentions one of words, and nothing kept mentions any of never."""
    def check(kept):
        text = " | ".join(kept).lower()
        if not any(w in text for w in words):
            return f"none of {words} in {kept}"
        bad = [w for w in never if w in text]
        return f"kept {bad} in {kept}" if bad else ""
    return check


def talk(*lines):
    """you, jarvis, you, ... in turn."""
    return [{"who": "jarvis" if i % 2 else "you", "text": text} for i, text in enumerate(lines)]


# name: (the conversation, check(kept) -> problem or "")
CASES = {
    # an address typed to pass on, then taken back: it was kept as the user's own email (and used to set up git)
    "took_back": (talk("Send Alex this email sam.k@example.com", "I have the address, Sam, but what should the email to Alex say?",
                       "like send him this email because he wants to use it on whatsapp", "I've sent the email address to Alex on WhatsApp.",
                       "tell him I sent the wrong email before", "Sent: 'I sent the wrong email before.'"), nothing),
    "dictated": (talk("send Maya this link https://example.com/join/abc and this number 555 0134 for the group booking",
                      "Sent the link and the number to Maya."), nothing),
    # a contact's name isn't a fact about the user ("Knows Alex", "Has a teacher named Omar" were kept)
    "knows": (talk("message Alex Reed that I'm running late", "Sent: 'I'm running late'.",
                   "and send the homework file to Omar computer teacher", "Sent the file to Omar computer teacher."), nothing),
    "small_talk": (talk("you good?", "Functioning flawlessly, Sam.", "tell me something I don't know",
                        "Bananas are curved because they grow towards the sun."), nothing),
    "lasting": (talk("by the way I moved to Lyon last month, I'm studying physics at the university there",
                     "Noted, Sam. How are you finding Lyon?", "it's fine"), has("lyon")),
    "corrected": (talk("my sister's name is Maya, remember that for later", "Of course.",
                       "sorry, I meant Mia, not Maya", "Mia it is."), has("mia", never=("maya",))),
    "lesson": (talk("check my email", "Opening Gmail in the browser.", "no, never open the browser for my email, use the account directly",
                    "Understood. You have three unread emails."), has("lesson", never=())),
    "background": (talk("so the mitochondria is the powerhouse of the cell and that will be on the exam on Friday", "",
                        "next slide please"), nothing),
}

if __name__ == "__main__":
    entries = [brain.entry(line) for line in os.environ["EVAL_MODELS"].split(",")] if os.environ.get("EVAL_MODELS") else brain.chain()
    b = brain.Brain.__new__(brain.Brain)
    b.backends, b.down_until, b.contents, b.notify = {}, {}, [], (lambda text: None)
    generate = b._generate
    b._generate = lambda contents, **kw: generate(contents, entries=entries)
    picked = [c for c in CASES if not sys.argv[1:] or c in sys.argv[1:]]
    passed = 0
    for name in picked:
        messages, check = CASES[name]
        started = time.time()
        try:
            kept = b.learn(messages)
            problem = "the reply held no list" if kept is None else check(kept)
        except Exception as e:
            kept, problem = [], f"failed: {e}"
        passed += not problem
        print(f"{'PASS' if not problem else 'FAIL'} {name:12} {time.time() - started:4.1f}s  {kept}", flush=True)
        if problem:
            print(f"     {problem}", flush=True)
    print(f"\n{passed}/{len(picked)}")
