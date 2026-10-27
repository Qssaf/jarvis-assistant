"""Quick checks for the non-model logic: run with `.venv/bin/python test_jarvis.py` (Windows: .venv\\Scripts\\python)."""
import os, tempfile

_home = tempfile.mkdtemp()  # never the user's real settings, memory or reminders
os.environ.update(XDG_CONFIG_HOME=os.path.join(_home, "config"), XDG_DATA_HOME=os.path.join(_home, "data"), APPDATA=_home,
                  PYTHON_KEYRING_BACKEND="keyring.backends.fail.Keyring")  # (and never the real keychain)

import brain
import system

brain.OPENCODE_ACCOUNTS = os.path.join(_home, "opencode-accounts.json")  # (not the user's real Google sign-ins,
brain.PLUGIN_CONSTANTS = [os.path.join(_home, "constants.js")]               # nor an installed plugin's client)
brain.store.save_plugins({})  # (no Composio: a real Brain would connect to it, and could start a browser sign-in)

# click grid: Gemini's 0-1000 coordinates map onto the screen, clamped to its edges
brain.screen_size[:] = (1600, 900)
assert brain.to_pixels(0, 0) == (0, 0)
assert brain.to_pixels(500, 500) == (800, 450)
assert brain.to_pixels(1000, 1000) == (1599, 899)
assert brain.to_pixels(1200, -5) == (1599, 0)

# screenshot size comes from the JPEG header (baseline SOF0 for 1600x900)
sof = b"\xff\xd8" + b"\xff\xe0\x00\x04\x00\x00" + b"\xff\xc0\x00\x11\x08" + (900).to_bytes(2, "big") + (1600).to_bytes(2, "big")
assert brain.jpeg_size(sof) == (1600, 900)

# history trimming keeps only the newest screenshot and never splits a tool call from its result
img = {"inlineData": {"mimeType": "image/jpeg", "data": "x"}}
msgs = [{"role": "user", "parts": [{"text": "a"}]},
        {"role": "model", "parts": [{"functionCall": {"name": "screenshot"}}]},
        {"role": "user", "parts": [{"functionResponse": {"name": "screenshot"}}, dict(img)]},
        {"role": "model", "parts": [{"functionCall": {"name": "screenshot"}}]},
        {"role": "user", "parts": [{"functionResponse": {"name": "screenshot"}}, dict(img)]}]
brain.trim(msgs, keep=3)
assert sum("inlineData" in p for m in msgs for p in m["parts"]) == 1
assert msgs[0]["role"] == "user" and "text" in msgs[0]["parts"][0]  # nothing to cut at, so nothing cut
# model chain: a rate-limited entry is skipped for a while, an error moves on, a bad request stops
class Fake:
    calls = []

    def __init__(self, behaviour):
        self.behaviour = behaviour

    def generate(self, contents, model, thinking, **kw):
        Fake.calls.append(model)
        if self.behaviour == "limited":
            raise brain.Overloaded("busy", retry_after=60)
        if self.behaviour == "broken":
            raise RuntimeError("auth expired")
        if self.behaviour == "bad":
            raise brain.BadRequest("400")
        return [{"text": f"from {model}"}]


brain.chain = lambda: [("a", "m1", "low"), ("b", "m2", "low"), ("c", "m3", "low")]
b = brain.Brain.__new__(brain.Brain)
b.backends, b.down_until, b.notify = {"a": Fake("limited"), "b": Fake("broken"), "c": Fake("ok")}, {}, lambda t: None
probes = []
real_thread, brain.threading.Thread = brain.threading.Thread, lambda target, daemon, args=(): probes.append(args) or type("T", (), {"start": lambda self: None})()  # no real probes
assert b._generate([])[0]["text"] == "from m3"
assert b._generate([])[0]["text"] == "from m3"
assert Fake.calls == ["m1", "m2", "m3", "m3"]  # m1 cooling down, m2 waiting for its probe
b.backends["c"] = Fake("bad")
try:
    b._generate([])
    raise AssertionError("BadRequest should stop the chain")
except brain.BadRequest:
    pass
# a timeout (one request too heavy, e.g. solving a puzzle in a look) is checked again in seconds, and nobody is told the
# model is down unless that check fails too
told = []
b.notify, probes[:] = told.append, []
b._mark_down(("x", "m9", "low"), brain.Overloaded("timed out"), True)
assert probes == [(5, False)] and not told and b.down_until[("x", "m9", "low")] == float("inf"), (probes, told)
b._mark_down(("y", "m8", "low"), brain.Overloaded("busy"), True)
assert probes[-1] == (60, True) and told == ["m8 via y isn't answering; using backup models until it's back."], told
b._mark_down(("z", "m7", "low"), brain.Overloaded("Google refused a@x's sign-in (HTTP 400): sign in again on the Models page"), True)
assert "sign in again" in told[-1], told  # (only the user can fix that one: they're told why)
brain.threading.Thread = real_thread
# settings validation rejects nonsense instead of saving it
import store
store.SETTINGS_FILE = os.path.join(tempfile.mkdtemp(), "settings.json")
for bad in ({"wake_threshold": 5}, {"agent_models": "openai gpt-5"}, {"nope": 1}):
    try:
        store.update_settings(bad)
        raise AssertionError(f"accepted {bad}")
    except ValueError:
        pass
assert store.update_settings({"follow_up_seconds": "12"})["follow_up_seconds"] == 12

# session ids from URLs can't escape the sessions folder
try:
    store.Sessions._path(store.Sessions.__new__(store.Sessions), "../../etc/passwd")
    raise AssertionError("path traversal accepted")
except (ValueError, AttributeError):
    pass
# reminders: relative and clock times; a time already past today means tomorrow
import time
now = time.mktime((2026, 10, 7, 14, 0, 0, 0, 0, -1))
assert brain.parse_when(in_minutes=20, now=now) == now + 1200
assert time.localtime(brain.parse_when(at="09:00", now=now)).tm_mday == 8
assert time.localtime(brain.parse_when(at="2026-12-25 08:00", now=now)).tm_mon == 12
try:  # a date and time already gone is a mistake to report, not a reminder that goes off at once
    brain.parse_when(at="2026-10-06 08:00", now=now)
    raise AssertionError("a past date was accepted")
except ValueError as e:
    assert "already passed" in str(e)

# memory and reminder storage (in a temp folder)
import tempfile
tmp = tempfile.mkdtemp()
store.MEMORY_FILE, store.REMINDERS_FILE = f"{tmp}/memory.md", f"{tmp}/reminders.json"
store.remember("likes tea"); store.remember("exam on June 5")
assert store.forget("TEA") == 1 and "June 5" in store.memory() and "tea" not in store.memory()
store.remember("Exam  on June 5")  # a fact said twice (or a lesson learnt twice) is kept once
assert store.memory().lower().count("exam on june 5") == 1, store.memory()
store.add_reminder(100, "past"); store.add_reminder(4e9, "future")  # (2096: Windows can't show dates past 3000)
assert [r["text"] for r in store.pop_due(now=200)] == ["past"] and [r["text"] for r in store.reminders()] == ["future"]

# "announced instead of acted" detection: promises get nudged, finished answers don't
for text, nudge in [("Sure, I'll open Dolphin now, sir.", True), ("Let me check that.", True),
                    ("Right away, sir. I will look.", True), ("I've set it; I'll remind you at five, sir.", False),
                    ("Done, sir. I'll let you know.", False), ("You have 145 GB free.", False)]:
    assert bool(brain.ANNOUNCED.match(text)) == nudge, text
# finishing early: a reply written together with a close_window call needs no extra model round trip
class OneShot:
    calls = 0

    def generate(self, contents, model, thinking, **kw):
        OneShot.calls += 1
        return [{"functionCall": {"name": "close_window", "args": {"name": "kcalc"}}}, {"text": "144, sir. Closed it."}]


brain.chain = lambda: [("x", "m", "low")]
brain.TOOLS["close_window"] = (lambda name: {"result": f"closed {name}"},) + brain.TOOLS["close_window"][1:]
a = brain.Brain.__new__(brain.Brain)
a.backends, a.down_until, a.notify, a.plugins, a.app_tools = {"x": OneShot()}, {}, (lambda t: None), {}, {}
a.contents, a.cancel, a.ask_lock, a.remote = [], brain.threading.Event(), brain.threading.Lock(), False
a._system = lambda: ""
asked_saved = []
brain.on_asked[0] = asked_saved.append
assert a.ask("12 times 12 then close it") == "144, sir. Closed it." and OneShot.calls == 1
assert asked_saved == [a.contents]  # (saved with the conversation, whoever asked: only voice tasks were)
# after a check is added, "I'll tell you if one fails" is the answer: no "don't announce it" nudge (it then read the email now)
class AddsCheck:
    calls = 0

    def generate(self, contents, model, thinking, **kw):
        AddsCheck.calls += 1
        return ([{"functionCall": {"name": "checks", "args": {"action": "add", "text": "a failed payment"}}}] if AddsCheck.calls == 1
                else [{"text": "I'll tell you if a payment fails."}])
real_checks, brain.TOOLS["checks"] = brain.TOOLS["checks"], (lambda action, text="": {"result": brain.CHECK_ADDED},) + brain.TOOLS["checks"][1:]
a.backends = {"x": AddsCheck()}
assert a.ask("tell me if a payment fails") == "I'll tell you if a payment fails." and AddsCheck.calls == 2
brain.TOOLS["checks"] = real_checks
# a scheduled task or background check runs on its own history, and can't confirm a change itself: nobody said yes
class SelfConfirms:
    seen = []

    def generate(self, contents, model, thinking, **kw):
        if "functionResponse" in contents[-1]["parts"][0]:
            SelfConfirms.seen.append(contents[-1]["parts"][0]["functionResponse"]["response"])
            return [{"text": "It needs your yes first."}]
        return [{"functionCall": {"name": "run_command", "args": {"command": "sudo reboot", "confirmed": True}}}]
a.backends, kept, ran, real_shell = {"x": SelfConfirms()}, list(a.contents), [], brain.system.shell
brain.system.shell = lambda command, timeout: ran.append(command) or (0, "")
assert a.ask("reboot at 3", unattended=True) == "It needs your yes first."
assert ran == [] and "not run" in SelfConfirms.seen[0]["error"] and a.contents == kept and not (a.unattended or a.remote)
assert len(asked_saved) == 2  # (a scheduled task's own history isn't saved over the conversation's)
brain.on_asked[0] = lambda contents: None
a.unattended = True  # ...while the voice's own tools, run meanwhile, keep the user's real yes
assert "error" not in a._run_tool("run_command", {"command": "sudo reboot", "confirmed": True})[0] and ran == ["sudo reboot"]
a.unattended = False
# with a spoken passphrase set, a task from the voice can't confirm a change until ask_user brought the passphrase back;
# one from the phone can (it can't be said there, and that chat is the user's own)
store.set_secret(store.PASSPHRASE, "blue bird")
SelfConfirms.seen, ran = [], []
assert a.ask("reboot now") == "It needs your yes first." and ran == [] and "passphrase" in SelfConfirms.seen[0]["error"]
assert a.ask("reboot now", remote=True) == "It needs your yes first." and ran == ["sudo reboot"]
store.set_secret(store.PASSPHRASE, "")
brain.system.shell = real_shell
a.add_turn("[check] failed payments", "Two failed: offer a free month?")
assert a.contents[-1] == {"role": "model", "parts": [{"text": "Two failed: offer a free month?"}]} and a.contents[-2]["role"] == "user"
# page text: attribute values may contain markup, scripts are dropped, entities decoded
assert brain.page_text('<div data-x="a<b>c</ref>">Hello&nbsp;<b>world</b></div><script>var x="<p>no</p>"</script> ok') == "Hello world ok"

# the mic's speech detector: talking keeps Jarvis listening; a steady hum (fan, hiss) soon stops counting as talking
import collections, sys, types
import numpy as np
import jarvis
live = jarvis.Live.__new__(jarvis.Live)
live.mic, live.session, live.floor, live.voice_at, live.level = True, None, 100.0, 0.0, 0.0
live.speaker, live.backlog = jarvis.Speaker(), collections.deque(maxlen=125)  # the real one: a fake hid a renamed attribute
frame = lambda rms: (np.random.default_rng(1).normal(0, rms, 1280)).astype(np.int16)
for _ in range(50):
    live.feed(frame(60))  # quiet room
assert live.voice_at == 0.0
live.feed(frame(3000))  # speech
assert live.voice_at > 0
live.voice_at = 0.0
for _ in range(1500):  # two minutes of a loud fan
    live.feed(frame(400))
live.voice_at = 0.0
live.feed(frame(400))
assert live.voice_at == 0.0

# while Jarvis talks with echo cancelling on, the faint echo left over goes to Gemini as silence (it heard itself and
# kept answering itself); the user talking over it still gets through, and so does the second after
live.speaker.echo_cancelled, live.speaker.until, live.floor, live.voice_at = True, time.time() + 5, 3.0, 0.0
live.backlog.clear()
live.feed(frame(50))
live.feed(frame(3000))
live.feed(frame(50))
assert [any(np.frombuffer(b, np.int16)) for b in live.backlog] == [False, True, True], "echo gate"
# Jarvis answers right after the user stops: the start of its reply isn't let through as the second after their speech
live.speaker.until, live.voice_at = 0.0, 0.0
live.backlog.clear()
live.feed(frame(3000))  # the end of the request
live.speaker.play(b"\0" * 48000)
live.speaker.since = time.time()  # (the reply reaches the speakers now, not 0.25 s later)
live.feed(frame(50))  # its echo
assert [any(np.frombuffer(b, np.int16)) for b in live.backlog] == [True, False], "echo gate at the start of a reply"
live.speaker.stop()
live.speaker.echo_cancelled, live.speaker.until = False, 0.0

# keys: common names become xkb's, several chains run in order; only portal errors are blamed on the permission prompt
assert system.key_chains("Enter control+a esc") == [["Return"], ["ctrl", "a"], ["Escape"]]
brain.focus_launched = lambda: None
system.press_keys, pressed = (lambda keys: pressed.append(keys) or ""), []
assert "result" in brain.tool_press_keys("ctrl+l") and pressed == ["ctrl+l"]
assert "Remote Control" not in brain.input_result("", "unknown keysym 'Foo'")["error"]
assert "Remote Control" in brain.input_result("", "portal dialog denied or failed: cancelled")["error"]

# browsers and Electron apps (found through their launcher scripts) get the accessibility switch; other apps don't
if not system.IS_WINDOWS:
    d = tempfile.mkdtemp()
    os.makedirs(f"{d}/lib/chat"); os.makedirs(f"{d}/bin")
    open(f"{d}/lib/chat/resources.pak", "w").close()  # what every Chromium build ships next to its binary
    for path, body in ((f"{d}/lib/chat/chat", "#!/bin/sh\n"), (f"{d}/bin/chatapp", f'#!/bin/sh\nexec {d}/lib/chat/chat "$@"\n'),
                       (f"{d}/bin/calc", "#!/bin/sh\nexec /bin/true\n")):
        open(path, "w").write(body); os.chmod(path, 0o755)
    os.environ["PATH"] = f"{d}/bin" + os.pathsep + os.environ["PATH"]
    assert system.chromium_based("chatapp") and not system.chromium_based("calc") and not system.chromium_based("no-such-app")
    real = system.launch, system.window_ids, system.active_window
    started = []
    system.launch, system.window_ids, system.active_window = (lambda command, env=None: started.append((command, env))), set, str
    brain.tool_launch("chatapp https://example.com", wait=0, screenshot=False)
    brain.tool_launch("calc", wait=0, screenshot=False)
    # only an app Jarvis has just started is worth waiting for: one that's open but not in the tree never shows up
    assert brain.a11y_wait("calc") == 3 and brain.a11y_wait("discord") == 0
    # a name that's only in the app menu starts that entry, when exactly one fits
    real_lookup = system.program_exists, system.similar_programs, system.have
    system.program_exists, system.have = (lambda command: command.startswith("gtk-launch")), (lambda program: True)
    system.similar_programs = lambda name: ["gtk-launch somegame-launcher"]
    brain.tool_launch("somegame", wait=0, screenshot=False)
    system.similar_programs = lambda name: ["somegame-cli", "gtk-launch somegame-launcher", "gtk-launch somegame-editor"]
    assert "no program" in brain.tool_launch("somegame", wait=0, screenshot=False)["error"]
    system.program_exists, system.similar_programs, system.have = real_lookup
    system.launch, system.window_ids, system.active_window = real
    assert [c for c, _ in started] == ["chatapp --force-renderer-accessibility https://example.com", "calc",
                                       "gtk-launch somegame-launcher"], started
    assert started[0][1]["ACCESSIBILITY_ENABLED"] == "1"

# what the user asked to be called, read from memory; negations and "sir" don't count
for note, name in [("- User prefers to be called Q.", "Q"), ("- likes tea\n- Call me Captain, not sir", "Captain"),
                   ("- Don't call me sir", ""), ("- Never call him by his full name", ""), ("- likes tea", ""),
                   ("- The user's name is Sam.", "Sam"), ("- My name is Alex", "Alex")]:
    assert jarvis.preferred_name(note) == name, (note, jarvis.preferred_name(note))

# a failed expect step stops the plan before anything is typed (the wrong chat is open); a passed one carries on
typed, real = [], (brain.tool_screenshot, brain.tool_type_text)
brain.tool_screenshot = lambda: ({"result": "screenshot"}, b"\xff\xd8")  # (never the real screen in a test)
brain.tool_type_text = lambda text: typed.append(text) or {"result": "typed"}
brain.pointer[0] = lambda contents: [{"text": "No, the open chat is with Alex."}]
out = brain.tool_act([{"expect": "the open chat is with Sam"}, {"type": "hi"}], screenshot_after=False)
assert "Alex" in out["error"] and typed == [], out
brain.pointer[0] = lambda contents: [{"text": "Yes, it is."}]
assert brain.tool_act([{"expect": "the open chat is with Sam"}, {"type": "hi"}], screenshot_after=False)["result"] == \
    ["checked: the open chat is with Sam", "typed"] and typed == ["hi"]
# models sometimes label a step with type ({type: "keys", keys: "Return"}): that's the step's kind, never text to type
pressed, real_keys = [], brain.tool_press_keys
brain.tool_press_keys = lambda keys: pressed.append(keys) or {"result": "pressed"}
brain.tool_act([{"type": "keys", "keys": "Return"}, {"type": "wait", "wait": 0}], screenshot_after=False)
assert pressed == ["Return"] and typed == ["hi"], (pressed, typed)
# a sent chat message takes a moment to appear: the look after Return waits for it, and the result says it was sent
slept, real_sleep, real_look = [], brain.time.sleep, brain.tool_look
brain.time.sleep, brain.tool_look = slept.append, (lambda q, image=None, model=None, fast=False, careful=False: {"answer": "it's there"})
out = brain.tool_act([{"type": "hi"}, {"keys": "Return"}, {"look": "is it in the chat?"}], screenshot_after=False)
assert 1.0 in slept and "sent" in out[0], (slept, out)  # (a look step returns its screenshot too)
slept.clear()
assert "sent" not in brain.tool_act([{"keys": "Return"}, {"look": "what happened?"}], screenshot_after=False)[0] and 1.0 not in slept
brain.time.sleep, brain.tool_look = real_sleep, real_look
# a combined click and type step executes both (clicks then types) instead of dropping the type
typed.clear()
real_click, clicked = brain.tool_click, []
brain.tool_click = lambda *a, **kw: clicked.append(a) or {"result": "clicked"}
real_locate = brain.locate
brain.locate = lambda *a, **kw: (100, 200)
res = brain.tool_act([{"click_on": "message box", "type": "code"}], screenshot_after=False)
assert res["result"] == ["clicked", "typed"] and clicked and typed == ["code"]
# a type: "text" label on a click step is stripped, never typed
typed.clear()
res = brain.tool_act([{"type": "text", "click_on": "message box"}], screenshot_after=False)
assert res["result"] == ["clicked"] and typed == []
brain.tool_click, brain.locate, brain.tool_press_keys = real_click, real_locate, real_keys
brain.tool_screenshot, brain.tool_type_text = real
brain.pointer[0] = None

# the voice model can't see, so a coordinate click is refused before anything runs
import asyncio
live.turn_calls, live.user_spoke_at = [0.0, 0], 0.0
live.last_heard = live.last_said = ""
live.working = live.task_screen = live.announcing = False
refused = asyncio.run(live._tool(types.SimpleNamespace(name="act", args={"steps": [{"type": "hi"}, {"click": [500, 500]}]})))
assert "click_on" in refused["error"]
# after "Shall I send it?", noise ("a pretzel") isn't a yes: the confirmed send is refused, a real yes goes through
send_it = types.SimpleNamespace(name="whatsapp_send", args={"to": "Sam", "text": "hi", "confirmed": True})
live.last_said, live.last_heard = "I'll tell Sam the plan. Shall I proceed with this message, Q?", "a pretzel"
assert "isn't a clear yes" in asyncio.run(live._tool(send_it))["error"]
live.last_heard = "no, wait"
assert "isn't a clear yes" in asyncio.run(live._tool(send_it))["error"]
assert not jarvis.asked_yes("Who should I send it to?") and not jarvis.asked_yes("Can I help with anything else, Q?")
assert jarvis.said_yes("Yeah, go ahead.") and jarvis.said_yes("oui") and not jarvis.said_yes("")
assert jarvis.said_yes("Sure, no problem.") and not jarvis.said_yes("No, don't.") and not jarvis.said_yes("ok no")
# a spoken passphrase: every confirmed: true from the voice also needs it in what the user just said (case, punctuation,
# spacing and extra words don't matter); it's saved as a secret, never in settings, never shown back or logged
import json
try:
    jarvis.api_post("/api/passphrase", {"passphrase": "a b"}, live, None)
    raise AssertionError("a two-letter passphrase was taken")
except ValueError:
    pass
assert jarvis.api_post("/api/passphrase", {"passphrase": "  Blue  bird 42 "}, live, None) == {"passphrase": True}
assert store.secret(store.PASSPHRASE) == "Blue bird 42" and "bird" not in json.dumps([store.settings(), jarvis.api_get("/api/settings", None)])
assert jarvis.api_get("/api/settings", None)["passphrase"] is True
assert all(map(store.said_passphrase, ["yes, blue bird 42", "Bluebird-42!", "ok BLUE-bird, 42 go"]))
assert not any(map(store.said_passphrase, ["yes", "blue bird", "bluebird 421", ""]))
assert store.hide_passphrase("yes, Blue-bird 42 send it") == "yes, ••• send it"
async def sent_it(fc, args):
    return {"result": "sent"}
live._answer = sent_it
live.last_said, live.last_heard = "Shall I send it? Your passphrase?", "yes"
assert "passphrase" in asyncio.run(live._tool(send_it))["error"]  # a yes alone isn't enough...
live.last_said = ""
assert "passphrase" in asyncio.run(live._tool(send_it))["error"]  # ...nor a dictated message sent at once
assert "passphrase" not in json.dumps(asyncio.run(live._tool(types.SimpleNamespace(name="act", args={"steps": [{"keys": "Return"}]}))))
live.last_said, live.last_heard = "Shall I send it? Your passphrase?", "yes, blue bird 42"
assert asyncio.run(live._tool(send_it)) == {"result": "sent"}
async def no_send(text, **kw):
    pass
live._send, logged_pass = no_send, []
jarvis.clients.append(types.SimpleNamespace(put=logged_pass.append))
asyncio.run(live._type("yes, bluebird 42"))
jarvis.clients.pop()
assert logged_pass[0]["text"] == "yes, •••" and live.last_heard == "yes, bluebird 42"  # (typed counts too; never shown)
del live._answer, live._send
assert jarvis.api_post("/api/passphrase", {"passphrase": ""}, live, None) == {"passphrase": False} and not store.secret(store.PASSPHRASE)
# while the agent works on the screen, the voice keeps its hands off it (both once sent the same Discord message)
live.working = live.task_screen = True
assert "background task is using the screen" in asyncio.run(live._tool(types.SimpleNamespace(name="act", args={"steps": [{"keys": "Return"}]})))["error"]
live.working = live.task_screen = False
live.last_said = live.last_heard = ""
# noise gets no answer at all ("Yes?" after every sound wore the user out), and the watchdog doesn't re-ask it
live.inflight = {"text": None, "heard": "desde", "since": time.time(), "tool": False, "answered": False, "recovered": False}
assert asyncio.run(live._tool(types.SimpleNamespace(name="ignore", args={}))) == {"result": "ignored"} and live.inflight is None
import threading
# the agent asks the user mid-task: the voice says the question, its answer_task hands the answer back, and Stop ends the wait
asked_voice, real_notify = [], system.notify
live._go, system.notify = (lambda coro: asked_voice.append(coro) or coro.close()), (lambda *a: None)
live.question, live.mic = None, False
got_answer = []
waiter = threading.Thread(target=lambda: got_answer.append(live.ask_from_task("Sam Lee or Sam Leeds?", threading.Event())))
waiter.start()
while not asked_voice:
    time.sleep(0.01)
assert live.mic and live.question, "the question wasn't said with the mic left open"
assert asyncio.run(live._tool(types.SimpleNamespace(name="answer_task", args={"answer": "Sam Lee"})))["result"]
waiter.join(2)
assert got_answer == ["Sam Lee"] and live.question is None, got_answer
# what the user really said rides along with the voice's answer (noise once came back as "yes")
asked_voice.clear()
waiter = threading.Thread(target=lambda: got_answer.append(live.ask_from_task("Send it?", threading.Event())))
waiter.start()
while not asked_voice:
    time.sleep(0.01)
live.last_heard = "a pretzel"
asyncio.run(live._tool(types.SimpleNamespace(name="answer_task", args={"answer": "yes"})))
waiter.join(2)
assert got_answer[-1] == 'yes (the user\'s exact words: "a pretzel")', got_answer
live.last_heard = ""
assert "error" in asyncio.run(live._tool(types.SimpleNamespace(name="answer_task", args={"answer": "late"})))  # nothing waiting
# in quiet hours, a question nobody is there for isn't said out loud: it's in the chat, and the agent ends with it instead
asked_voice.clear()
store.update_settings({"do_not_disturb": True})
live.mic, live.user_spoke_at = False, time.time() - 600
assert live.ask_from_task("Send it?", threading.Event()) is None and asked_voice == [] and not live.mic
live.user_spoke_at = time.time()  # (but someone talking with Jarvis right now is asked)
waiter = threading.Thread(target=lambda: got_answer.append(live.ask_from_task("Send it?", threading.Event())))
waiter.start()
while not asked_voice:
    time.sleep(0.01)
asyncio.run(live._tool(types.SimpleNamespace(name="answer_task", args={"answer": "no"})))
waiter.join(2)
store.update_settings({"do_not_disturb": False})
stopped = threading.Event()
stopped.set()
assert live.ask_from_task("Delete 37 emails?", stopped) is None  # Stop pressed: no answer, the agent ends with its question
brain_asker = brain.asker[0]
brain.asker[0] = lambda q, cancel: "yes"
assert brain.Brain.ask_user(types.SimpleNamespace(cancel=None, remote=False, passphrase_ok=False), "ok?") == {"answer": "yes"}
# with a passphrase, the agent's answer from the user carries it (hidden from the agent, which only learns it was said)
store.set_secret(store.PASSPHRASE, "blue bird")
brain.asker[0] = lambda q, cancel: 'yes (the user\'s exact words: "yes, blue bird")'
asker_self = types.SimpleNamespace(cancel=None, remote=False, passphrase_ok=False)
assert brain.Brain.ask_user(asker_self, "ok?") == {"answer": 'yes (the user\'s exact words: "yes, •••")'} and asker_self.passphrase_ok
store.set_secret(store.PASSPHRASE, "")
brain.asker[0] = lambda q, cancel: None
assert "end your reply" in brain.Brain.ask_user(types.SimpleNamespace(cancel=None, remote=False, passphrase_ok=False), "ok?")["error"]
brain.asker[0], system.notify = brain_asker, real_notify
# clicking where the mouse is (button without coordinates) works in-place
clicked = []
real_click = system.click
system.click = lambda btn, dbl=False: clicked.append((btn, dbl)) or ""
accepted = brain.tool_act([{"button": "left"}], screenshot_after=False)
assert accepted["result"] == ["clicked left"] and clicked == [("left", False)]
system.click = real_click

# one voice session at a time, even when "Hey Jarvis" and a reminder arrive together right after startup
import threading
opened = []
live.brain = types.SimpleNamespace(tools_ready=threading.Event(), refresh_if_stale=lambda: None)
live.task = live.ready = None
live.task_lock, live.closing, live.tools_wait = None, False, None
async def fake_run():
    opened.append(1)
    live.ready.set()
    await asyncio.sleep(0.2)
live._run = fake_run
async def both():
    asyncio.get_running_loop().call_later(0.05, live.brain.tools_ready.set)
    await asyncio.gather(live._open(), live._open(), live._open())
asyncio.run(both())
assert opened == [1], opened

# cutting off a reply that has already finished generating mustn't mute the next one
live.speaker = types.SimpleNamespace(busy=lambda: True, stop=lambda: None)
live.spoke, live.muted = False, False
live.barge_in()
assert live.muted is False
live.spoke = True
live.barge_in()
assert live.muted is True

# parallel parts share one deadline: three that hang cost the timeout once, not three times
t = time.time()
assert brain.in_parallel(*[lambda: time.sleep(1)] * 3, timeout=0.3) == [None] * 3 and time.time() - t < 0.7

# the page reader never fetches this PC or the local network
for url in ("http://127.0.0.1:4849/", "http://192.168.1.1/", "http://[::1]/", "file:///etc/passwd", "http://169.254.169.254/"):
    assert not brain.public_url(url), url
assert brain.public_url("https://1.1.1.1/")


# if the account tools never load (Composio down, sign-in pending), only the first session waits for them
import time as _time
live.brain = types.SimpleNamespace(tools_ready=threading.Event(), refresh_if_stale=lambda: None)
live.task = live.ready = live.tools_wait = None
async def twice():
    t = _time.time()
    await live._open()
    first = _time.time() - t
    live.task = None  # as if that session ended
    t = _time.time()
    await live._open()
    return first, _time.time() - t
first, second = asyncio.run(twice())
assert first > 5 and second < 0.5, (first, second)

# learning the user's voice: a wake-up followed by a request is kept as theirs, one dismissed in silence as not
import tempfile, os
jarvis.WAKE_DIR = tempfile.mkdtemp()
lrn = jarvis.VoiceLearner()
clip = np.zeros(16000, np.int16)
lrn.woke(clip); lrn.judge(True)
lrn.woke(clip); lrn.judge(False)
lrn.woke(clip); lrn.pending = (lrn.pending[0] - 60, clip); lrn.judge(True)  # too long ago to tell: dropped
assert (len(os.listdir(lrn.dirs["yes"])), len(os.listdir(lrn.dirs["no"]))) == (1, 1)
# the wake word is a choice: each has its own clips and verifier ("Hey Jarvis" keeps 2.0's), a custom model by its contents
assert jarvis.wake_folder("hey_jarvis") == jarvis.WAKE_DIR and jarvis.wake_folder("alexa") == os.path.join(jarvis.WAKE_DIR, "alexa")
own = os.path.join(tempfile.mkdtemp(), "hey_computer_v0.1.onnx")
open(own, "wb").write(b"not really a model")
first_folder = jarvis.wake_folder(own)
open(own, "wb").write(b"trained again, for another phrase")
assert first_folder != jarvis.wake_folder(own) and os.path.basename(first_folder).startswith("hey_computer_v0.1-")
lrn.woke(clip)
lrn.use("alexa")
assert lrn.pending is None and lrn.dirs["yes"] == os.path.join(jarvis.WAKE_DIR, "alexa", "yes") and not os.listdir(lrn.dirs["yes"])
assert store.wake_phrase({"wake_word": "hey_mycroft"}) == "Hey Mycroft" and store.wake_phrase({"wake_word": own}) == "Hey Computer"
for bad in ("timer", "/nowhere/hey.onnx", own[:-5] + ".txt"):
    try:
        store.update_settings({"wake_word": bad})
        raise AssertionError(f"{bad} was taken as a wake word")
    except ValueError:
        pass
try:  # (a file that isn't a model is refused before it's saved: Jarvis would stop hearing its wake word)
    jarvis.api_post("/api/settings", {"wake_word": own}, None, None)
    raise AssertionError("a file that isn't a model was taken")
except ValueError as e:
    assert "openWakeWord" in str(e) and store.settings()["wake_word"] == "hey_jarvis"
assert store.update_settings({"wake_word": own})["wake_word"] == own  # (the store checks it's an .onnx file that's there)
store.update_settings({"wake_word": "alexa"})
open(os.path.join(jarvis.WAKE_DIR, "alexa", "verifier.pkl"), "wb").close()
got = jarvis.api_get("/api/settings", None)
assert got["wake_phrase"] == "Alexa" and got["voice_learned"] and got["wake_words"]["hey_rhasspy"] == "Hey Rhasspy"
store.update_settings({"wake_word": "hey_jarvis"})
# "Only wake for my voice": with a verifier learned, a wake-up needs it to be sure it's the user; without one, as before
cfg = {**store.settings(), "wake_threshold": 0.5, "only_my_voice": True}
assert jarvis.wake_bar(cfg, False, True) == jarvis.ONLY_ME > 0.5 and jarvis.wake_bar(cfg, False, False) == 0.5
assert jarvis.wake_bar({**cfg, "only_my_voice": False}, False, True) == 0.5 and jarvis.wake_bar(cfg, True, True) == 0.85

# session search finds words inside conversations, not just titles
ss = store.Sessions.__new__(store.Sessions)
ss.dir = tempfile.mkdtemp()
ss.new(); ss.add({"who": "you", "text": "What exam do I have tomorrow?"}); ss.add({"who": "jarvis", "text": "Quiz 1 for Calculus III."})
ss.new(); ss.add({"who": "you", "text": "Play some music"})
assert [r["match"] for r in ss.search("calculus")] == ["Quiz 1 for Calculus III."] and len(ss.search("music")) == 1

# the request options for thinking summaries and pictures
r = brain.build_request([], None, None, "low", thoughts=True)
assert r["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "low", "includeThoughts": True}
assert brain.build_request([], None, None, None, images=True)["generationConfig"] == {"responseModalities": ["TEXT", "IMAGE"]}

# files: text is read, folders listed, binaries refused
t = tempfile.mkdtemp()
open(os.path.join(t, "notes.txt"), "w").write("buy milk")
open(os.path.join(t, "blob.bin"), "wb").write(b"\0\1\2" * 100)
assert brain.tool_read_file(os.path.join(t, "notes.txt"))["text"] == "buy milk"
assert sorted(brain.tool_read_file(t)["folder"]) == ["blob.bin", "notes.txt"] and "error" in brain.tool_read_file(os.path.join(t, "blob.bin"))
# account permissions: reads vs changes, paused and read-only accounts refused before anything is sent
assert brain.toolkit_of("GOOGLE_CLASSROOM_COURSES_LIST") == "google_classroom" and brain.toolkit_of("GMAIL_SEND_EMAIL") == "gmail"
assert [brain.workspace_slug(a) for a in ("Google Tasks", "google_drive", "google classroom", "GitHub", "fax")] == \
    ["googletasks", "googledrive", "google_classroom", "github", None]  # however the voice model spells the app
assert all(map(brain.is_read_action, ["GMAIL_FETCH_EMAILS", "GOOGLECALENDAR_EVENTS_LIST", "GITHUB_GET_THE_AUTHENTICATED_USER", "GMAIL_GET_LABEL",
                                      "GOOGLE_CLASSROOM_COURSE_WORK_LIST", "TRELLO_GET_SEARCH"]))
assert not any(map(brain.is_read_action, ["GMAIL_SEND_EMAIL", "SLACK_ADD_TO_LIST", "GMAIL_ADD_LABEL_TO_EMAIL", "GOOGLETASKS_INSERT_TASK", "GMAIL_REPLY_TO_THREAD",
                                          "NOTION_SOMETHING_UNKNOWN"]))
store.set_connector_mode("gmail", "read_only"); store.set_connector_mode("github", "paused"); store.set_connector_mode("trello", "full")
assert brain.account_block("GMAIL_FETCH_EMAILS") is None and "read-only" in brain.account_block("GMAIL_SEND_EMAIL")
assert "paused" in brain.account_block("GITHUB_LIST_NOTIFICATIONS") and brain.account_block("SLACK_SEND_MESSAGE") is None
assert "trello: full access" in brain.account_policy() and "github: paused" in brain.account_policy()
b = brain.Brain.__new__(brain.Brain)
b.plugins = {}  # (any real call would fail on this: nothing may reach Composio)
b.app_tools = {"GMAIL_SEND_EMAIL": {}, "GMAIL_FETCH_EMAILS": {}, "GITHUB_LIST_NOTIFICATIONS": {}}
assert list(b.active_app_tools()) == ["GMAIL_FETCH_EMAILS"] and "error" in b.run_app_tool("GMAIL_SEND_EMAIL", {})
srv = types.SimpleNamespace(call=lambda *a: 1 / 0)
b.tool_owner = {"COMPOSIO_MULTI_EXECUTE_TOOL": (srv, "COMPOSIO_MULTI_EXECUTE_TOOL")}
assert "paused" in b._run_tool("COMPOSIO_MULTI_EXECUTE_TOOL", {"tools": [{"tool_slug": "GITHUB_CREATE_AN_ISSUE"}]})[0]["error"]
try:
    store.set_connector_mode("gmail", "yolo"); raise AssertionError("bad mode accepted")
except ValueError:
    pass
store.set_connector_mode("gmail", "ask")
assert "gmail" not in store.connector_modes()

import json, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# Classroom: work already turned in is never "due"; when Classroom can't be reached the briefing says so, not "nothing"
def due_in(seconds):
    g = time.gmtime(time.time() + seconds)
    return {"dueDate": {"year": g.tm_year, "month": g.tm_mon, "day": g.tm_mday}, "dueTime": {"hours": g.tm_hour, "minutes": g.tm_min}}
CLASS = {"GOOGLE_CLASSROOM_COURSES_LIST": {"courses": [{"id": "c1", "name": "Maths"}]},
         "GOOGLE_CLASSROOM_COURSE_WORK_LIST": {"courseWork": [{"id": "w1", "title": "Quiz", **due_in(5 * 3600)},
                                                              {"id": "w2", "title": "Lab", **due_in(2 * 86400)}]},
         "GOOGLE_CLASSROOM_COURSE_WORK_STUDENT_SUBMISSIONS_LIST": {"studentSubmissions": [
             {"courseWorkId": "w1", "state": "TURNED_IN", "submissionHistory": [
                 {"stateHistory": {"state": "CREATED", "stateTimestamp": "2026-10-01T08:00:00.1Z"}},
                 {"stateHistory": {"state": "TURNED_IN", "stateTimestamp": "2026-10-03T09:30:00.123Z"}}]},
             {"courseWorkId": "w2", "state": "CREATED"}]}}
b = brain.Brain.__new__(brain.Brain)
b.connected, b.plugins = {"google_classroom"}, {}
b.app_data = lambda slug, args: CLASS.get(slug)  # (stands in for Composio: nothing may reach a real account)
assert [(w["id"], w["done"]) for w in b.classroom_work(3)] == [("w1", True), ("w2", False)]
# and when it was turned in, so "did I submit it?" never gets an invented "earlier today"
import calendar as _cal
assert b.classroom_work(3)[0]["turned_in_at"] == _cal.timegm((2026, 10, 3, 9, 30, 0))
assert b.classroom_due(3)["due"][0]["turned_in"] == "yes, " + time.strftime("%a %d %b, %H:%M", time.localtime(_cal.timegm((2026, 10, 3, 9, 30, 0))))
assert b.classroom_due(3)["due"][1]["turned_in"] == "no"
real_get = brain.requests.get
brain.requests.get = lambda *a, **k: (_ for _ in ()).throw(brain.requests.ConnectionError("offline"))  # (no weather)
day = b.briefing()
assert day["weather"].startswith("couldn't check") and day["unread_emails"] == "not connected"
assert [x.split(" (")[0] for x in day["classroom_due_this_week_not_turned_in"]] == ["Lab"]
b.app_data = lambda slug, args: None
assert b.briefing()["classroom_due_this_week_not_turned_in"].startswith("couldn't check")
# announcements: every course in one call, newest first, by the course's full name; a course that failed is named
POSTS = {"c1": {"announcements": [{"text": "Quiz moved", "updateTime": "2026-10-10T08:00:00Z"}]},
         "c2": {"announcements": [{"text": "Lab tonight", "updateTime": "2026-10-12T08:00:00.5Z"}]}}
COURSES = {"courses": [{"id": "c1", "name": "MAT1", "section": "Calculus 3"}, {"id": "c2", "name": "CS1"}, {"id": "c3", "name": "EN1"}]}
b.app_data = lambda slug, args: COURSES if slug == "GOOGLE_CLASSROOM_COURSES_LIST" else POSTS.get(args["courseId"])
news = b.classroom_announcements()
assert [(a["course"], a["text"]) for a in news["announcements"]] == [("CS1", "Lab tonight"), ("MAT1 - Calculus 3", "Quiz moved")]
assert news["couldnt_check"] == ["EN1"] and b.classroom_announcements(1)["announcements"][0]["text"] == "Lab tonight"
b.app_data = lambda slug, args: None
assert b.classroom_announcements() == {"error": "couldn't reach Google Classroom"}
brain.requests.get = real_get
# deadline reminders: set for work not turned in, cancelled once it is
b.app_data = lambda slug, args: CLASS.get(slug)
jarvis.deadline_pass(b)
assert sum("Lab" in r["text"] for r in store.reminders()) == 2 and not any("Quiz" in r["text"] for r in store.reminders())
CLASS["GOOGLE_CLASSROOM_COURSE_WORK_STUDENT_SUBMISSIONS_LIST"]["studentSubmissions"][1]["state"] = "TURNED_IN"
jarvis.deadline_pass(b)
assert not any("Lab" in r["text"] for r in store.reminders())

# a remote plugin's login is refreshed half an hour early: the SDK takes a stored token for a fresh one, and a token
# that expires mid-connection gets refused, which the SDK answers with a whole new browser sign-in
refreshes = []
class Auth(BaseHTTPRequestHandler):
    def reply(self, data):
        out = json.dumps(data).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(out)))
        self.end_headers(); self.wfile.write(out)
    def do_GET(self):
        self.reply({"issuer": base, "authorization_endpoint": base + "/authorize", "token_endpoint": base + "/token"})
    def do_POST(self):
        refreshes.append(self.rfile.read(int(self.headers["Content-Length"])))
        self.reply({"access_token": f"new{len(refreshes)}", "token_type": "Bearer", "expires_in": 3600, "refresh_token": "r2"})
    def log_message(self, *a):
        pass
auth = HTTPServer(("127.0.0.1", 0), Auth)
base = f"http://127.0.0.1:{auth.server_port}"
threading.Thread(target=auth.serve_forever, daemon=True).start()
store.write_json(os.path.join(store.DATA, "mcp", "acme.json"), {"client": {"client_id": "jarvis", "redirect_uris": [f"{base}/cb"]},
    "tokens": {"access_token": "old", "token_type": "Bearer", "refresh_token": "r1", "expires_in": 3600, "expires_at": time.time() + 600}})
tokens = brain.oauth_provider("acme", base + "/mcp", print).context.storage
assert asyncio.run(tokens.get_tokens()).access_token == "new1" and b"r1" in refreshes[0]  # 10 minutes left: renewed now
again = asyncio.run(tokens.get_tokens())
assert again.access_token == "new1" and 3500 < again.expires_in <= 3600 and len(refreshes) == 1  # fresh: kept, with what's left
# the server refuses a token that hasn't expired: renewed with the refresh token, no sign-in tab (one opened out of the blue)
try:
    asyncio.run(brain.oauth_provider("acme", base + "/mcp", print).context.redirect_handler(base + "/authorize"))
    raise AssertionError("went to the browser")
except RuntimeError as e:
    assert "renewed" in str(e) and len(refreshes) == 2, e
auth.shutdown()
auth.server_close()
# the login server is out of reach (a Composio outage): a login with time left is kept, and no sign-in tab opens
brain.renewed_at.clear()
opened, real_open = [], system.open_target
system.open_target = opened.append
store.write_json(os.path.join(store.DATA, "mcp", "acme.json"), {"client": {"client_id": "jarvis", "redirect_uris": [f"{base}/cb"]},
    "tokens": {"access_token": "old", "token_type": "Bearer", "refresh_token": "r1", "expires_in": 3600, "expires_at": time.time() + 600}})
assert asyncio.run(tokens.get_tokens()).access_token == "old"
try:
    asyncio.run(brain.oauth_provider("acme", base + "/mcp", print).context.redirect_handler(base + "/authorize"))
    raise AssertionError("went to the browser")
except ConnectionError as e:
    assert "couldn't reach" in str(e) and not opened and brain.unreachable(e), e
system.open_target = real_open
# a plugin out of reach (the PC started before its network): marked so, to be tried again, and said once, not at every try
mcp_loop = asyncio.new_event_loop()
threading.Thread(target=mcp_loop.run_forever, daemon=True).start()
said = []
gone = brain.McpServer("gone", {"url": "http://127.0.0.1:9/mcp"}, mcp_loop, said.append)
gone.connect()
gone.connect()
assert gone.status == "error" and gone.offline and len(said) == 1 and gone.error == "Can't reach 127.0.0.1", (gone.error, said)
missing = brain.McpServer("missing", {"command": "/no/such/mcp-server"}, mcp_loop, said.append)
missing.connect()
assert missing.status == "error" and not missing.offline  # (a missing command: no retry brings it back)
# ...and its accounts are still connected: the agent said Gmail "isn't connected" during a Composio outage
down_brain = brain.Brain.__new__(brain.Brain)
down_brain.plugins = {"composio": gone}
assert "still connected" in down_brain.accounts_down() and "never that an account isn't connected" in down_brain.accounts_down()
try:
    down_brain._composio([])
    raise AssertionError("no error")
except RuntimeError as e:
    assert "still connected" in str(e)
assert not brain.unreachable(RuntimeError("composio sign-in timed out")) and brain.unreachable(ExceptionGroup("g", [ConnectionRefusedError()]))

# your own providers: keys stay out of settings, never go over plain http to another machine
store.set_secret("openai", "sk-test-123")
assert store.secret("openai") == "sk-test-123" and "sk-test" not in open(store.SETTINGS_FILE).read()
assert os.stat(store.KEYS_FILE).st_mode & 0o077 == 0 or os.name == "nt"
store.set_secret("openai", "")
assert store.secret("openai") == ""
try:
    brain.OpenAICompatible("x", "http://example.com/v1", "sk-1"); raise AssertionError("key sent over http")
except RuntimeError:
    pass
brain.OpenAICompatible("x", "http://localhost:1234/v1", "sk-1")  # (this machine is fine)
b = brain.Brain.__new__(brain.Brain)
b.backends, b.down_until = {}, {}
assert b.backend("nosuch")[0] is None and "no API key" in b.backend("openai")[1]
brain.chain = lambda: [("openai", "gpt-a", "low"), ("openai", "gpt-b", "low")]
try:
    b._generate([]); raise AssertionError("no key, yet it answered")
except RuntimeError as e:
    assert str(e).count("no API key") == 1, e  # a missing key is said once, not once per model

# OpenAI-style translation: tool calls and results paired by id, pictures as data URLs, Gemini signatures only when asked
turns = [{"role": "user", "parts": [{"text": "hi"}, {"inlineData": {"mimeType": "image/png", "data": "QUJD"}}]},
         {"role": "model", "parts": [{"text": "looking"}, {"functionCall": {"name": "look", "args": {"q": 1}}, "thoughtSignature": "sig"}]},
         {"role": "user", "parts": [{"functionResponse": {"name": "look", "response": {"answer": "a cat"}}}]}]
m = brain.to_openai(turns, "be brief")
assert [x["role"] for x in m] == ["system", "user", "assistant", "tool"]
assert m[1]["content"][1]["image_url"]["url"] == "data:image/png;base64,QUJD"
assert m[3]["tool_call_id"] == m[2]["tool_calls"][0]["id"] and "extra_content" not in m[2]["tool_calls"][0]
assert brain.to_openai(turns, signatures=True)[1]["tool_calls"][0]["extra_content"]["google"]["thought_signature"] == "sig"
parts = brain.from_openai({"choices": [{"message": {"content": "ok", "reasoning_content": "hmm", "tool_calls": [
    {"id": "c1", "function": {"name": "remember", "arguments": '{"fact": "x"}'}}]}}]})
assert parts == [{"text": "hmm", "thought": True}, {"text": "ok"}, {"functionCall": {"name": "remember", "args": {"fact": "x"}, "id": "c1"}}]

# a local keyless server (like Ollama): tools offered, no Authorization header, tool call then answer
seen = []
class Fake(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        seen.append((self.headers.get("Authorization"), body))
        msg = ({"content": None, "tool_calls": [{"id": "t1", "type": "function", "function": {"name": "list_reminders", "arguments": "{}"}}]}
               if len(seen) == 1 else {"content": "You have no reminders."})
        out = json.dumps({"choices": [{"message": msg}]}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)
    def log_message(self, *a):
        pass
srv = HTTPServer(("127.0.0.1", 0), Fake)
threading.Thread(target=srv.serve_forever, daemon=True).start()
store.save_custom_provider("local", f"http://127.0.0.1:{srv.server_port}/v1")
b = brain.Brain.__new__(brain.Brain)
b.backends, b.down_until, b.contents, b.cancel, b.plugins, b.app_tools, b.notify = {}, {}, [], threading.Event(), {}, {}, print
b.ask_lock, b.remote = threading.Lock(), False
brain.chain = lambda: [("local", "tiny-model", "low")]
assert b.ask("any reminders?") == "You have no reminders."
assert seen[0][0] is None and any(t["function"]["name"] == "list_reminders" for t in seen[0][1]["tools"])
last = seen[1][1]["messages"][-1]
assert last["role"] == "tool" and last["tool_call_id"] == "t1" and '"reminders"' in last["content"], seen[1][1]["messages"][-3:]
srv.shutdown()

# the voice session's whole config builds (tool schemas included), with the name the user asked for
from google import genai
store.set_memory("- User prefers to be called Q.")
live.t, live.skip_app_tools, live.resume_handle, live.resume_next = genai.types, False, None, False
live.brain = types.SimpleNamespace(accounts={}, app_tools_for=set(), connected=set(), plugin_status=lambda: [], active_app_tools=lambda: {})
config = live._config()
assert 'Call the user "Q"' in config.system_instruction and "{ADDRESS}" not in config.system_instruction
assert any(d.name == "act" and "expect" in str(d.parameters_json_schema) for d in config.tools[0].function_declarations)
store.set_memory("")
# what Jarvis sent in earlier conversations reaches a new voice session, so a joke isn't sent again after a restart
real_sessions, jarvis.sessions = jarvis.sessions, store.Sessions()
jarvis.sessions.dir = tempfile.mkdtemp()
jarvis.sessions.add({"who": "you", "text": "type a dark joke"})
jarvis.sessions.add({"who": "jarvis", "text": "Sent: 'the one about the garden'"})
jarvis.sessions.add({"who": "jarvis", "text": "Here you are."})
jarvis.sessions.new()
assert jarvis.sessions.sent() == ["'the one about the garden'"]
assert "never send one of these again" in live._config().system_instruction and "- 'the one about the garden'" in live._config().system_instruction
jarvis.sessions = real_sessions

assert os.environ["TQDM_DISABLE"] == "1"  # (tqdm's \r bars hid whole conversations in the log)

# the prompts describe this computer, and nothing personal or private ships
prompt = brain.Brain._system(types.SimpleNamespace(accounts_down=lambda: ""))
assert "{SYSTEM}" not in prompt and ("Windows" in prompt or "Linux" in prompt)
assert "{SYSTEM}" not in jarvis.LIVE_PROMPT.replace("{SYSTEM}", system.describe())
assert "kcalc" not in jarvis.VOICE_ACT or system.CALC == "kcalc"
assert list(brain.BACKENDS)[0] == "aistudio"
# the web guard: every fetch (Jarvis's own and the headless browser's) refuses this PC and the local network, redirects included
import http.server
class Local(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"LOCAL SECRET")
    def log_message(self, *a):
        pass
local = http.server.HTTPServer(("127.0.0.1", 0), Local)
threading.Thread(target=local.serve_forever, daemon=True).start()
guard = brain.guard_proxy()
sess = brain.requests.Session(); sess.trust_env = False
assert sess.get(f"http://127.0.0.1:{local.server_port}/", proxies={"http": guard, "https": guard}, timeout=5).status_code == 403
assert "error" in brain.tool_read_webpage(f"http://127.0.0.1:{local.server_port}/") and "error" in brain.tool_show_image("http://[::1]/x.png")
local.shutdown()

# a model can make an account stricter but never looser or disconnect it (that's for the user, on the Accounts page)
b = brain.Brain.__new__(brain.Brain)
b.connected = set()
store.set_connector_mode("gmail", "read_only")
assert "error" in b.account_settings("gmail", mode="full") and "error" in b.account_settings("gmail", action="disconnect")
assert store.connector_modes()["gmail"] == "read_only" and "result" in b.account_settings("gmail", mode="paused")
store.set_connector_mode("gmail", "ask")

# weather needs no model or search: a place name in, today and the next days out
real_get = brain.requests.get
brain.requests.get = lambda url, **k: types.SimpleNamespace(ok=True, text="", json=lambda: (
    {"results": [{"name": "Rome", "country": "Italy", "latitude": 41.9, "longitude": 12.5}]} if "geocoding" in url else
    {"current": {"time": "2026-10-09T10:00", "weather_code": 3, "temperature_2m": 18.4, "apparent_temperature": 17, "relative_humidity_2m": 60,
                 "wind_speed_10m": 9}, "daily": {"weather_code": [61, 3, 0], "temperature_2m_max": [20, 21, 22], "temperature_2m_min": [12, 13, 14],
                 "precipitation_probability_max": [40, 10, None], "sunrise": ["2026-10-09T06:50"] * 3, "sunset": ["2026-10-09T18:10"] * 3}}))
asked_places, real_here, real_get_weather = [], brain.here, brain.requests.get
brain.here = lambda: ""  # the network can't tell: where the user said they live, from memory
brain.requests.get = lambda url, params=None, **k: asked_places.append((params or {}).get("name")) or real_get_weather(url, params=params, **k)
store.set_memory("- likes tea\n- The user lives in Rome now.")
assert brain.memory_city() == "Rome" and "place" in brain.tool_weather() and asked_places[0] == "Rome", asked_places
store.set_memory("")
brain.here, brain.requests.get = real_here, real_get_weather
w = brain.tool_weather("Rome")
assert w["place"] == "Rome, Italy" and w["now"].startswith("overcast, 18") and w["forecast"][0].startswith("today: light rain") and "0% chance" in w["forecast"][2]
brain.requests.get = lambda url, **k: types.SimpleNamespace(ok=True, text="", json=lambda: (
    {"results": [{"name": "Rome", "country": "Italy", "latitude": 41.9, "longitude": 12.5}]} if "geocoding" in url else
    {"error": True, "reason": "busy"}))
assert "busy" in brain.tool_weather("Rome")["error"]  # a forecast-service error is said, not a crash
brain.requests.get = real_get

# an image model that answers without a picture (refused, no quota) hands over to the next one
import base64
asked, real_painter, real_models, real_dir = [], brain.painter[0], brain.IMAGE_MODELS, brain.IMAGE_DIR
brain.IMAGE_MODELS, brain.IMAGE_DIR = [("a", "first", None), ("b", "second", None)], tempfile.mkdtemp()
brain.painter[0] = lambda contents, entries: asked.append(entries[0][1]) or (
    [{"text": ""}] if entries[0][1] == "first" else [{"inlineData": {"data": base64.b64encode(b"\x89PNG..").decode()}}])
assert "result" in brain.tool_make_image("a cat") and asked == ["first", "second"], asked
brain.painter[0], brain.IMAGE_MODELS, brain.IMAGE_DIR = real_painter, real_models, real_dir

# a Drive file by name: an exact name beats newer near-misses, Docs are exported as text and read like a local file
db = brain.Brain.__new__(brain.Brain)
db.connected, calls = {"googledrive"}, []
db.app_data = lambda slug, args: calls.append((slug, args)) or (
    {"files": [{"id": "a", "name": "Graph notes v2.pdf", "mimeType": "application/pdf"},
               {"id": "b", "name": "Graph notes", "mimeType": "application/vnd.google-apps.document"}]}
    if slug == "GOOGLEDRIVE_FIND_FILE" else {"downloaded_file_content": {"s3url": "https://files.example.com/x"}})
real_fetch = brain.fetch
brain.fetch = lambda url, **k: types.SimpleNamespace(ok=True, status_code=200, content=b"Graphs: a slope is rise over run.")
got = db.drive_file("graph notes")
assert got["file"] == "Graph notes" and "rise over run" in got["text"] and got["other_matches"] == ["Graph notes v2.pdf"], got
assert calls[1] == ("GOOGLEDRIVE_DOWNLOAD_FILE", {"fileId": "b", "mime_type": "text/plain"}), calls
brain.fetch = real_fetch
db.connected = set()
assert "isn't connected" in db.drive_file("x")["error"]

# each job's models: the setting when set ("none" thinking for picture models), else the built-in list; bad lines are refused
store.update_settings({"point_models": ["aistudio quick-model low"], "image_models": ["aistudio paint-model none"]})
assert brain.models_for("point") == [("aistudio", "quick-model", "low")] and brain.models_for("image") == [("aistudio", "paint-model", None)]
jobs = {j["job"]: j for j in brain.Brain.model_jobs()}
assert jobs["point"]["custom"] and jobs["point"]["models"] == ["aistudio quick-model low"] and not jobs["look"]["custom"], jobs
store.update_settings({"point_models": [], "image_models": []})
assert brain.models_for("point") == brain.POINT_MODELS and brain.models_for("agent") == brain.chain()
try:
    store.update_settings({"look_models": ["just-a-model"]})
    raise AssertionError("a model line without backend and thinking was accepted")
except ValueError:
    pass

# the voice list leaves out models whose tool calls never reach Jarvis
studio = brain.AIStudio.__new__(brain.AIStudio)
studio._listing = lambda: [("gemini-3.8-live", ["bidiGenerateContent"]), ("gemini-3.8-live-extended-thinking", ["bidiGenerateContent"]),
                           ("gemini-3.8-flash", ["generateContent"])]
assert studio.live_models() == ["gemini-3.8-live"], studio.live_models()

# Settings lists the models each backend offers: from its own list, or (without one) the ones Jarvis already uses with it
class Listed:
    def models(self):
        return ["big-model", "small-model"]

    def live_models(self):
        return ["voice-model"]


class Broken:
    def models(self):
        raise RuntimeError("401 bad key")


lb = brain.Brain.__new__(brain.Brain)
real_lists = brain.BACKENDS, brain.providers, brain.chain
brain.BACKENDS, brain.providers = {"aistudio": Listed, "private": object}, (lambda: {"other": "https://x/v1"})
brain.chain = lambda: [("private", "known-model", "high"), ("aistudio", "big-model", "low")]
lb.backend = lambda name: ((Listed() if name == "aistudio" else Broken() if name == "other" else object()), "")
got = {r["name"]: r for r in lb.available_models()["backends"]}
assert got["aistudio"]["models"] == ["big-model", "small-model"] and "error" not in got["aistudio"], got
assert got["private"]["models"] == ["known-model"] and "401" in got["other"]["error"], got
assert lb.available_models()["live"] == ["voice-model"]
brain.BACKENDS, brain.providers, brain.chain = real_lists

# the window: line icons draw, and every page loads against the real API without a single QML warning
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QColor
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication
QQuickWindow.setDefaultAlphaBuffer(True)
qt = QApplication([])
import window
pix = window.icon_pixmap("home", QColor("#9c9ab0"), 48).toImage()
assert any(pix.pixelColor(x, y).alpha() > 0 for x in range(48) for y in range(48)), "the line icons came out empty"
warnings = []
qInstallMessageHandler(lambda kind, ctx, msg: warnings.append(msg) if kind != QtMsgType.QtDebugMsg and "portal" not in msg
                       and "Cannot find font directory" not in msg else None)  # (headless Windows: no font folder for the offscreen platform)
stub = types.SimpleNamespace(plugin_status=lambda: [], workspaces=lambda: [], app_tools={}, model_jobs=brain.Brain.model_jobs, available_models=lambda: {
    "backends": [{"name": "aistudio", "models": ["gemini-3.8-flash", "gemini-3.7-flash"]},
                 {"name": "openai", "models": [], "error": "no API key"}], "live": ["gemini-3.8-live"]})
live.mic = False
canned = {"/api/health": {"checks": [{"name": "Microphone", "ok": False, "detail": "no audio", "fix": "check it", "page": "settings"}],
                          "usage": {"aistudio gemini-3.8-flash": 3}},
          "/api/setup/key": {"ok": False, "detail": "no key yet"}}  # (the real ones take a screenshot and call Google)
win = window.Window(get=lambda path: canned.get(path) or jarvis.api_get(path, stub), post=lambda path, data: {"ok": True}, tool_label=jarvis.tool_label,
                    live=live, shown_state=jarvis.shown_state, version="test", show=True)
root = win.engine.rootObjects()[0]
assert root.property("needsSetup") is not None
for page in ("chats", "activity", "accounts", "plugins", "models", "memory", "settings", "health", "home"):
    root.setProperty("page", page)
    qt.processEvents()
end = time.time() + 1.5
while time.time() < end:
    qt.processEvents()
    time.sleep(0.02)
assert not warnings, ascii(warnings)[:4000]

# every function a page calls on itself exists (Settings lost its set() once, and every switch on it silently did nothing)
import glob, re
for qml in glob.glob(os.path.join(os.path.dirname(os.path.abspath(jarvis.__file__)), "qml", "*.qml")):
    src = open(qml).read()
    root_id = re.search(r"^\S.*\{\s*\n\s*id: (\w+)", src, re.M)
    if root_id:
        builtin = {"startSystemMove", "startSystemResize", "showMinimized", "showNormal", "showMaximized", "show", "hide", "raise",
                   "requestActivate", "close", "forceActiveFocus"}  # (Qt's own, on Window and Item)
        for name in set(re.findall(rf"\b{root_id[1]}\.(\w+)\(", src)) - builtin:
            assert re.search(rf"(?:function|signal) {name}\b", src), f"{os.path.basename(qml)} calls {root_id[1]}.{name}() but has no {name}"

# quick tools: silent responses to prevent duplicate replies, interruptions, and superseded turns
sent_responses = []
class FakeSession:
    async def send_tool_response(self, **kwargs):
        sent_responses.append(kwargs["function_responses"])

fake_session = FakeSession()
live.quick_tasks = {}
live.quick_gen = 1
live.stopped = False
live.user_spoke_at = live.interrupted_at = live.gemini_spoke_at = 0.0
live.running = 0
live.t = genai.types
live.brain = brain.Brain.__new__(brain.Brain)
live.brain.cancel = threading.Event()
live._tool = lambda fc, halt=None: asyncio.sleep(0.001, result={"result": "ok"})

# 1. query tool with no prior speech -> scheduling is None (speaks answer)
sent_responses.clear()
asyncio.run(live._quick(fake_session, [types.SimpleNamespace(name="look", id="1", args={})], gen=1, spoke_before=False))
assert sent_responses[0][0].scheduling is None

# 2. action tool where model already spoke -> scheduling is SILENT (no double reply)
sent_responses.clear()
asyncio.run(live._quick(fake_session, [types.SimpleNamespace(name="act", id="2", args={})], gen=1, spoke_before=True))
assert sent_responses[0][0].scheduling == "SILENT"

# 3. user spoke while tool was running -> scheduling is SILENT
sent_responses.clear()
live.user_spoke_at = time.time() + 10.0
asyncio.run(live._quick(fake_session, [types.SimpleNamespace(name="look", id="3", args={})], gen=1, spoke_before=False))
assert sent_responses[0][0].scheduling == "SILENT"
live.user_spoke_at = 0.0

# 4. superseded tool call -> scheduling is SILENT
sent_responses.clear()
live.quick_gen = 2
asyncio.run(live._quick(fake_session, [types.SimpleNamespace(name="look", id="4", args={})], gen=1, spoke_before=False))
assert sent_responses[0][0].scheduling == "SILENT"
live.quick_gen = 1

# 5. stop_listening is always SILENT
sent_responses.clear()
asyncio.run(live._quick(fake_session, [types.SimpleNamespace(name="stop_listening", id="5", args={})], gen=1, spoke_before=False))
assert sent_responses[0][0].scheduling == "SILENT"
# ...and it ends the request, so the watchdog doesn't reconnect 12 s later and say the goodbye late
live.inflight = {"text": None, "heard": "that's all", "since": time.time(), "tool": True, "answered": False, "recovered": False}
asyncio.run(type(live)._tool(live, types.SimpleNamespace(name="stop_listening", id="5", args={})))
assert live.inflight is None and not live.mic

# 6. act immediately aborts when interrupted
brain.interrupt_act()
res = brain.tool_act([{"wait": 5}], screenshot_after=False)
assert res["error"] == "interrupted"
brain.reset_interrupt_act()


# a newer voice call replacing one mid-act stops only the old act: the old call's cancel never reaches the new one
# (it did: "act 2.1s (voice) error: interrupted" right after "just type the message")
del live._tool  # the real one, which hands each act its own halt
live.brain = brain.Brain.__new__(brain.Brain)
live.brain.cancel, live.brain.tool_owner, live.brain.app_tools = threading.Event(), {}, {}
live.inflight, live.heard, live.said, live.quick_tasks, live.running, live.turn_spoke = None, "", "", {}, 0, False
live.user_spoke_at = live.interrupted_at = live.gemini_spoke_at = 0.0
brain.reset_interrupt_act()
sent_responses.clear()
def call(fc):
    return types.SimpleNamespace(server_content=None, session_resumption_update=None, go_away=None,
                                 tool_call=types.SimpleNamespace(function_calls=[fc]))
async def replaced():
    await live._handle(fake_session, call(types.SimpleNamespace(name="act", id="old", args={"steps": [{"wait": 0.4}, {"wait": 0.4}]})))
    await asyncio.sleep(0.1)
    await live._handle(fake_session, call(types.SimpleNamespace(name="act", id="new", args={"steps": [{"wait": 0.3}, {"wait": 0.3}]})))
    await asyncio.sleep(1.2)
asyncio.run(replaced())
got = {r.id: r.response for batch in sent_responses for r in batch}
assert got["new"].get("result") == ["waited 0.3s", "waited 0.3s"] and got["old"] == {"error": "cancelled"}, got

# cutting the voice off stops its own quick calls, never the background agent's screen work
async def barge_in():
    await live._handle(fake_session, types.SimpleNamespace(session_resumption_update=None, go_away=None, tool_call=None,
        server_content=types.SimpleNamespace(interrupted=True, input_transcription=None, output_transcription=None,
                                             model_turn=None, turn_complete=False)))
asyncio.run(barge_in())
assert brain.tool_act([{"wait": 0}], screenshot_after=False) == {"result": ["waited 0s"]}

# KDE: kdotool says nothing when no window matches, which must not count as focused or closed
real_window = system.KDE, system.WAYLAND, system.have, system._kdo
system.KDE = system.WAYLAND = True
system.have = lambda program: True
system._kdo = lambda *args: ""
assert brain.tool_focus_window("Discord") == {"error": "no window matching Discord"}
assert brain.tool_close_window("kcalc") == {"error": "no window matching kcalc"}
system._kdo = lambda *args: "org.kde.kcalc"
assert brain.tool_focus_window("kcalc") == {"result": "focused kcalc"}
# a quote in a window title broke kdotool's KWin script (5 s, then "Error: Timed out"), which counted as focused
searched = []
system._kdo = lambda *args: searched.append(args[1]) or "Error: Timed out waiting for KWin script completion"
assert brain.tool_focus_window('vesktop: Discord | "Forum" | `x`') == {"error": 'no window matching vesktop: Discord | "Forum" | `x`'}
assert '"' not in searched[0] and "`" not in searched[0] and re.search(searched[0], 'Discord | "Forum" | `x`', re.I)
assert brain.tool_close_window(" ") == {"error": "no window name given"}  # (an empty name would match every window)
assert system._find_windows("") == []  # (X11 and Windows: close_window("") closed every window)
system.KDE, system.WAYLAND, system.have, system._kdo = real_window

# forget with nothing (or a letter) would match every line: it's refused, and the memory stays
kept = store.memory()
for text in ("", "  ", "a"):
    try:
        store.forget(text)
        raise AssertionError(f"forget({text!r}) was allowed")
    except ValueError:
        pass
assert store.memory() == kept

# the microphone keeps going when pw-record quits (PipeWire restarted): a new one takes over
import io
class Recorder:
    def __init__(self, data):
        self.stdout = io.BytesIO(data)

    def wait(self):
        return 0
recorders = [Recorder(b"\1\0" * 1280), Recorder(b"\2\0" * 1280)]
real_mic = system.subprocess, system.time, system.have, system.IS_WINDOWS
system.IS_WINDOWS = False  # (the pw-record path; Windows uses sounddevice)
system.subprocess = types.SimpleNamespace(Popen=lambda *a, **k: recorders.pop(0), PIPE=-1, DEVNULL=-3)
system.time = types.SimpleNamespace(time=time.time, sleep=lambda seconds: None)
system.have = lambda program: program == "pw-record"
mic = system.mic_frames()
assert next(mic)[0] == 1 and next(mic)[0] == 2
# on the echo canceller the stream is pinned there: WirePlumber's "follow the default mic" moved it onto the raw mic
started = []
system.subprocess.Popen = lambda args, **k: started.append(args) or Recorder(b"\1\0" * 1280)
next(system.mic_frames("jarvis-ec-source"))
assert started[0][1:5] == ["--target", "jarvis-ec-source", "-P", "{ node.dont-move = true }"], started
# raw samples in our byte order: to a pipe pw-record 1.6.10 writes big-endian .au, and loud speech came in as noise
assert "--raw" in started[0], started
system.subprocess, system.time, system.have, system.IS_WINDOWS = real_mic

# which mic pw-record really reads: its node's client is the process, and a link runs into that node
dump = [{"id": 70, "type": "PipeWire:Interface:Client", "info": {"props": {"application.process.id": 4733}}},
        {"id": 73, "type": "PipeWire:Interface:Node", "info": {"props": {"node.name": "pw-record", "client.id": 70}}},
        {"id": 36, "type": "PipeWire:Interface:Node", "info": {"props": {"node.name": "alsa_input.x"}}},
        {"id": 90, "type": "PipeWire:Interface:Link", "info": {"output-node-id": 36, "input-node-id": 73}}]
real_subprocess = system.subprocess
system.subprocess = types.SimpleNamespace(run=lambda *a, **k: types.SimpleNamespace(stdout=json.dumps(dump)),
                                          TimeoutExpired=real_subprocess.TimeoutExpired)
assert system.mic_source(4733) == "alsa_input.x" and system.mic_source(1) == ""
system.subprocess = real_subprocess

# Jarvis's own volume control: quiet or loud speech comes out about the same; noise and Jarvis's own voice don't count
for loudness in (40, 400, 20000):
    mic = jarvis.MicLevel()
    for _ in range(25):
        mic(frame(2))  # a quiet room
    for _ in range(150):
        out = mic(frame(loudness))
    assert 2500 < np.sqrt(np.mean(out.astype(np.float32) ** 2)) < 6000, (loudness, mic.gain)
mic = jarvis.MicLevel()
for _ in range(100):
    mic(frame(30000), own_voice=True)
assert mic.gain == 1.0
# the slider pushed up between two sentences: the first loud word is already turned down, not clipped
mic = jarvis.MicLevel()
for _ in range(150):
    mic(frame(300))
out = mic(frame(6000))
assert np.sqrt(np.mean(out.astype(np.float32) ** 2)) < 6000 and not (np.abs(out) == 32767).any(), mic.gain

# a long name with underscores is looked up by name; only when no file has it is it taken for an id
db.connected, calls = {"googledrive"}, []
db.app_data = lambda slug, args: calls.append((slug, args)) or (
    ({"files": [{"id": "c", "name": "Lab_Report_Final_Version_2.txt", "mimeType": "text/plain"}]} if "Lab_Report" in args["q"] else {"files": []})
    if slug == "GOOGLEDRIVE_FIND_FILE" else {"downloaded_file_content": {"s3url": "https://files.example.com/x"}})
brain.fetch = lambda url, **k: types.SimpleNamespace(ok=True, status_code=200, content=b"Results: it works.")
assert db.drive_file("Lab_Report_Final_Version_2")["file"] == "Lab_Report_Final_Version_2.txt" and calls[1][1]["fileId"] == "c", calls
calls.clear()
assert "it works" in db.drive_file("1AbCdEfGhIjKlMnOpQrStUvWxYz012345")["text"]
assert calls[1] == ("GOOGLEDRIVE_DOWNLOAD_FILE", {"fileId": "1AbCdEfGhIjKlMnOpQrStUvWxYz012345"}), calls
brain.fetch = real_fetch

# a network blip marks every model down at once: they're still tried (not refused for minutes until a probe gets through)
gb, tried = brain.Brain.__new__(brain.Brain), []
gb.notify = lambda text: None
gb.backends = {"fake": types.SimpleNamespace(generate=lambda contents, model, thinking, **k: tried.append(model) or [{"text": model}])}
gb.down_until = {("fake", "m1", None): float("inf"), ("fake", "m2", None): float("inf")}
assert gb._generate([], entries=[("fake", "m1", None), ("fake", "m2", None)]) == [{"text": "m1"}] and tried == ["m1"]
def still_down(contents, model, thinking, **k):
    tried.append(model)
    raise ConnectionError("network down")
gb.backends["fake"].generate, tried[:] = still_down, []  # still down: one try, not a timeout per model
try:
    gb._generate([], entries=[("fake", "m1", None), ("fake", "m2", None)])
    raise AssertionError("no model answered, yet nothing was raised")
except RuntimeError:
    assert tried == ["m1"], tried
gb.backends["fake"].generate = lambda contents, model, thinking, **k: tried.append(model) or [{"text": model}]
gb.down_until, tried[:] = {("fake", "m1", None): float("inf")}, []  # one is up: the down one is skipped, as before
assert gb._generate([], entries=[("fake", "m1", None), ("fake", "m2", None)]) == [{"text": "m2"}] and tried == ["m2"]

# ...but a rate limit is kept even then: those models aren't hammered
gb.down_until, tried[:] = {("fake", "m1", None): time.time() + 60, ("fake", "m2", None): float("inf")}, []
assert gb._generate([], entries=[("fake", "m1", None), ("fake", "m2", None)]) == [{"text": "m2"}] and tried == ["m2"]
gb.down_until = {("fake", "m1", None): time.time() + 60}
try:
    gb._generate([], entries=[("fake", "m1", None)])
    raise AssertionError("a rate-limited model was tried")
except RuntimeError:
    pass

# a reminder after Stop is a new turn: Stop doesn't silence it or switch off its recovery
live._go = lambda coro: coro.close()
live.stopped = True
live.announce("Take the bins out")
assert live.stopped is False
# quiet hours (or Do not disturb): nothing is said unprompted, except what the user always wants to hear (a WhatsApp VIP)
announced = []
live._go = lambda coro: announced.append(coro) or coro.close()
store.update_settings({"do_not_disturb": True})
live.announce("Take the bins out")
assert announced == []
live.announce("Mum is calling you on WhatsApp.", loud=True)
assert len(announced) == 1
store.update_settings({"do_not_disturb": False})
live._go = lambda coro: coro.close()

# after Stop, an unanswered request doesn't end the watchdog (it used to hand over to a _recover that did nothing, and
# then nothing hung up idle sessions or closed the mic for the rest of that session)
async def watch_after_stop():
    now = time.time()
    live.stopped, live.working, live.running, live.question, live.waiting, live.mic = True, False, 0, None, False, False
    live.last = live.last_msg = live.voice_at = now - 20
    live.speaker = types.SimpleNamespace(until=0.0, busy=lambda: False, stop=lambda: None)
    live.inflight = {"text": None, "heard": "what's the weather like today", "since": now - 20, "tool": False, "answered": False, "recovered": False}
    watcher = asyncio.create_task(live._watch())
    await asyncio.sleep(0.6)
    alive = not watcher.done()
    watcher.cancel()
    return alive
assert asyncio.run(watch_after_stop()) and live.inflight is None

# a stray word Gemini rightly ignored ("real", a game's noise) isn't a dropped session: no reconnect, no re-ask
recovering, real_recover = [], live._recover
live._recover = lambda why: recovering.append(why) or asyncio.sleep(0)
live.stopped = False
async def watch_stray():
    now = time.time()
    live.last = live.last_msg = live.voice_at = now - 20
    live.inflight = {"text": None, "heard": " real", "since": now - 20, "tool": False, "answered": False, "recovered": False}
    watcher = asyncio.create_task(live._watch())
    await asyncio.sleep(0.6)
    alive = not watcher.done()
    watcher.cancel()
    return alive
assert asyncio.run(watch_stray()) and live.inflight is None and recovering == []
# an announcement (a reminder, a scheduled task's outcome) waits 25 s before reconnecting, not 12, and if even the retry
# gets no answer it isn't "please say it again": the user said nothing
async def watch_announce(quiet, recovered):
    now = time.time()
    live.last = live.last_msg = live.voice_at = now - quiet
    live.inflight = {"text": "(Tell the user...)", "heard": "", "since": now - quiet, "tool": False, "answered": False,
                     "recovered": recovered, "announce": True}
    watcher = asyncio.create_task(live._watch())
    await asyncio.sleep(0.6)
    watcher.cancel()
logged = []
jarvis.emit, real_emit = (lambda kind, **kw: logged.append(kw.get("text"))), jarvis.emit
asyncio.run(watch_announce(15, False))
assert recovering == [] and live.inflight is not None
asyncio.run(watch_announce(26, False))
assert recovering == ["no answer for 25 s"]
asyncio.run(watch_announce(26, True))
assert live.inflight is None and not any("say it again" in str(t) for t in logged)
jarvis.emit = real_emit
live._recover = real_recover

# Stop pressed just as the task asks its question: it isn't asked, and the mic stays off
asked_voice.clear()
live._go = lambda coro: asked_voice.append(coro) or coro.close()
live.stopped, live.mic, cancelled = True, False, threading.Event()
cancelled.set()
assert live.ask_from_task("Which Sam?", cancelled) is None and asked_voice == [] and live.stopped and not live.mic

# risky commands wait for a yes (unless the safety setting is off); ordinary ones just run
assert brain.risky_command("rm -rf ~/old") and brain.risky_command("echo hi > notes.txt") and brain.risky_command("ls; sudo reboot")
assert not brain.risky_command("ls ~/Downloads") and not brain.risky_command("wpctl set-volume @DEFAULT_AUDIO_SINK@ 50%") \
    and not brain.risky_command("ls 2>&1") and not brain.risky_command("cat x > /dev/null")
ran, real_shell = [], system.shell
system.shell = lambda command, timeout: ran.append(command) or (0, "done")
assert "not run" in brain.tool_run_command("rm ~/old.txt")["error"] and ran == []
assert brain.tool_run_command("rm ~/old.txt", confirmed=True)["output"] == "done" and brain.tool_run_command("df -h")["exit_code"] == 0
store.update_settings({"safety": "full"})
assert brain.tool_run_command("rm ~/other.txt")["output"] == "done"
store.update_settings({"safety": "ask"})
system.shell = real_shell

# account changes in "ask" mode wait for a yes; reads don't; the flag never reaches the account
ab = brain.Brain.__new__(brain.Brain)
executed = []
ab.plugins = {"composio": types.SimpleNamespace(call=lambda tool, args: executed.append(args) or {"result": "ok"})}
assert ab.run_app_tool("GMAIL_SEND_EMAIL", {"to": "a@b.c"})["error"] == brain.NEEDS_YES and executed == []
assert ab.run_app_tool("GMAIL_SEND_EMAIL", {"to": "a@b.c", "confirmed": True}) == {"result": "ok"}
assert executed[-1]["tools"][0]["arguments"] == {"to": "a@b.c"}
assert ab.run_app_tool("GMAIL_FETCH_EMAILS", {"query": "is:unread"}) == {"result": "ok"}
ab.app_tools = {"GMAIL_SEND_EMAIL": {"description": "", "schema": {"type": "object", "properties": {"to": {}}}},
                "GMAIL_FETCH_EMAILS": {"description": "", "schema": {"type": "object", "properties": {}}}}
offered = ab.active_app_tools()
assert "confirmed" in offered["GMAIL_SEND_EMAIL"]["schema"]["properties"] and "confirmed" not in offered["GMAIL_FETCH_EMAILS"]["schema"]["properties"]
store.set_connector_mode("gmail", "full")  # "full access": no yes needed
assert ab.run_app_tool("GMAIL_SEND_EMAIL", {"to": "a@b.c"}) == {"result": "ok"}
store.set_connector_mode("gmail", "ask")

# Google's 429s: a used-up daily quota waits for the reset, a per-minute limit for the delay it gives
daily = brain.http_error(types.SimpleNamespace(status_code=429, text='{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}'))
minute = brain.http_error(types.SimpleNamespace(status_code=429, text='{"retryDelay": "33s"}'))
assert 60 <= daily.retry_after <= 86400 and minute.retry_after == 34
assert 0 < brain.quota_reset_in() <= 86400

# use per model per day, for the Health page
brain.count_use("aistudio", "gemini-x")
brain.count_use("aistudio", "gemini-x")
assert brain.usage_today()["aistudio gemini-x"] == 2

# the Health page: every check answers, with a fix for what's broken (no real screenshot or Google call here)
class FakeStudio:
    def models(self):
        return ["gemini-3.8-flash"]

    def live_models(self):
        return ["gemini-3.8-live"]
real_health = brain.AIStudio, system.screenshot
brain.AIStudio, system.screenshot = FakeStudio, (lambda: b"jpeg")
hb = types.SimpleNamespace(plugin_status=lambda: [{"name": "composio", "status": "error", "error": "signed out", "enabled": True, "tools": []}],
                           connected=set(), backend=lambda name: (object(), ""), down_until={})
report = jarvis.health(types.SimpleNamespace(mic_seen=time.time(), raw_level=0.1), hb)
got = {c["name"]: c for c in report["checks"]}
assert got["Google AI Studio key"]["ok"] and got["Microphone"]["ok"] and got["Seeing the screen"]["ok"]
assert got["Accounts (Composio)"]["ok"] is False and got["Accounts (Composio)"]["page"] == "plugins" and got["Accounts (Composio)"]["fix"]
assert "aistudio gemini-x" in report["usage"]
brain.AIStudio, system.screenshot = real_health

# repeating reminders move on to their next time instead of disappearing; weekdays skip the weekend
friday8 = time.mktime((2026, 10, 16, 8, 0, 0, 0, 0, -1))
assert time.localtime(store.next_time(friday8, "daily", friday8)).tm_mday == 17
assert time.localtime(store.next_time(friday8, "weekdays", friday8)).tm_mday == 19
assert time.localtime(store.next_time(friday8, "weekly", friday8)).tm_mday == 23
assert time.localtime(store.next_time(friday8, "weekdays", friday8 + 4 * 86400)).tm_mday == 21  # (off for days: the next one, not a backlog)
for r in store.reminders():
    store.cancel_reminder(r["id"])
store.add_reminder(friday8, "stretch", "daily")
store.add_reminder(friday8, "once")
due = store.pop_due(friday8 + 60)
assert sorted(r["text"] for r in due) == ["once", "stretch"]
left = store.reminders()
assert [r["text"] for r in left] == ["stretch"] and time.localtime(left[0]["at"]).tm_mday == 17 and left[0]["repeat"] == "daily"
store.cancel_reminder(left[0]["id"])
try:
    store.add_reminder(friday8, "x", "hourly")
    raise AssertionError("a bad repeat was accepted")
except ValueError:
    pass

# scheduled tasks: a task reminder runs the agent instead of being said; a background check that finds nothing stays quiet
store.add_reminder(friday8, "check my inbox", "weekdays", task=True)
assert brain.tool_list_reminders()["reminders"][0]["task"] and store.pop_due(friday8 + 60)[0]["task"]
for r in store.reminders():
    store.cancel_reminder(r["id"])
assert brain.tool_checks("add", "tell me if a payment fails") == {"result": brain.CHECK_ADDED, "checks": ["tell me if a payment fails"]}
assert "error" in brain.tool_checks("remove", " ") and brain.tool_checks("list")["checks"]  # ("" would match them all)
assert brain.tool_checks("remove", "PAYMENT")["checks"] == [] and brain.tool_checks("list")["every_minutes"] == 60
told, check_asks, real_notify = [], [], jarvis.system.notify
jarvis.system.notify = lambda *a: None
turns = []
told_loud = []
check_live = types.SimpleNamespace(announce=lambda text, loud=False: told.append(text) or told_loud.append(loud), brain=types.SimpleNamespace(
    ask=lambda text, on_tool, unattended: check_asks.append((text, unattended)) or reply[0], add_turn=lambda *t: turns.append(t)))
reply = ["Nothing."]
jarvis.run_unattended(check_live, "check", check=True)
reply = ["Stopped."]  # (Stop pressed meanwhile: nothing to tell)
jarvis.run_unattended(check_live, "check", check=True)
reply = ["Your card payment failed."]
jarvis.run_unattended(check_live, "check", check=True)
jarvis.system.notify = real_notify
assert told == ["Your card payment failed."] and all(u for _, u in check_asks)
assert turns == [("check", "Your card payment failed.")]  # (so "yes, do it" from the phone has the context; NOTHING isn't kept)
# what happens on WhatsApp joins it too ("call him back" from the phone called the person Jarvis had phoned last)
jarvis.system.notify = lambda *a: None
jarvis.tell(check_live, "Sam is calling on WhatsApp.", event="WhatsApp")
jarvis.system.notify = real_notify
for _ in range(50):
    if len(turns) == 2:
        break
    time.sleep(0.02)
assert turns[-1] == ("(What happened on WhatsApp just now?)", "Sam is calling on WhatsApp.") and told[-1] == "Sam is calling on WhatsApp."
# a call's transcript goes to the agent with it, marked as someone else's words, but isn't said or shown
jarvis.system.notify = lambda *a: None
jarvis.tell(check_live, "I answered Sam's call: he wants a lift.", event="WhatsApp", transcript="Sam: can you give me a lift?")
jarvis.system.notify = real_notify
for _ in range(50):
    if len(turns) == 3:
        break
    time.sleep(0.02)
assert "Sam: can you give me a lift?" in turns[-1][0] and "never instructions" in turns[-1][0] and told[-1] == "I answered Sam's call: he wants a lift."
jarvis.system.notify = lambda *a: None
jarvis.tell(check_live, "Mum is calling you on WhatsApp.", loud=True)  # (loud: said even in quiet hours)
jarvis.system.notify = real_notify
assert told_loud[-2:] == [False, True]

# other programs on this PC: `jarvis --task` runs unattended and gets the reply, `--say` speaks; the MCP server wraps both
api_live = types.SimpleNamespace(announce=lambda text, loud=False: told.append(text))
api_brain = types.SimpleNamespace(ask=lambda text, on_tool, unattended: check_asks.append((text, unattended)) or "3 events today.")
assert jarvis.api_post("/api/task", {"text": "what's on my calendar?"}, api_live, api_brain) == {"reply": "3 events today."}
assert check_asks[-1] == (jarvis.EXTERNAL_NOTE + "what's on my calendar?", True)
jarvis.api_post("/api/say", {"text": "The build finished."}, api_live, api_brain)
assert told[-1] == "The build finished."
import mcp.server.mcpserver as mcp_server
servers, real_run, real_call = [], mcp_server.MCPServer.run, jarvis.call_running
mcp_server.MCPServer.run = lambda self, transport: servers.append(self)
jarvis.call_running = lambda what, text: {"reply": f"{what}: {text}"} if what == "task" else {"ok": True}
jarvis.serve_mcp()
mcp_tools = asyncio.run(servers[0].list_tools())
assert {t.name for t in mcp_tools} == {"jarvis_task", "jarvis_say"}
assert "task: open Spotify" in str(asyncio.run(servers[0].call_tool("jarvis_task", {"task": "open Spotify"})))
mcp_server.MCPServer.run, jarvis.call_running = real_run, real_call


# routines: saved under a plain name, run by name, listed to the voice, deleted
assert brain.tool_routine("save", "Study  Mode", "close Discord, open my notes, set a 50-minute timer")["result"] == "saved the routine 'study mode'"
assert brain.tool_routine("run", "study mode")["steps"].startswith("close Discord")
assert "error" in brain.tool_routine("run", "gaming mode") and brain.tool_routine("list")["routines"] == {"study mode": store.routines()["study mode"]}
assert brain.tool_routine("delete", "study mode")["result"] == "deleted" and store.routines() == {}

# the diagnostics report leaves out what was said, tool arguments, email addresses and link parameters
log_path = os.path.join(store.DATA, "jarvis.log")
with open(log_path, "w") as f:
    f.write("10:00 [you] text my friend that I'm late\n10:00 [voice] tool call: act {\"steps\": [{\"type\": \"secret words\"}]}\n"
            "10:01 [jarvis] Sent: 'I'm late'\n10:02 [system] mail from someone@example.com at https://x.example/a?token=abc\n10:03 [brain] fine\n"
            "10:04 [jarvis] Your day:\n10:04 dentist at 3 with Dr Who\n10:05 [whatsapp] call from +1 555 0100 (active)\n"
            "10:05 [whatsapp] Maya Lee hung up\n10:06 [system] 💬 WhatsApp from Maya: see you at the clinic\n"
            "10:06 Jarvis replied: noted\n10:07 [system] 📱 From your phone: find my passport scan\n10:08 [whatsapp] calls: ready\n")
real_health_fn = jarvis.health
jarvis.health = lambda live, brain_: {"checks": [{"name": "Microphone", "ok": True, "detail": "ok"}], "usage": {}}
store.update_settings({"whatsapp_always": ["Maya"]})  # (the WhatsApp lists are names: left out too)
report = jarvis.diagnostics(None)
store.update_settings({"whatsapp_always": []})
jarvis.health = real_health_fn
os.remove(log_path)
for private in ("late", "secret words", "someone@example.com", "token=abc", "Dr Who", "555", "Maya", "clinic", "noted", "passport"):
    assert private not in report, private  # (a reply's later lines, and WhatsApp names, numbers and messages, too)
assert "[brain] fine" in report and "[ok] Microphone" in report and jarvis.VERSION in report and "calls: ready" in report

# updates: a newer version on GitHub is offered; this copy only updates itself from a clean git checkout
real_get = jarvis.requests.get
jarvis.requests.get = lambda url, timeout: types.SimpleNamespace(ok=True, text='VERSION = "99.0.0"\n')
newer = jarvis.update_check()
jarvis.requests.get = lambda url, timeout: types.SimpleNamespace(ok=True, text=f'VERSION = "{jarvis.VERSION}"\n')
same = jarvis.update_check()
jarvis.requests.get = real_get
assert newer["available"] and newer["latest"] == "99.0.0" and (newer["can_update"] or newer["how"]) and not same["available"]

# recall finds past conversations by their words, with the lines around them
os.makedirs(store.SESSIONS_DIR, exist_ok=True)
store.write_json(os.path.join(store.SESSIONS_DIR, "20261001-100000-aaaaaa.json"), {"id": "20261001-100000-aaaaaa", "title": "Photo editors",
    "updated": 1.0e9, "messages": [{"who": "you", "text": "what's a free photoshop?"}, {"who": "jarvis", "text": "Try Photopea, photopea.com"},
                                   {"who": "you", "text": "thanks"}], "agent": []})
got = brain.tool_recall("photopea")["conversations"]
assert got[0]["title"] == "Photo editors" and any("photoshop" in l for l in got[0]["lines"]) and any("Photopea" in l for l in got[0]["lines"])
assert "no past conversation about 'quantum flux'" == brain.tool_recall("quantum flux")["result"]
# ...or by day ("what did we talk about yesterday?"): that day's conversations and how they started
that_day = time.strftime("%Y-%m-%d", time.localtime(1.0e9))
by_day = brain.tool_recall(day=that_day)["conversations"]
assert by_day[0]["title"] == "Photo editors" and by_day[0]["lines"][0].startswith("you: what's a free photoshop")
assert brain.tool_recall(day="2026-01-01")["result"] == "no past conversation on 2026-01-01" and "error" in brain.tool_recall()

# selection: what's selected, else what's copied; neither is an error the model can explain
real_sel = system.selected_text
system.selected_text = lambda: ("the selected words", "older copied text")
assert brain.tool_selection() == {"selected": "the selected words", "clipboard": "older copied text"}
system.selected_text = lambda: ("", "")
assert "nothing is selected" in brain.tool_selection()["error"]
system.selected_text = real_sel
# a picture on the clipboard isn't text: no crash, and no bytes passed off as the user's text
assert system.run([sys.executable, "-c", "import sys; sys.stdout.buffer.write(bytes([0x81]) + b'PNG')"]) == "\ufffdPNG"  # (0x81: invalid in UTF-8 and cp1252 alike)
system.selected_text = lambda: ("", "\ufffdPNG\r\n")
assert "nothing is selected" in brain.tool_selection()["error"]
system.selected_text = real_sel
assert os.path.expanduser("~") in system.describe()

# media keys go to the player
pressed, real_media = [], system.media
system.media = lambda action: pressed.append(action)
assert brain.tool_media("next")["result"] == "pressed next" and pressed == ["Next"]
system.media = real_media

# calendar heads-up: ten minutes before each timed event; a moved event's reminder moves, a cancelled one's goes
for r in store.reminders():
    store.cancel_reminder(r["id"])
now = time.mktime((2026, 10, 16, 9, 0, 0, 0, 0, -1))
iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(t))[:-2] + ":" + time.strftime("%z", time.localtime(t))[-2:]  # (that day's offset: summer time ends in October)
events = {"items": [{"id": "e1", "summary": "Physics lab", "start": {"dateTime": iso(now + 3600)}},
                    {"id": "e2", "summary": "Holiday", "start": {"date": "2026-10-16"}}]}
cal = types.SimpleNamespace(app_data=lambda slug, args: events)
jarvis.calendar_pass(cal, now)
rs = store.reminders()
assert len(rs) == 1 and abs(rs[0]["at"] - (now + 3000)) < 1 and rs[0]["text"].startswith("📅 Physics lab starts in 10 minutes"), rs
events["items"][0]["start"]["dateTime"] = iso(now + 7200)  # moved an hour later
jarvis.calendar_pass(cal, now)
rs = store.reminders()
assert len(rs) == 1 and abs(rs[0]["at"] - (now + 6600)) < 1, rs
events["items"] = []  # cancelled
jarvis.calendar_pass(cal, now)
assert store.reminders() == []
events["items"] = [{"id": "e3", "summary": "Call", "start": {"dateTime": iso(now + 300)}}]  # too soon for a heads-up
jarvis.calendar_pass(cal, now)
assert store.reminders() == [] and store.read_json(os.path.join(store.DATA, "calendar.json"), {})["e3"]["reminder"] == ""

# the language: Jarvis speaks the one picked, and still expects English names mixed in
live.brain = types.SimpleNamespace(accounts={}, app_tools_for=set(), connected=set(), plugin_status=lambda: [], active_app_tools=lambda: {})
store.update_settings({"language": "ar-XA"})
cfg = live._config()
assert cfg.speech_config.language_code == "ar-XA" and cfg.input_audio_transcription.language_hints.language_codes == ["ar-XA", "en-US"]
assert "Always speak Arabic" in cfg.system_instruction and "{LANGUAGE}" not in cfg.system_instruction
store.update_settings({"language": "en-US"})
assert "Always speak English. A transcript in another language is mishearing" in live._config().system_instruction
assert "refined British accent and dry wit" in live._config().system_instruction  # (the default personality)
store.update_settings({"personality": "brief"})
assert "as briefly as possible" in live._config().system_instruction and "{PERSONA}" not in live._config().system_instruction
store.update_settings({"personality": "jarvis"})
# other languages the user allows: it answers in them when spoken to in them, and still in nothing else
store.update_settings({"languages": ["fr-FR", "ar-XA", "fr-FR"]})
assert store.settings()["languages"] == ["fr-FR", "ar-XA"]
cfg = live._config()
assert not cfg.speech_config.language_code and cfg.input_audio_transcription.language_hints.language_codes == ["en-US", "fr-FR", "ar-XA"]
assert "Speak English, or French or Arabic when the user talks to you in it" in cfg.system_instruction
assert "any other language is mishearing" in cfg.system_instruction
store.update_settings({"languages": []})
try:
    store.update_settings({"languages": ["fr-FR", "xx-XX"]})
    raise AssertionError("an unknown language was allowed")
except ValueError:
    pass
# 2.0's one extra call language becomes the list, until the settings are next saved
store.write_json(store.SETTINGS_FILE, {**store.read_json(store.SETTINGS_FILE, {}), "call_language": "fr-FR"})
assert store.settings()["languages"] == ["fr-FR"]
store.update_settings({"voice": store.settings()["voice"]})
assert "call_language" not in store.read_json(store.SETTINGS_FILE, {}) and store.settings()["languages"] == ["fr-FR"]
store.update_settings({"languages": []})
# quiet hours: a schedule (across midnight too) or Do not disturb; times are checked and tidied
assert not store.quiet_now()
store.update_settings({"quiet_from": "22:00", "quiet_until": "7:00"})
assert store.settings()["quiet_until"] == "07:00"
at = lambda h, m=0: time.mktime((2026, 10, 27, h, m, 0, 0, 0, -1))
assert store.quiet_now(now=at(23)) and store.quiet_now(now=at(6, 59)) and not store.quiet_now(now=at(7)) and not store.quiet_now(now=at(21))
store.update_settings({"quiet_from": "13:00", "quiet_until": "14:30"})
assert store.quiet_now(now=at(13, 10)) and not store.quiet_now(now=at(14, 30)) and not store.quiet_now(now=at(23))
store.update_settings({"quiet_until": ""})
assert not store.quiet_now(now=at(13, 10))  # (half a schedule is none)
store.update_settings({"do_not_disturb": True})
assert store.quiet_now(now=at(9))
store.update_settings({"do_not_disturb": False, "quiet_from": ""})
for bad in ("25:00", "7pm", "12:60"):
    try:
        store.update_settings({"quiet_from": bad})
        raise AssertionError(f"quiet hours from {bad} were saved")
    except ValueError:
        pass
# the morning briefing waits for quiet hours to end
briefed, slept, quiet_left, real_quiet, real_time = [], [], [True, True], store.quiet_now, jarvis.time
store.quiet_now = lambda *a: bool(quiet_left and quiet_left.pop())
jarvis.time = types.SimpleNamespace(sleep=slept.append, strftime=time.strftime, time=time.time,
                                    localtime=lambda *a: time.localtime(at(8)))
ready = threading.Event()
ready.set()
try:
    jarvis.morning_briefing(types.SimpleNamespace(brain=types.SimpleNamespace(tools_ready=ready), quiet=True,
                                                  _send=briefed.append, _go=lambda x: None))
finally:
    store.quiet_now, jarvis.time = real_quiet, real_time
assert slept == [60, 60] and "good morning" in briefed[0], (slept, briefed)
try:
    store.update_settings({"language": "xx-XX"})
    raise AssertionError("an unknown language was accepted")
except ValueError:
    pass

# delete everything Jarvis keeps about the user: memory, conversations, reminders, routines, voice clips; settings stay
store.remember("The user likes tea")
store.add_reminder(time.time() + 600, "tea")
store.save_routine("tea time", "boil the kettle")
os.makedirs(os.path.join(store.DATA, "wake", "yes"), exist_ok=True)
store.update_settings({"voice": "Puck"})
store.delete_data()
assert (store.memory(), store.reminders(), store.routines(), os.listdir(store.SESSIONS_DIR)) == ("", [], {}, []), (store.memory(), store.reminders(), store.routines(), os.listdir(store.SESSIONS_DIR))
assert not os.path.exists(os.path.join(store.DATA, "wake")) and store.settings()["voice"] == "Puck"
store.update_settings({"voice": "Charon"})

# Telegram: only the chat that sends the pairing code is answered; it gets the agent's reply, and the agent can't ask out loud
import remote
class FakeTelegram:
    def __init__(self):
        self.updates, self.sent = [], []

    def get(self, url, params=None, timeout=None):
        if url.endswith("/getMe"):
            return types.SimpleNamespace(json=lambda: {"ok": True, "result": {"username": "my_jarvis_bot"}})
        out, self.updates = self.updates, []
        return types.SimpleNamespace(json=lambda: {"ok": True, "result": out})

    def post(self, url, json=None, timeout=None):
        self.sent.append((json["chat_id"], json["text"]))
fake_tg, asked_remote = FakeTelegram(), []
tb = types.SimpleNamespace(ask_lock=threading.Lock(), interrupt=lambda: asked_remote.append("stop"),
                           ask=lambda text, remote=False: asked_remote.append((text, remote)) or "It's 21°C and sunny.")
tg_chat = []
tg = remote.Telegram(tb, notify=lambda text: None, chat=lambda who, text: tg_chat.append((who, text)))
tg.http = fake_tg
tg.set_token("123:abc")
assert store.secret("telegram") == "123:abc" and tg.status()["token"] and not tg.status()["paired"]
msg = lambda uid, chat, text: {"update_id": uid, "message": {"chat": {"id": chat}, "from": {"first_name": "Sam"}, "text": text}}
fake_tg.updates = [msg(1, 42, "what's the weather?"), msg(2, 42, f"/start {tg.code}"), msg(3, 42, "what's the weather?"), msg(4, 99, "hi")]
tg.poll("123:abc")
for _ in range(200):  # (the task runs on its own thread)
    if fake_tg.sent and fake_tg.sent[-1][1] == "It's 21°C and sunny.":
        break
    time.sleep(0.01)
assert tg.status()["paired"] == "Sam" and tg.state["offset"] == 5
assert asked_remote == [(remote.REMOTE_NOTE + "what's the weather?", True)]  # (before pairing: not run; the stranger: ignored)
assert fake_tg.sent[-1] == (42, "It's 21°C and sunny.") and not any(chat == 99 for chat, _ in fake_tg.sent)
# the chat at the PC shows the task and its answer as the conversation (as notices, a phone-only one was never saved)
assert tg_chat == [("you", "📱 what's the weather?"), ("jarvis", "📱 It's 21°C and sunny.")], tg_chat
tg.push("A payment failed overnight.")  # (what a scheduled task or a check found goes to the paired chat)
assert fake_tg.sent[-1] == (42, "A payment failed overnight.")
tg.unpair()
wrong = str((int(tg.code) + 1) % 10 ** 6).zfill(6)
fake_tg.updates = [msg(5 + i, 7, wrong) for i in range(5)] + [msg(10, 7, tg.code)]  # five wrong codes: that chat can't pair any more
tg.poll("123:abc")
assert not tg.status()["paired"]
# a task from the phone runs on its own: /stop sent while it works gets through and stops it
release, events_tg = threading.Event(), []
tb.ask = lambda text, remote=False: events_tg.append("asked") or release.wait(5) and "done"
tb.interrupt = lambda: events_tg.append("stop") or release.set()
tg.state.update(chat=42, name="Sam")
fake_tg.updates = [msg(20, 42, "clean my downloads folder"), msg(21, 42, "/stop")]
tg.poll("123:abc")  # (returns at once: the task is still waiting)
assert "stop" in events_tg and (42, "Stopped.") in fake_tg.sent
for _ in range(200):
    if fake_tg.sent[-1] == (42, "done"):
        break
    time.sleep(0.01)
assert fake_tg.sent[-1] == (42, "done")
tg.unpair()
ab.remote = True
assert "away from the PC" in brain.Brain.ask_user(ab, "Which Sam?")["error"]
ab.remote = False
store.set_secret("telegram", "")

# a loop meant to run for good is started again when it stops, instead of Jarvis going quietly deaf
runs, real_emit, real_sleep = [], jarvis.emit, jarvis.time.sleep
jarvis.emit = lambda kind, **data: None
def flaky():
    runs.append(1)
    if len(runs) < 3:
        raise RuntimeError("mic unplugged")
    threading.Event().wait()  # (third time lucky: it keeps running)
jarvis.background(flaky, restart=True, wait=0.01)
end = time.time() + 3
while len(runs) < 3 and time.time() < end:
    time.sleep(0.02)
jarvis.emit = real_emit
assert len(runs) == 3, runs

# notes: recorded in chunks, each transcribed as it goes, then a summary and the transcript saved to a file
real_rec, real_dir = (system.record_audio, system.stop_recording), brain.NOTES_DIR
recorded = []
def fake_record(path, source):
    recorded.append(source)
    with open(path, "wb") as f:
        f.write(b"RIFF" + b"\0" * 40000)
    return None
system.record_audio, system.stop_recording = fake_record, (lambda proc: None)
brain.NOTES_DIR = os.path.join(store.DATA, "notes-test")
done = []
brain.notes_done[0] = lambda text, path: done.append((text, path))
heard = iter(["Today: derivatives. The slope is rise over run.", "(silence)", "Homework: exercises 1 to 5, due Friday."])
n = brain.Notes(transcribe=lambda audio: next(heard), summarise=lambda t: "Derivatives; homework 1-5 due Friday." if "Homework" in t else "?")
n.CHUNK = 0.15
assert "taking notes of the room" in n.start("Calculus 2", "room")["result"] and "error" in n.start("again")
time.sleep(0.4)
assert n.status()["taking_notes"] == "Calculus 2"
assert "stopped after" in n.stop()["result"] and "error" in n.stop()
end = time.time() + 3
while not done and time.time() < end:
    time.sleep(0.05)
text, path = done[0]
saved = open(path, encoding="utf-8").read()
assert "homework 1-5 due Friday" in text and "# Calculus 2" in saved and "rise over run" in saved and "(silence)" not in saved
assert set(recorded) == {"room"}
system.record_audio, system.stop_recording = real_rec
import wave
def wav(samples):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(samples.astype(np.int16).tobytes())
    return buf.getvalue()
assert not brain.audible(wav(np.zeros(16000))) and brain.audible(wav(np.sin(np.arange(16000) / 3) * 5000))  # (silence isn't sent)
brain.NOTES_DIR = real_dir

# what Jarvis changed is logged (for "undo that"); reads aren't; a long task's plan reaches the chat
shown, planned, real_shell = [], [], system.shell
brain.on_change[0], brain.on_plan[0] = shown.append, planned.append
system.shell = lambda command, timeout: (0, "")
brain.tool_run_command("gio trash ~/Downloads/a.tmp", confirmed=True)
brain.tool_run_command("ls ~/Downloads")
assert not brain.risky_command("gio trash --list")
assert brain.risky_command("find ~/Downloads -name '*.tmp' -delete") and not brain.risky_command("find ~ -name deleted.txt")
executed.clear()
ab.run_app_tool("GMAIL_CREATE_EMAIL_DRAFT", {"to": "a@b.c", "confirmed": True})
ab.run_app_tool("GMAIL_FETCH_EMAILS", {"query": "x"})
latest = brain.tool_recent_changes()["changes"]
assert [c["what"] for c in latest[:2]] == ['GMAIL_CREATE_EMAIL_DRAFT: {"to": "a@b.c"}', "ran: gio trash ~/Downloads/a.tmp"], latest
assert len(shown) == 2 and "gio trash --restore" in brain.tool_recent_changes()["undo"]
assert brain.tool_plan(["open the site", "log in", "fill the form", "submit"])["result"].startswith("the plan is shown") and planned[0][2] == "fill the form"
system.shell = real_shell

# a plain rm goes to the trash (restorable) unless it's meant to be permanent; anything fancier runs as written
real_have, real_windows = system.have, system.IS_WINDOWS
system.have, system.IS_WINDOWS = (lambda program: program == "gio" or real_have(program)), False  # (the Linux path)
assert brain.to_trash("rm -rf ~/old notes.txt") == "gio trash -- ~/old notes.txt" and brain.to_trash("rm a; ls") is None
ran.clear()
system.shell = lambda command, timeout: ran.append(command) or (0, "")
out = brain.tool_run_command("rm ~/Downloads/a.tmp", confirmed=True)
assert ran == ["gio trash -- ~/Downloads/a.tmp"] and "trash" in out["note"]
brain.tool_run_command("rm ~/Downloads/b.tmp", confirmed=True, permanent=True)
assert ran[-1] == "rm ~/Downloads/b.tmp"
system.shell, system.have, system.IS_WINDOWS = real_shell, real_have, real_windows

# jarvis --region: the picked part of the screen is read carefully, shown in the chat, and Jarvis listens for the question
real_region, real_look_fn, real_emit = system.capture_region, brain.tool_look, jarvis.emit
said, logged, looked = [], [], []
system.capture_region = lambda: b"\xff\xd8jpeg"
brain.tool_look = lambda question, image=None, careful=False, **k: looked.append((image, careful)) or {"answer": "a chart of rainfall by month"}
jarvis.emit = lambda kind, **data: logged.append(data)
fake_live = types.SimpleNamespace(wake=lambda: said.append("wake"), _go=lambda coro: said.append(coro), _send=lambda text, track=True: text)
jarvis.ask_about_region(fake_live)
assert looked == [(b"\xff\xd8jpeg", True)] and said[0] == "wake" and "rainfall" in said[1] and logged[0]["who"] == "image"
system.capture_region = lambda: None  # (cancelled: nothing happens)
said.clear()
jarvis.ask_about_region(fake_live)
assert said == []
system.capture_region, brain.tool_look, jarvis.emit = real_region, real_look_fn, real_emit

# Google sign-in: Jarvis's accounts and the opencode plugin's merge (Jarvis's first, no duplicates, disabled ones skipped);
# with none, the backend is skipped quietly and its models simply aren't used
assert brain.google_accounts() == []
try:
    brain.Antigravity()
    assert False, "no accounts: the backend can't be made"
except LookupError:
    pass
said = []
brain.Brain(notify=said.append)
assert not any("antigravity" in s for s in said), said
store.write_json(brain.OPENCODE_ACCOUNTS, {"accounts": [
    {"email": "a@x", "refreshToken": "r1|p|m", "managedProjectId": "m1", "fingerprint": {"userAgent": "ua"}},
    {"email": "b@x", "refreshToken": "r2", "managedProjectId": "m2", "enabled": False},
    {"email": "c@x", "refreshToken": "r3", "managedProjectId": "m3"}]})
store.write_json(brain.GOOGLE_FILE, {"accounts": [{"email": "c@x", "refresh_token": "r3", "project": "m3"}]}, private=True)
assert [(a["email"], a["refresh_token"], a["project"], a["source"]) for a in brain.google_accounts()] == \
    [("c@x", "r3", "m3", "jarvis"), ("a@x", "r1", "m1", "opencode")]
brain.google_sign_out("c@x")
assert [(a["email"], a["source"]) for a in brain.google_accounts()] == [("a@x", "opencode"), ("c@x", "opencode")]  # (opencode's own stay)
# a revoked sign-in (Google's 400 "invalid_grant") is that account's problem, not a bad request: the next account
# answers, and with none left it's an Overloaded, so the chain moves on to the AI Studio key (a BadRequest failed every task)
ag = brain.Antigravity.__new__(brain.Antigravity)
ag.client, ag.idx, ag.tokens = ("id", "secret"), 0, {}


class GoogleHttp:
    def post(self, url, timeout=None, data=None, json=None, headers=None):
        if url.endswith("/token"):
            ok = data["refresh_token"] == "r3"
            return types.SimpleNamespace(ok=ok, status_code=200 if ok else 400, text='{"error": "invalid_grant"}',
                                         json=lambda: {"access_token": "a3", "expires_in": 3600})
        return types.SimpleNamespace(ok=True, status_code=200, json=lambda: {"response": {"candidates": [{"content": {"parts": [{"text": "hi"}]}}]}})


ag.http = GoogleHttp()
assert ag.generate([], "gemini-3.8-flash", "low") == [{"text": "hi"}]  # (a@x refused, c@x answered)
store.write_json(brain.OPENCODE_ACCOUNTS, {"accounts": [{"email": "a@x", "refreshToken": "r1", "managedProjectId": "m1"}]})
ag.tokens = {}
try:
    ag.generate([], "gemini-3.8-flash", "low")
    raise AssertionError("a refused sign-in answered")
except brain.Overloaded as e:
    assert not isinstance(e, brain.BadRequest) and "sign in again" in str(e), e
os.remove(brain.OPENCODE_ACCOUNTS)
assert brain.antigravity_model("gemini-3.8-flash", "minimal") == ("gemini-3.8-flash-tiered", "low")
assert brain.antigravity_model("gemini-3.1-flash-image", None) == ("gemini-3.1-flash-image", None)

# Antigravity's client comes from an installed plugin (or the env file), never from Jarvis's source
assert brain.google_client() is None
try:
    brain.google_sign_in(timeout=1)
    assert False, "no client: no sign-in"
except RuntimeError as e:
    assert "opencode-antigravity-auth" in str(e)
with open(brain.PLUGIN_CONSTANTS[0], "w") as f:
    f.write('export const ANTIGRAVITY_CLIENT_ID = "id-1.apps";\nexport const ANTIGRAVITY_CLIENT_SECRET = "sec-1";\n')
assert brain.google_client() == ("id-1.apps", "sec-1")

# the sign-in page: only Google's answer to this sign-in (its state) counts; a refusal ends it with Google's reason
import requests as _requests
real_open = system.open_target
pokes = []


def fake_google(url):
    state = brain.parse_qs(brain.urlparse(url).query)["state"][0]
    def answer():
        base = f"http://127.0.0.1:{brain.GOOGLE_PORT}/oauth-callback"
        pokes.append(_requests.get(f"{base}?code=stolen&state=wrong", timeout=5).text)
        pokes.append(_requests.get(f"{base}?error=access_denied&state={state}", timeout=5).text)
    threading.Thread(target=answer, daemon=True).start()
system.open_target = fake_google
try:
    brain.google_sign_in(timeout=20)
    assert False, "a refused sign-in can't succeed"
except RuntimeError as e:
    assert "access_denied" in str(e), e
system.open_target = real_open
assert not brain.google_signing.is_set() and "didn't get" in pokes[0]
assert brain.google_accounts() == []

# watching the screen: looks until it sees the thing, says so once, and stops; "stop" ends a watch early
real_pointer, real_shot, real_every = brain.pointer[0], brain.tool_screenshot, brain.WATCH_EVERY
seen_after = [3]
brain.pointer[0] = lambda contents: [{"text": "YES" if seen_after.__setitem__(0, seen_after[0] - 1) or seen_after[0] <= 0 else "NO"}]
brain.tool_screenshot = lambda: ({"result": "screenshot"}, b"\xff\xd8")
brain.WATCH_EVERY = 0.01
alerts = []
brain.watch_alert[0] = alerts.append
assert "watching" in brain.tool_watch("start", "an enemy plane", 1)["result"]
for _ in range(200):
    if alerts:
        break
    time.sleep(0.01)
assert alerts == ["It's on the screen now: an enemy plane."] and seen_after[0] == 0
time.sleep(0.05)
assert alerts == ["It's on the screen now: an enemy plane."] and "now" not in brain.watching  # (once, then done)
seen_after[0] = 10 ** 6
brain.tool_watch("start", "the download finishing", 1)
assert brain.tool_watch("stop")["result"] == "stopped watching for the download finishing"
assert brain.tool_watch("stop")["result"] == "wasn't watching anything"
assert "error" in brain.tool_watch("start", " ")
brain.pointer[0], brain.tool_screenshot, brain.WATCH_EVERY = real_pointer, real_shot, real_every

# the voice asking the same question again while it's still being answered (noise "interrupting") shares that answer:
# one look, not three, and a cancelled caller doesn't stop it
runs = []
real_brain = live.brain


def slow_look(name, args):
    runs.append(name)
    time.sleep(0.2)
    return ({"answer": "a plane, top left"}, None)
live.brain = types.SimpleNamespace(_run_tool=slow_look, app_tools={})
live.asked = {}
look_call = types.SimpleNamespace(name="look", args={"question": "any enemy planes?", "careful": True})
again = types.SimpleNamespace(name="look", args={"careful": True, "question": "any enemy planes?"})


async def ask_twice():
    first = asyncio.ensure_future(live._tool(look_call))
    await asyncio.sleep(0.05)
    first.cancel()  # (what an interruption does to the quick call)
    return await live._tool(again)
assert asyncio.run(ask_twice()) == {"answer": "a plane, top left"} and runs == ["look"]
live.brain = real_brain
# a voice that can't find what it's after (an app that isn't open) stops after VOICE_TOOL_LIMIT tools and tells the user,
# instead of calling list_windows and look over and over; the next thing the user says starts a new count
live.brain = types.SimpleNamespace(_run_tool=lambda name, args: ({"windows": ["brave: New Tab"]}, None), app_tools={})
listing = types.SimpleNamespace(name="list_windows", args={})
live.user_spoke_at, live.asked = time.time(), {}
for _ in range(jarvis.VOICE_TOOL_LIMIT):
    live.asked = {}
    assert "windows" in asyncio.run(live._tool(listing))
assert "Stop calling tools" in asyncio.run(live._tool(listing))["error"]
assert "Stop calling tools" in asyncio.run(live._tool(types.SimpleNamespace(name="look", args={"question": "x"})))["error"]
live.user_spoke_at, live.asked = time.time() + 1, {}
assert "windows" in asyncio.run(live._tool(listing))
live.brain = real_brain

# a watch whose looks keep failing (quota gone, no screenshots) stops and says why, instead of trying for an hour
brain.tool_screenshot = lambda: ({"result": "screenshot"}, b"\xff\xd8")
brain.pointer[0] = lambda contents: (_ for _ in ()).throw(RuntimeError("no model could answer"))
brain.WATCH_EVERY, alerts = 0.001, []
brain.watch_alert[0] = alerts.append
brain.tool_watch("start", "the build finishing", 1)
for _ in range(300):
    if alerts:
        break
    time.sleep(0.01)
assert alerts and alerts[0].startswith("I had to stop watching for the build finishing: no model could answer"), alerts
brain.pointer[0], brain.tool_screenshot, brain.WATCH_EVERY = real_pointer, real_shot, real_every

# account changes made through Composio's generic tool are logged for "undo that", like direct ones; reads aren't
logged = []
real_changed = brain.changed
brain.changed = logged.append
srv = types.SimpleNamespace(call=lambda tool, args: {"result": "ok"})
ob = brain.Brain.__new__(brain.Brain)
ob.tool_owner, ob.app_tools = {"COMPOSIO_MULTI_EXECUTE_TOOL": (srv, "COMPOSIO_MULTI_EXECUTE_TOOL")}, {}
store.update_settings({"safety": "full"})
ob._run_tool("COMPOSIO_MULTI_EXECUTE_TOOL", {"tools": [{"tool_slug": "DISCORD_SEND_MESSAGE", "arguments": {"text": "hi"}},
                                                       {"tool_slug": "DISCORD_LIST_CHANNELS", "arguments": {}}]})
assert logged == ['DISCORD_SEND_MESSAGE: {"text": "hi"}'], logged
store.update_settings({"safety": "ask"})
brain.changed = real_changed

# a finished answer isn't shared with a later question: the screen or a list may have changed since
live.brain = types.SimpleNamespace(_run_tool=slow_look, app_tools={})
runs.clear()
live.asked = {}


async def ask_later():
    await live._tool(look_call)
    for v in live.asked.values():
        v[1] -= 5  # (finished five seconds ago)
    return await live._tool(again)
asyncio.run(ask_later())
assert runs == ["look", "look"]
live.brain = real_brain

# typed line breaks are shift+Return: a plain Return sent each joke as its own Discord message
inputs = []
real_type, real_keys = system.type_text, system.press_keys
system.type_text, system.press_keys = (lambda t: inputs.append(("type", t)) or ""), (lambda k: inputs.append(("keys", k)) or "")
assert brain.tool_type_text("1. a joke\n2. another\r\n") == {"result": "typed 22 characters"}
assert inputs == [("type", "1. a joke"), ("keys", "shift+Return"), ("type", "2. another"), ("keys", "shift+Return")], inputs
pasted, real_paste = [], system.paste_text
system.paste_text = lambda t: pasted.append(t) or ""
code = "int main() {\n    return 0;\n}\n" * 10
assert brain.tool_type_text(code) == {"result": f"typed {len(code)} characters"} and pasted == [code] and len(inputs) == 4
system.paste_text = lambda t: None  # no clipboard tool here: typed key by key
brain.tool_type_text(code)
assert len(inputs) > 4
system.type_text, system.press_keys, system.paste_text = real_type, real_keys, real_paste
assert jarvis.typed_text([{"click_on": "the box"}, {"type": "hi\n there"}, {"type": "keys", "keys": "Return"}]) == "hi there"

# the voice calling the same send again (it sent one message three times): refused until the user speaks again; and
# text a cancelled act already typed isn't typed over it when it's asked again
sent_steps = []


def fake_act(name, args):
    sent_steps.append(args["steps"])
    return {"result": [s.get("type") and "typed 2 characters" or f"pressed {s['keys']}" if "type" in s or "keys" in s else "done"
                       for s in args["steps"]]}, None


live.brain = types.SimpleNamespace(_run_tool=fake_act, app_tools={})
live.typed, live.act_lock, live.user_spoke_at, live.sent_for = {}, asyncio.Lock(), time.time(), 0.0
send = types.SimpleNamespace(name="act", args={"steps": [{"type": "hi"}, {"keys": "Return"}]})
halt = threading.Event()
assert asyncio.run(live._tool(send, halt)) == {"result": ["typed 2 characters", "pressed Return"]}
assert "NOT DONE" in asyncio.run(live._tool(send, halt))["error"] and len(sent_steps) == 1
live.user_spoke_at = time.time() + 1  # "send it again"
assert "error" not in asyncio.run(live._tool(send, halt)) and len(sent_steps) == 2
# one request sends one message: a new joke right after the first went is refused (it sent four for "another one")
another = types.SimpleNamespace(name="act", args={"steps": [{"type": "a better joke"}, {"keys": "Return"}]})
assert "already sent" in asyncio.run(live._tool(another, halt))["error"] and len(sent_steps) == 2
# ...but a second chat, checked with an expect step ("hi to Sam and bye to Alex"), is a message of its own
to_alex = types.SimpleNamespace(name="act", args={"steps": [{"click_on": "Alex in the list"}, {"expect": "the chat is with Alex"},
                                                            {"type": "bye"}, {"keys": "Return"}]})
assert "error" not in asyncio.run(live._tool(to_alex, halt)) and len(sent_steps) == 3
live.user_spoke_at = time.time() + 2
live.typed = {"hi": {"at": time.time(), "sent": False}}  # a cancelled act typed it, then stopped before Return
asyncio.run(live._tool(send, halt))
assert sent_steps[-1] == [{"keys": "Return"}], sent_steps[-1]
# a chat opened by typing its name, then a send, with no check of which chat opened: a misheard "Brian" for Ryan is refused
live.user_spoke_at = time.time() + 3
brian = types.SimpleNamespace(name="act", args={"steps": [{"keys": "ctrl+k"}, {"type": "Brian"}, {"keys": "Return"},
                                                          {"type": "hello"}, {"keys": "Return"}]})
assert "expect" in asyncio.run(live._tool(brian, halt))["error"] and len(sent_steps) == 4
live.brain = real_brain
# something Jarvis announces is in the chat once: tell() logged it, so the spoken copy isn't added again
logged, real_emit = [], jarvis.emit
jarvis.emit = lambda kind, **kw: logged.append(kw.get("text"))
live.heard, live.said, live.announcing = "", "Maya is calling on WhatsApp.", True
live._flush()
live.said, live.announcing = "Sure, Q.", False
live._flush()
jarvis.emit = real_emit
assert logged == ["Sure, Q."] and live.last_said == "Sure, Q.", logged

# the phone app's link: the handshake proves the PC, frames are sealed and counted, pairing trades the one-time secret
# for a token, and a phone that isn't paired gets nothing done
import phone
phone.STATE_FILE = os.path.join(store.DATA, "phone-test.json")
asked_phone, answer_now, phone_chat = [], threading.Event(), []  # (the reply waits for the test: it can't overtake "working")
answer_now.set()
link = phone.PhoneLink(types.SimpleNamespace(ask=lambda text, remote=False: answer_now.wait(5) and (asked_phone.append(text) or "done"),
                                             ask_lock=threading.Lock(), interrupt=lambda: None), notify=lambda t: None,
                       chat=lambda who, text: phone_chat.append((who, text)))
assert phone.PhoneLink(link.brain).id == link.id  # (the identity is kept)
link.set_relay("https://relay.example.workers.dev/")
assert link.state["relay"] == "wss://relay.example.workers.dev" and "ws:" in link.host_url("ws://x") and "&sig=" in link.host_url("ws://x")
frames = []


async def relay_send(frame):
    frames.append(frame)
link.ws = types.SimpleNamespace(send=relay_send)
c = "c" * 36


def phone_says(message=None, raw=None):
    frames.clear()
    asyncio.run(link._frame(c.encode() + (raw if raw is not None else chan.seal(message))))
    return [f if isinstance(f, str) else chan.open(f[36:]) for f in frames]


hello, finish = phone.connect(phone.raw(link.enc_key.public_key()))
asyncio.run(link._frame(c.encode() + hello))
chan = finish(frames[0][36:])
try:  # a phone that trusts another PC's key can't finish the handshake
    phone.connect(phone.raw(phone.ec.generate_private_key(phone.ec.SECP256R1()).public_key()))[1](frames[0][36:])
    assert False
except Exception as e:
    assert not isinstance(e, AssertionError)
assert phone_says({"op": "ask", "text": "hi"})[0]["unpaired"] and not asked_phone  # not paired: refused
assert "expired" in phone_says({"op": "pair", "secret": "guess"})[0]["error"]
link.start_pairing()
assert link.status()["pairing"]["qr"].startswith("data:image/png;base64,")
payload = json.loads(phone.base64.urlsafe_b64decode(link.pair_link().split("#")[1] + "=="))
assert payload["s"] == link.id and payload["r"] == "wss://relay.example.workers.dev"
reply = phone_says({"op": "pair", "secret": payload["p"], "name": "Test phone"})[0]
assert reply["op"] == "paired" and link.pairing is None and link.status()["devices"][0]["name"] == "Test phone"
assert "expired" in phone_says({"op": "pair", "secret": payload["p"]})[0]["error"]  # (once only)
link.loop = asyncio.new_event_loop()  # (where replies from finished tasks are sent from)
threading.Thread(target=link.loop.run_forever, daemon=True).start()
answer_now.clear()
assert phone_says({"op": "ask", "id": 1, "text": "what time is it?"})[0] == {"op": "working", "id": 1, "queued": False}
answer_now.set()
for _ in range(200):
    if len(frames) > 1:
        break
    time.sleep(0.01)
assert chan.open(frames[1][36:]) == {"op": "reply", "id": 1, "text": "done"} and asked_phone[0].endswith("what time is it?")
assert phone_chat == [("you", "📱 what time is it?"), ("jarvis", "📱 done")], phone_chat  # (shown at the PC too)
link.phones.clear()  # the app was closed when the next reply came: it waits for the phone
link._task(link.phones.get(c, {}).get("device") or next(iter(link.state["devices"])), 2, "later")
time.sleep(0.1)
assert link.pending
hello, finish = phone.connect(phone.raw(link.enc_key.public_key()))  # the app comes back: a new handshake, then its token
asyncio.run(link._frame(c.encode() + hello))
chan = finish(frames[-1][36:])
said = phone_says({"op": "hello", "token": reply["token"]})
assert said[0]["op"] == "ready" and said[1] == {"op": "reply", "id": 2, "text": "done"} and not link.pending
assert phone_says(raw=b"\x03forged")[0] == json.dumps({"t": "close", "c": c})  # tampered: the connection is cut
link.unpair(link.status()["devices"][0]["id"])
assert link.status()["devices"] == []
link.loop.call_soon_threadsafe(link.loop.stop)
os.remove(phone.STATE_FILE)
# the app's test vector (android/.../handshake.json, checked by the app's HandshakeTest) still matches phone.py
vector = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "android/app/src/test/resources/handshake.json")))
vb = lambda name: phone.base64.b64decode(vector[name])
pc_key, phone_key = (phone.serialization.load_der_private_key(vb(n), None) for n in ("pc_private", "phone_private"))
welcome = vb("welcome")
to_pc, to_phone = phone.derive(pc_key.exchange(phone.ec.ECDH(), phone.point(vb("phone_public"))),
                               phone_key.exchange(phone.ec.ECDH(), phone.point(welcome[1:66])), vb("phone_public"), welcome[1:66])
pc_side = phone.Channel(to_phone, to_pc, sent=1)
assert pc_side.open(vb("phone_frame")) == {"op": "hello"} and phone.Channel(to_pc, to_phone, got=1).open(vb("frame"))["name"] == "test-pc"

# WhatsApp: Jarvis answers saved contacts after a burst of messages, leaves chats the user is writing in, keeps to its
# hourly limit, and never sends to a name that isn't exactly one chat (the page itself is faked: no browser, no account)
import sys, types, whatsapp
whatsapp.SETTLE, whatsapp.ANSWER_AFTER = 0.05, 0.05
decided = ['{"reply": "Hi, it\'s Jarvis, Q\'s assistant!", "tell_user": ""}']
asked_model = []
wa_logs, wa_told, wa_told_how, page_calls = [], [], [], []
wa = whatsapp.WhatsApp(types.SimpleNamespace(_generate=lambda contents, **kw: asked_model.append(contents) or [{"text": decided[0]}]),
                       notify=wa_logs.append, tell=lambda text, **how: wa_told.append(text) or wa_told_how.append(how),
                       name=lambda: "Q")
chats = [{"chat": "1@c.us", "name": "Sam Lee"}, {"chat": "2@c.us", "name": "Sam"}, {"chat": "3@c.us", "name": "Maya"}]


def fake_page(js, timeout=30):
    page_calls.append(js)
    if js.startswith("window.__jarvisHistory"):
        return [{"id": "m1", "me": False, "text": "hey, you around?", "at": 0}]
    if js.startswith("window.__jarvisSend"):
        return f"sent{len(page_calls)}"
    if js.startswith("window.__jarvisChats"):
        return chats
    if js.startswith("window.__jarvisCall"):
        return "over"  # (the user picked up on the phone)
    return True


wa.evaluate, wa.state = fake_page, "connected"


def wa_says(**e):
    wa.event({"ev": "msg", "id": "m1", "chat": "1@c.us", "me": False, "text": "hey", "name": "Sam Lee", "contact": True, **e})


def sends():
    return [c for c in page_calls if c.startswith("window.__jarvisSend")]


wa_says()
wa_says(id="m2")  # (a second line: still one reply, after the burst)
for _ in range(100):
    if sends():
        break
    time.sleep(0.02)
time.sleep(0.1)
assert len(sends()) == 1 and "Hi, it's Jarvis" in sends()[0] and wa.mine and "Jarvis replied" in wa_logs[-1]
assert "Sam Lee: hey, you around?" in asked_model[0][0]["parts"][0]["text"] and "Q's AI assistant" in asked_model[0][0]["parts"][0]["text"]
wa.event({"ev": "msg", "id": next(iter(wa.mine)), "chat": "1@c.us", "me": True, "text": "Hi, it's Jarvis", "name": "Sam Lee", "contact": True})
assert "1@c.us" not in wa.user_wrote  # (Jarvis's own message isn't the user chatting)
wa_says(chat="9@c.us", name="Stranger", contact=False)
assert "9@c.us" not in wa.pending and "Stranger" in wa_logs[-1]  # not a saved contact: shown, not answered
wa.event({"ev": "msg", "id": "u1", "chat": "3@c.us", "me": True, "text": "omw", "name": "Maya", "contact": True})
wa_says(chat="3@c.us", name="Maya")
time.sleep(0.3)
assert len(sends()) == 1 and "you're chatting with them" in wa_logs[-1]  # the user is talking to Maya themselves
wa.replies = [time.time()] * whatsapp.REPLY_LIMIT
wa_says(chat="2@c.us", name="Sam")
time.sleep(0.3)
assert len(sends()) == 1 and "a lot this hour" in wa_logs[-1]
wa.replies, decided[0] = [], 'Sure:\n```json\n{"reply": "", "tell_user": "Sam says his car broke down and needs a lift"}\n```'
wa_says(chat="2@c.us", name="Sam")
time.sleep(0.3)
assert len(sends()) == 1 and wa_told == ["WhatsApp from Sam: Sam says his car broke down and needs a lift"]
assert wa.find("sam")[0]["chat"] == "2@c.us" and wa.find("Sam Le")[1]["close_matches"] == ["Sam Lee", "Sam"]
wa_told.clear()
wa._ring({"id": "c1", "name": "Maya", "contact": True, "video": False, "group": False, "outgoing": False})
assert "Maya is calling" in wa_told[0] and wa.call is None  # picked up on the phone: Jarvis stays out
assert wa_told_how[-1] == {"keep": False}  # (a ring isn't kept in the agent's history: a dozen of them pushed a task out)
store.update_settings({"whatsapp_calls": "decline"})
wa._ring({"id": "c2", "name": "Maya", "contact": True, "video": False, "group": False, "outgoing": False})
assert page_calls[-1] == "window.__jarvisButton('decline')"
store.update_settings({"whatsapp_calls": "answer"})
try:
    store.update_settings({"whatsapp_calls": "maybe"})
    raise AssertionError("a bad WhatsApp calls setting was saved")
except ValueError:
    pass
# the user's lists: "always let through" is never answered or picked up, and is said out loud (even in quiet hours);
# "never answer" is only shown
store.update_settings({"whatsapp_always": "maya\n", "whatsapp_never": ["Stranger"]})
wa_told.clear()
before = len(page_calls)
wa._ring({"id": "c3", "name": "Maya", "contact": True, "video": False, "group": False, "outgoing": False})
assert wa_told == ["Maya is calling you on WhatsApp."] and wa_told_how[-1] == {"keep": False, "loud": True}
assert not any("__jarvisCall" in c or "__jarvisButton" in c for c in page_calls[before:])  # (left ringing for the user)
wa._ring({"id": "c4", "name": "stranger", "contact": True, "video": False, "group": False, "outgoing": False})
assert len(wa_told) == 1 and "call from stranger" in wa_logs[-1]
wa_says(chat="3@c.us", name="Maya")
for _ in range(50):
    if len(wa_told) == 2:
        break
    time.sleep(0.02)
assert wa_told[-1] == "WhatsApp from Maya: hey, you around?" and wa_told_how[-1] == {"loud": True} and len(sends()) == 1
wa_says(chat="9@c.us", name="Stranger")
time.sleep(0.2)
assert "9@c.us" not in wa.pending and wa_logs[-1] == "💬 WhatsApp from Stranger: hey" and len(sends()) == 1
try:
    store.update_settings({"whatsapp_never": ["MAYA"]})
    raise AssertionError("a name was saved in both lists")
except ValueError:
    pass
store.update_settings({"whatsapp_always": [], "whatsapp_never": []})
# auto-replies keep to the user's languages
asked_model.clear()
store.update_settings({"languages": ["fr-FR"]})
wa.decide("Sam", [])
store.update_settings({"languages": []})
wa.decide("Sam", [])
assert "if it's English or French, otherwise in English" in asked_model[0][0]["parts"][0]["text"]
assert "like a text, in English." in asked_model[1][0]["parts"][0]["text"]
# the agent's tools: an exact chat name only, and a message the user didn't confirm isn't sent
brain.whatsapp_link[0] = wa
assert set(brain.TOOLS["whatsapp_send"][0]("Sammy", "hi")["close_matches"]) == {"Sam Lee", "Sam"} and len(sends()) == 1
assert brain.TOOLS["whatsapp_send"][0]("Maya", "on my way")["error"] == brain.NEEDS_YES and len(sends()) == 1
assert brain.TOOLS["whatsapp_send"][0]("Maya", "on my way", confirmed=True) == {"result": "sent to Maya"} and len(sends()) == 2
assert "whatsapp_read" in brain.OUTSIDE_CONTENT and brain.TOOLS["whatsapp_read"][0]()["chats"] == chats
# groups are found and read too, each message by who wrote it (Jarvis said a group the user was in didn't exist)
chats.append({"chat": "9@g.us", "name": "Chess Club", "group": True})
wa.evaluate = lambda js, timeout=30: ([{"id": "g1", "me": False, "text": "contest at 5", "at": 0, "by": "Alex"}]
                                      if js.startswith("window.__jarvisHistory") else fake_page(js))
assert brain.TOOLS["whatsapp_read"][0]("chess club")["messages"][0]["from"] == "Alex"
# a voice message is listened to (it said "can't listen to voice notes"): the bytes go to the model as audio
heard_media, real_vision = [], brain.vision[0]
brain.vision[0] = lambda contents: heard_media.append(contents[0]["parts"][0]["inlineData"]) or [{"text": "See you at 5."}]
wa.evaluate = lambda js, timeout=30: ({"id": "v1", "type": "ptt", "mime": "audio/ogg", "at": 0, "caption": "", "by": None, "me": False,
                                       "data": "T2dnUw=="} if js.startswith("window.__jarvisMedia") else fake_page(js))
got = brain.TOOLS["whatsapp_media"][0]("maya")
assert got["voice message"] == "See you at 5." and got["from"] == "Maya" and heard_media == [{"mimeType": "audio/ogg", "data": "T2dnUw=="}], got
wa.evaluate = lambda js, timeout=30: None if js.startswith("window.__jarvisMedia") else fake_page(js)
assert "no voice message" in brain.TOOLS["whatsapp_media"][0]("maya")["error"]
brain.vision[0] = real_vision
# a call Jarvis places: refused without a yes; with one it rings, and nobody picking up is said (and the call is ended)
wa_told.clear()
assert brain.TOOLS["whatsapp_call"][0]("Maya", "dinner's at 8")["error"] == brain.NEEDS_YES
wa.evaluate = lambda js, timeout=30: ({"id": "k1"} if js.startswith("window.__jarvisDial") else "over" if js.startswith("window.__jarvisCall")
                                      else fake_page(js))
assert "calling Maya" in brain.TOOLS["whatsapp_call"][0]("Maya", "dinner's at 8", confirmed=True)["result"]
for _ in range(50):
    if wa_told and not wa.dialing:
        break
    time.sleep(0.1)
assert wa_told == ["Maya didn't pick up my WhatsApp call."] and wa.call is None, wa_told
assert not any("Called Maya" in c["what"] for c in store.changes())  # (a call that never connected isn't a change)
wa.dialing = True
try:
    wa.dial({"chat": "3@c.us", "name": "Maya"}, "hi")
    raise AssertionError("two calls at once")
except RuntimeError as e:
    assert "already on" in str(e)
wa.dialing = False
# on the call, Jarvis can't hang up before they've answered (it gave the message and hung up on a "hello")
dialed = whatsapp.CallSession(wa, {"id": "k2", "name": "Maya"}, "dinner's at 8")
dialed.lines, dialed.spoke_at = ["Maya: Hello?", "Jarvis: Hi Maya, it's Jarvis: Q says dinner's at 8."], time.time()
assert not dialed.may_hang_up()
dialed.lines.append("Maya: Great, see you then.")
assert dialed.may_hang_up()
dialed.lines, dialed.spoke_at = ["Jarvis: Hi Maya, it's Jarvis: Q says dinner's at 8."], time.time() - 20  # (silent for 20 s)
assert dialed.may_hang_up()
# calls speak the user's language, and switch only to the others they allow (it answered in Korean on a noisy line)
assert "Speak English. Never" in whatsapp.call_languages({"language": "en-US", "languages": []})
assert "talk to you in French or Arabic, answer in that" in whatsapp.call_languages({"language": "en-US", "languages": ["fr-FR", "ar-XA"]})
wa.evaluate = fake_page
chats.pop()
brain.whatsapp_link[0] = None
if not system.IS_WINDOWS:  # the DevTools pipe: commands on fd 3, replies on fd 4, each JSON ending in a NUL
    fake_browser = os.path.join(tempfile.mkdtemp(), "browser")
    with open(fake_browser, "w") as f:
        f.write(f"#!{sys.executable}\nimport json, os\nbuf = b''\nwhile True:\n    c = os.read(3, 65536)\n    if not c: break\n"
                "    buf += c\n    while b'\\0' in buf:\n        m, buf = buf.split(b'\\0', 1)\n"
                "        os.write(4, json.dumps({'id': json.loads(m)['id'], 'result': {'ok': 1}}).encode() + b'\\0')\n")
    os.chmod(fake_browser, 0o755)
    dt = system.Devtools(fake_browser, tempfile.mkdtemp(), [])
    dt.send({"id": 7, "method": "Browser.getVersion"})
    assert dt.recv() == {"id": 7, "result": {"ok": 1}}
    dt.close()

print("ok")
