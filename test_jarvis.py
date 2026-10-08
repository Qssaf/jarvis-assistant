"""Quick checks for the non-model logic: run with `.venv/bin/python test_jarvis.py` (Windows: .venv\\Scripts\\python)."""
import os, tempfile

_home = tempfile.mkdtemp()  # never the user's real settings, memory or reminders
os.environ.update(XDG_CONFIG_HOME=os.path.join(_home, "config"), XDG_DATA_HOME=os.path.join(_home, "data"), APPDATA=_home,
                  PYTHON_KEYRING_BACKEND="keyring.backends.fail.Keyring")  # (and never the real keychain)

import brain
import system

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
real_thread, brain.threading.Thread = brain.threading.Thread, lambda target, daemon: type("T", (), {"start": lambda self: None})()  # no real probes
assert b._generate([])[0]["text"] == "from m3"
assert b._generate([])[0]["text"] == "from m3"
assert Fake.calls == ["m1", "m2", "m3", "m3"]  # m1 cooling down, m2 waiting for its probe
b.backends["c"] = Fake("bad")
try:
    b._generate([])
    raise AssertionError("BadRequest should stop the chain")
except brain.BadRequest:
    pass
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

# memory and reminder storage (in a temp folder)
import tempfile
tmp = tempfile.mkdtemp()
store.MEMORY_FILE, store.REMINDERS_FILE = f"{tmp}/memory.md", f"{tmp}/reminders.json"
store.remember("likes tea"); store.remember("exam on June 5")
assert store.forget("TEA") == 1 and "June 5" in store.memory() and "tea" not in store.memory()
store.add_reminder(100, "past"); store.add_reminder(10**12, "future")
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
a.contents, a.cancel = [], brain.threading.Event()
a._system = lambda: ""
assert a.ask("12 times 12 then close it") == "144, sir. Closed it." and OneShot.calls == 1
# page text: attribute values may contain markup, scripts are dropped, entities decoded
assert brain.page_text('<div data-x="a<b>c</ref>">Hello&nbsp;<b>world</b></div><script>var x="<p>no</p>"</script> ok') == "Hello world ok"

# the mic's speech detector: talking keeps Jarvis listening; a steady hum (fan, hiss) soon stops counting as talking
import collections, types
import numpy as np
import jarvis
live = jarvis.Live.__new__(jarvis.Live)
live.mic, live.session, live.floor, live.voice_at = True, None, 100.0, 0.0
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
    system.launch, system.window_ids, system.active_window = real
    assert [c for c, _ in started] == ["chatapp --force-renderer-accessibility https://example.com", "calc"], started
    assert started[0][1]["ACCESSIBILITY_ENABLED"] == "1"
    # only an app Jarvis has just started is worth waiting for: one that's open but not in the tree never shows up
    assert brain.a11y_wait("calc") == 3 and brain.a11y_wait("discord") == 0

# the voice model can't see, so a coordinate click is refused before anything runs
import asyncio
refused = asyncio.run(live._tool(types.SimpleNamespace(name="act", args={"steps": [{"type": "hi"}, {"click": [500, 500]}]})))
assert "click_on" in refused["error"]

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
assert all(map(brain.is_read_action, ["GMAIL_FETCH_EMAILS", "GOOGLECALENDAR_EVENTS_LIST", "GITHUB_GET_THE_AUTHENTICATED_USER",
                                      "GOOGLE_CLASSROOM_COURSE_WORK_LIST", "TRELLO_GET_SEARCH"]))
assert not any(map(brain.is_read_action, ["GMAIL_SEND_EMAIL", "SLACK_ADD_TO_LIST", "GOOGLETASKS_INSERT_TASK", "GMAIL_REPLY_TO_THREAD",
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
import json, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
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
brain.chain = lambda: [("local", "tiny-model", "low")]
assert b.ask("any reminders?") == "You have no reminders."
assert seen[0][0] is None and any(t["function"]["name"] == "list_reminders" for t in seen[0][1]["tools"])
last = seen[1][1]["messages"][-1]
assert last["role"] == "tool" and last["tool_call_id"] == "t1" and '"reminders"' in last["content"]
srv.shutdown()

# the prompts describe this computer, and nothing personal or private ships
prompt = brain.Brain._system(None)
assert "{SYSTEM}" not in prompt and ("Windows" in prompt or "Linux" in prompt)
assert "{SYSTEM}" not in jarvis.LIVE_PROMPT.replace("{SYSTEM}", system.describe())
assert "kcalc" not in jarvis.VOICE_ACT or system.CALC == "kcalc"
assert list(brain.BACKENDS)[0] == "aistudio"
print("ok")
