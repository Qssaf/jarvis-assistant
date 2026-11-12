"""Jarvis in its own phone app, through your private relay (relay/worker.js, on your own Cloudflare account). The PC and
the phone both dial out to the relay, so nothing on the PC is open to the internet, and everything between them is
end-to-end encrypted: the relay only ever forwards ciphertext. Pairing is a QR code in Settings carrying the relay's
address, this PC's id and public key (what the phone trusts) and a one-time secret; the phone trades the secret for
its own token, which every later connection shows.

The handshake: the phone sends a fresh P-256 key; the PC answers with its own fresh key and a short sealed proof.
Both sides derive one AES-256-GCM key each way from ECDH(PC's long-term key, phone's fresh key) + ECDH(both fresh
keys), so only the PC holding its private key can answer, and a recorded session can't be read later. Frames are
counted, never sent twice, in order (the relay keeps them in order), and the counter is the nonce.

The direct way in: while a phone is paired (or a pairing code is showing) the PC also listens on PORT for the same
handshake, so a phone on the same Wi-Fi, or on a VPN like Tailscale, needs no relay. Whoever connects there gets the
handshake and nothing else: every frame after it must open with the keys only the paired phone can derive.

Inside the channel, a phone asks (`ask`, `stop`), talks (`voice`, `audio`, `barge`: its microphone and speaker stand in
for the PC's, see jarvis.PhoneVoice), reads a few of the window's pages and stops a task (`get`, `post`: PHONE_GET,
PHONE_POST) and fetches the wake word's models (`wake`). The PC sends `event` for every line of the chat and change of state."""
import asyncio, base64, hashlib, hmac, json, os, re, secrets, shutil, socket, tempfile, threading, time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

import store
import system
from remote import REMOTE_NOTE

STATE_FILE = os.path.join(store.DATA, "phone.json")  # {"relay": url, "sign"/"enc": PEM keys, "devices": {id: {...}}}
PAIR_SECONDS = 600  # how long a pairing QR code works
PORT = 47800  # the direct way in (the next free one if it's taken: the pairing code and every `ready` say which)
MAX_DIRECT = 8  # direct connections at once (the relay's MAX_PHONES)
STRANGER = 20  # seconds a direct connection has to show it's a paired phone (or to pair)
CHUNK = 180_000  # bytes of a wake word model per frame (frames stay well under the relay's 1 MiB)
# what a paired phone may read and do of the window's API: nothing else (settings, keys, accounts and data stay the PC's)
PHONE_GET = ("/api/today", "/api/reminders", "/api/media", "/api/system", "/api/conversation", "/api/screen", "/api/jobs")
PHONE_POST = re.compile(r"/api/(media/(PlayPause|Next|Previous)|jobs/\d+/stop|stop|new)")
HELLO, WELCOME, DATA = 1, 2, 3  # the first byte of every frame between the phone and the PC
INFO = b"jarvis-relay-v1"
RELAY_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "relay")  # (the Windows build carries it too)
NODE_HELP = ("Setting the relay up needs Node.js: install it from nodejs.org (on Linux, your package manager's nodejs and "
             "npm), then try again.")


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def raw(public_key):
    return public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)


def point(data):
    return ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), bytes(data))


def nonce(n):
    return n.to_bytes(12, "big")


def token_hash(token):
    return hashlib.sha256(str(token).encode()).hexdigest()


class Channel:
    """One encrypted conversation: a key and a frame counter each way."""

    def __init__(self, send_key, receive_key, sent=0, got=0):
        self.out, self.into, self.sent, self.got = AESGCM(send_key), AESGCM(receive_key), sent, got

    def seal(self, message):
        frame = bytes([DATA]) + self.out.encrypt(nonce(self.sent), json.dumps(message).encode(), None)
        self.sent += 1
        return frame

    def open(self, frame):
        if frame[:1] != bytes([DATA]):
            raise ValueError("not a data frame")
        message = json.loads(self.into.decrypt(nonce(self.got), bytes(frame[1:]), None))
        self.got += 1
        return message


def derive(long_term, fresh, phone_key, pc_key):
    keys = HKDF(hashes.SHA256(), 64, phone_key + pc_key, INFO).derive(long_term + fresh)
    return keys[:32], keys[32:]  # (phone to PC, PC to phone)


def accept(enc_key, hello):
    """The PC's side of the handshake: (the welcome frame to send back, the Channel)."""
    if len(hello) != 66 or hello[0] != HELLO:
        raise ValueError("not a hello")
    phone_key, fresh = bytes(hello[1:]), ec.generate_private_key(ec.SECP256R1())
    to_pc, to_phone = derive(enc_key.exchange(ec.ECDH(), point(phone_key)), fresh.exchange(ec.ECDH(), point(phone_key)),
                             phone_key, raw(fresh.public_key()))
    return bytes([WELCOME]) + raw(fresh.public_key()) + AESGCM(to_phone).encrypt(nonce(0), b"jarvis", None), \
        Channel(to_phone, to_pc, sent=1)


def connect(pc_key):
    """The phone's side, as the app does it in Kotlin (tests use this one): (hello frame, finish(welcome) -> Channel)."""
    fresh = ec.generate_private_key(ec.SECP256R1())

    def finish(welcome):
        if len(welcome) < 66 or welcome[0] != WELCOME:
            raise ValueError("not a welcome")
        to_pc, to_phone = derive(fresh.exchange(ec.ECDH(), point(pc_key)), fresh.exchange(ec.ECDH(), point(welcome[1:66])),
                                 raw(fresh.public_key()), bytes(welcome[1:66]))
        if AESGCM(to_phone).decrypt(nonce(0), bytes(welcome[66:]), None) != b"jarvis":
            raise ValueError("the PC didn't prove who it is")
        return Channel(to_pc, to_phone, got=1)
    return bytes([HELLO]) + raw(fresh.public_key()), finish


class PhoneLink:
    def __init__(self, brain, notify=print, chat=lambda who, text: print(f"[{who}] {text}"), api=None, voice=None,
                 label=str):
        self.brain, self.notify, self.chat = brain, notify, chat  # notify: a notice; chat: a line of the conversation
        self.api = api      # {"get": f(path), "post": f(path, data)}: the window's API, for PHONE_GET and PHONE_POST
        self.voice = voice  # jarvis.PhoneVoice: a phone's microphone and speaker in the PC's voice session
        self.label = label  # a tool's name as the chat shows it ("Reading your screen")
        self.floor = None   # the connection whose phone is talking with Jarvis now
        self.server, self.port, self.direct_n, self.direct_lock = None, 0, 0, None  # the direct way in
        self.state = store.read_json(STATE_FILE, {})
        if not self.state.get("sign"):
            pem = lambda: ec.generate_private_key(ec.SECP256R1()).private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
            self.state.update(sign=pem(), enc=pem(), devices={})
            self.save()
        load = lambda name: serialization.load_pem_private_key(self.state[name].encode(), None)
        self.sign_key, self.enc_key = load("sign"), load("enc")
        self.id = b64url(hashlib.sha256(raw(self.sign_key.public_key())).digest())  # what the relay knows this PC by
        self.pairing = None  # {"secret": the QR code's one-time secret, "until": when it stops working}
        self.error, self.connected = "", False
        self.setup = {}  # "Set up my relay": {"running", "log": wrangler's last lines, "error"}
        self.loop = self.ws = self.changed = None
        # connection id (the relay's, or "direct-n") -> {"channel": Channel, "device": paired device id or None,
        # "tries": n, "relay": came through the relay, "send": coroutine(bytes), "close": coroutine()}
        self.phones = {}
        self.pending = {}  # device -> replies it hasn't received yet (the app was closed when they came)

    def save(self):
        store.write_json(STATE_FILE, self.state, private=True)

    # ---- the Settings page
    def status(self):
        pairing = None
        if self.pairing and time.time() < self.pairing["until"]:
            import segno
            link = self.pair_link()
            pairing = {"link": link, "qr": segno.make(link, error="m").png_data_uri(scale=6, border=2)}
        online = {p["device"] for p in list(self.phones.values())}
        return {"relay": self.state.get("relay", ""), "connected": self.connected, "error": self.error, "pairing": pairing,
                "devices": [{"id": d, "name": v["name"], "online": d in online} for d, v in self.state["devices"].items()],
                "direct": self.direct_addresses(),
                "setup": {**self.setup, "log": self.setup.get("log", [])[-6:]}}

    def set_relay(self, url):
        url = url.strip().rstrip("/").replace("https://", "wss://", 1).replace("http://", "ws://", 1)
        if url and not url.startswith(("wss://", "ws://")):
            raise ValueError("paste your relay's address, like https://jarvis-relay.you.workers.dev")
        self.state["relay"], self.error, self.connected = url, "", False
        self.save()
        self._kick()

    def set_up_relay(self):
        """Puts the user's own relay online with Cloudflare's wrangler, in the background: a sign-in in the browser if
        there's none yet, then a deploy, whose workers.dev address becomes the relay."""
        if self.setup.get("running"):
            return
        if not system.have("npx"):
            self.setup = {"running": False, "log": [], "error": NODE_HELP}
            return
        self.setup = {"running": True, "log": [], "error": ""}
        threading.Thread(target=self._set_up_relay, daemon=True).start()

    def _set_up_relay(self):
        log, deployed, npx = self.setup["log"], [], ["npx", "--yes", "wrangler"]

        def show(line):
            line = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()  # (wrangler's colours)
            if line:
                log.append(line)
                del log[:-50]

        def me(folder):  # who's signed in, and their accounts ({} if no one, or wrangler couldn't say). Never shown: the
            said = []    # accounts are named after the person's email
            if system.run_lines(npx + ["whoami", "--json"], said.append, cwd=folder):
                return {}
            text = "\n".join(said)
            try:
                return json.loads(text[text.find("{"):])  # (after any warning wrangler prints first)
            except ValueError:
                return {}
        try:
            # a copy of the relay folder: wrangler writes its own files next to the worker, and Jarvis's may be read-only
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
                shutil.copytree(RELAY_FOLDER, folder, dirs_exist_ok=True)
                who = me(folder)  # (the first run also downloads wrangler; anything but a clear "logged in" means signing in)
                if not who.get("loggedIn"):
                    show("Sign in to Cloudflare in your browser…")
                    if system.run_lines(npx + ["login"], show, cwd=folder):
                        raise RuntimeError("the Cloudflare sign-in didn't finish")
                    who = me(folder)
                accounts = [a for a in who.get("accounts") or [] if re.fullmatch(r"[0-9a-f]{32}", str(a.get("id")))]
                if len(accounts) > 1:  # wrangler can't ask which without a terminal: the signed-in person's own account
                    mine = next((a for a in accounts  # (Cloudflare keeps the email's capitals as first typed; the login's are lower)
                                 if str(a.get("name")).lower() == f"{who.get('email')}'s account".lower()), None)
                    own = mine or accounts[0]
                    toml = os.path.join(folder, "wrangler.toml")
                    with open(toml) as f:
                        text = f.read()
                    with open(toml, "w") as f:
                        f.write(f'account_id = "{own["id"]}"\n' + text)
                    show(f"Your sign-in has {len(accounts)} Cloudflare accounts: using {'your own' if mine else 'the first one'}")
                show("Putting the relay online…")
                for retry in (True, False):
                    deployed.clear()
                    code = system.run_lines(npx + ["deploy"], lambda line: show(line) or deployed.append(line), cwd=folder)
                    if not code or not retry or not any("fetch failed" in line for line in deployed):
                        break
                    show("Cloudflare didn't answer: trying again…")  # (a network blip: it failed the first try once)
            urls = re.findall(r"https://[\w.-]+\.workers\.dev\b", "\n".join(deployed))
            if code or not urls:
                raise RuntimeError(next((line for line in reversed(log) if "ERROR" in line), "wrangler didn't print the relay's address"))
            self.set_relay(urls[-1])
            show(f"The relay is online at {urls[-1]}")
            self.setup["running"] = False
        except Exception as e:
            self.setup.update(running=False, error=str(e)[:300] or type(e).__name__)

    def start_pairing(self):
        self.pairing = {"secret": b64url(secrets.token_bytes(16)), "until": time.time() + PAIR_SECONDS}
        if self.loop:  # (the code carries the direct port: listening before it's shown)
            try:
                asyncio.run_coroutine_threadsafe(self._sync_direct(), self.loop).result(5)
            except Exception as e:
                print(f"[phone] the direct way in didn't start: {e}", flush=True)
        if not self.state.get("relay") and not self.direct_addresses():
            self.pairing = None
            raise ValueError("this PC is on no network a phone could reach: connect it to your Wi-Fi, or set up the relay")
        return self.status()

    def direct_addresses(self):
        """Where a phone on the same network (or VPN) finds this PC: ["ip:port", ...], empty while that's off."""
        return [f"{ip}:{self.port}" for ip in system.local_addresses()] if self.port else []

    def pair_link(self):
        payload = {"v": 1, "r": self.state.get("relay", ""), "s": self.id, "k": b64url(raw(self.enc_key.public_key())),
                   "p": self.pairing["secret"], "d": self.direct_addresses()}
        return "jarvis://pair#" + b64url(json.dumps(payload, separators=(",", ":")).encode())  # (a fragment: never sent on)

    def unpair(self, device):
        self.state["devices"].pop(device, None)
        self.pending.pop(device, None)
        self.save()
        for c, phone in list(self.phones.items()):
            if phone["device"] == device:
                self._call(self._drop(c))
        self._call(self._sync_direct())

    # ---- the connection to the relay
    def run(self):
        asyncio.run(self._main())

    async def _main(self):
        import websockets
        self.loop, self.changed, wait = asyncio.get_running_loop(), asyncio.Event(), 2
        asyncio.create_task(self._direct_loop())
        while True:
            relay = self.state.get("relay")
            if relay:
                started = time.time()
                try:
                    async with websockets.connect(self.host_url(relay), max_size=2 ** 20, ping_interval=20, open_timeout=15) as ws:
                        self.ws, self.connected, self.error = ws, True, ""
                        self._relay_gone()
                        async for frame in ws:
                            await self._frame(frame)
                except Exception as e:
                    self.error = "another Jarvis with this identity took over" if getattr(getattr(e, "rcvd", None), "code", 0) == 4001 \
                        else f"can't reach the relay ({str(e)[:120] or type(e).__name__})"
                    print(f"[phone] {self.error}", flush=True)
                self.ws, self.connected = None, False
                self._relay_gone()
                wait = 2 if time.time() - started > 60 else min(wait * 2, 60)
            try:
                await asyncio.wait_for(self.changed.wait(), wait if relay else None)
            except asyncio.TimeoutError:
                pass
            self.changed.clear()

    def host_url(self, relay):
        ts = str(int(time.time() * 1000))
        r, s = decode_dss_signature(self.sign_key.sign(f"jarvis-relay:{self.id}:{ts}".encode(), ec.ECDSA(hashes.SHA256())))
        sig = b64url(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
        return f"{relay}/host?id={self.id}&pub={b64url(raw(self.sign_key.public_key()))}&ts={ts}&sig={sig}"

    def _kick(self):
        """Reconnect with the new settings."""
        if self.loop:
            self.loop.call_soon_threadsafe(self.changed.set)
            if self.ws:
                self._call(self.ws.close())

    def _call(self, coro):
        if self.loop:
            asyncio.run_coroutine_threadsafe(coro, self.loop)
        else:
            coro.close()

    # ---- the direct way in
    async def _direct_loop(self):
        while True:  # (the setting, the first pairing and the last unpairing all change whether it listens)
            try:
                await self._sync_direct()
            except Exception as e:
                print(f"[phone] the direct way in: {e}", flush=True)
            await asyncio.sleep(10)

    async def _sync_direct(self):
        """Listens only while there's someone to listen for: a paired phone, or a pairing code on screen."""
        import websockets
        self.direct_lock = self.direct_lock or asyncio.Lock()  # (asked from the loop, a pairing and an unpairing at once)
        async with self.direct_lock:
            want = store.settings()["phone_direct"] and bool(
                self.state["devices"] or (self.pairing and time.time() < self.pairing["until"]))
            if want and not self.server:
                for port in (PORT, 0):
                    try:
                        self.server = await websockets.serve(self._direct, "0.0.0.0", port, max_size=2 ** 20, ping_interval=20)
                        break
                    except OSError:
                        if not port:
                            raise
                self.port = self.server.sockets[0].getsockname()[1]
                print(f"[phone] listening for paired phones on port {self.port}", flush=True)
            elif not want and self.server:
                self.server.close()
                self.server, self.port = None, 0

    async def _direct(self, ws):
        if sum(not p["relay"] for p in self.phones.values()) >= MAX_DIRECT:
            return await ws.close()
        self.direct_n += 1
        c = f"direct-{self.direct_n}"
        phone, until = self._phone(c, ws.send, ws.close, relay=False), time.time() + STRANGER
        try:
            while self.phones.get(c) is phone:
                # (a stranger that says nothing, or never gets as far as pairing, doesn't keep a place)
                frame = await asyncio.wait_for(ws.recv(), None if phone["device"] else max(0.01, until - time.time()))
                if isinstance(frame, str):  # phones only send encrypted (binary) frames
                    break
                await self._data(c, phone, bytes(frame))
        except Exception:
            pass
        finally:
            if self.phones.get(c) is phone:
                self._gone(c)
            await ws.close()

    # ---- frames from phones
    def _phone(self, c, send, close, relay=True):
        return self.phones.setdefault(c, {"channel": None, "device": None, "tries": 0, "relay": relay, "send": send, "close": close})

    def _gone(self, c):
        self.phones.pop(c, None)
        if self.floor == c:
            self._release()

    def _relay_gone(self):
        for c in [c for c, p in self.phones.items() if p["relay"]]:
            self._gone(c)

    async def _frame(self, frame):
        """A frame from the relay."""
        if isinstance(frame, str):  # the relay: a phone came or went
            m = json.loads(frame)
            if m.get("t") in ("open", "close"):
                self._gone(m.get("c"))
            return
        c = frame[:36].decode(errors="replace")

        async def send(data):
            if self.ws:
                await self.ws.send(c.encode() + data)

        async def close():
            if self.ws:
                await self.ws.send(json.dumps({"t": "close", "c": c}))
        await self._data(c, self._phone(c, send, close), frame[36:])

    async def _data(self, c, phone, data):
        try:
            if data[:1] == bytes([HELLO]):  # (a new handshake starts the conversation over)
                welcome, phone["channel"] = accept(self.enc_key, data)
                phone["device"] = None
                return await phone["send"](welcome)
            message = phone["channel"].open(data)
        except Exception:  # not from a phone that did the handshake: it gets nothing
            return await self._drop(c, phone)
        try:
            await self._handle(c, phone, message)
        except Exception as e:  # a message that isn't one: this phone is cut off (it used to end the relay's loop for all)
            print(f"[phone] dropped a connection: {type(e).__name__}", flush=True)
            await self._drop(c, phone)

    async def _send(self, c, message):
        phone = self.phones.get(c)
        if phone and phone["channel"]:
            await phone["send"](phone["channel"].seal(message))

    async def _drop(self, c, phone=None):
        phone = self.phones.get(c) or phone
        self._gone(c)
        if phone:
            await phone["close"]()

    async def _refuse(self, c, phone, error, unpaired=False):
        phone["tries"] += 1  # (five wrong secrets or tokens and that connection is cut: no guessing)
        await self._send(c, {"op": "error", "error": error, "unpaired": unpaired})
        if phone["tries"] >= 5:
            await self._drop(c)

    async def _handle(self, c, phone, m):
        op, devices = m.get("op"), self.state["devices"]
        if op == "pair":
            p = self.pairing
            if not (p and time.time() < p["until"] and hmac.compare_digest(str(m.get("secret", "")).encode(), p["secret"].encode())):
                return await self._refuse(c, phone, "That pairing code has expired: show a new one in Jarvis's Settings.")
            self.pairing, token, device = None, secrets.token_urlsafe(32), secrets.token_hex(8)
            devices[device] = {"name": str(m.get("name") or "Phone")[:60], "hash": token_hash(token), "paired": time.time()}
            self.save()
            phone["device"] = device
            self.notify(f"📱 Paired with {devices[device]['name']}: the Jarvis app reaches this PC now.")
            return await self._send(c, {"op": "paired", "token": token, "name": socket.gethostname()})
        if op == "hello":
            device = next((d for d, v in devices.items() if hmac.compare_digest(v["hash"], token_hash(m.get("token", "")))), None)
            if not device:
                return await self._refuse(c, phone, "This phone isn't paired with Jarvis any more: pair it again.", unpaired=True)
            phone["device"] = device
            for old in [o for o, p in self.phones.items() if o != c and p["device"] == device]:
                await self._drop(old)  # (the same app on a new network: the old connection is dead, and replies went into it)
            await self._send(c, {"op": "ready", "name": socket.gethostname(), "v": 2, "direct": self.direct_addresses(),
                                 "wake": self.voice.phrase() if self.voice else "",
                                 # (what the app's own Gemini session uses while this PC is off)
                                 "live": store.settings()["live_model"], "voice_name": store.settings()["voice"]})
            for reply in self.pending.pop(device, []):
                await self._send(c, reply)
            return
        if not phone["device"] or phone["device"] not in devices:
            return await self._refuse(c, phone, "This phone isn't paired with Jarvis any more: pair it again.", unpaired=True)
        if op == "ask" and str(m.get("text", "")).strip():
            text = str(m["text"]).strip()
            self.chat("you", f"📱 {text}")  # (as notices, a conversation held only from the phone was never saved)
            await self._send(c, {"op": "working", "id": m.get("id")})  # (never queued: tasks run side by side)
            threading.Thread(target=self._task, args=(phone["device"], m.get("id"), text), daemon=True).start()
        elif op == "stop":
            self.brain.interrupt()
            await self._send(c, {"op": "stopped"})
        elif op in ("get", "post") and self.api:
            asyncio.create_task(self._api(c, m))  # (the weather or a screenshot takes a moment: nothing else waits for it)
        elif op == "voice" and self.voice:
            await self._voice(c, m)
        elif op == "audio" and self.floor == c:
            self.voice.feed(base64.b64decode(str(m.get("d", ""))))
        elif op == "barge" and self.floor == c:
            self.voice.barge()
        elif op == "wake" and self.voice:
            asyncio.create_task(self._wake_files(c))

    async def _api(self, c, m):
        op, path, reply = m["op"], str(m.get("path", "")), {"op": "got", "id": m.get("id")}
        if not (path in PHONE_GET if op == "get" else PHONE_POST.fullmatch(path)):
            return await self._send(c, {**reply, "error": "The phone app can't do that."})
        try:
            args = (path,) if op == "get" else (path, m.get("data") if isinstance(m.get("data"), dict) else {})
            reply["data"] = await asyncio.to_thread(self.api[op], *args)
        except Exception as e:
            reply["error"] = str(e)[:200] or type(e).__name__
        await self._send(c, reply)

    # ---- talking with Jarvis from the phone
    async def _voice(self, c, m):
        if not m.get("on"):
            if self.floor == c:
                self._release()
            return await self._send(c, {"op": "voice", "on": False})
        if self.floor and self.floor != c:  # (another paired phone was talking: this one takes over)
            await self._send(self.floor, {"op": "voice", "on": False, "why": "Another phone is talking with Jarvis."})
            self._release()

        def play(pcm):  # (from the voice session's thread) Jarvis's voice, or None: stop playing at once
            self._call(self._send(c, {"op": "audio", "d": base64.b64encode(pcm).decode()} if pcm else {"op": "hush"}))
        try:
            why = None if self.floor == c else self.voice.start(play, tapped=m.get("how") != "wake")
        except Exception as e:
            why = f"Jarvis's voice couldn't start: {str(e)[:120]}"
        if why:
            return await self._send(c, {"op": "voice", "on": False, "why": why})
        if self.floor != c:
            self.floor = c
            asyncio.create_task(self._watch_floor(c))
        await self._send(c, {"op": "voice", "on": True})

    async def _watch_floor(self, c):
        """Tells the phone when the conversation is over: Jarvis stopped listening, or the PC took it back."""
        while self.floor == c:
            await asyncio.sleep(0.25)
            if self.floor == c and self.voice.over():
                self._release()
                await self._send(c, {"op": "voice", "on": False})

    def _release(self):
        self.floor = None
        self.voice.stop()

    async def _wake_files(self, c):
        """The wake word the PC listens for, as its three models: the app runs the same ones."""
        try:
            phrase, paths = await asyncio.to_thread(self.voice.wake_files)
            for path in paths:
                data = await asyncio.to_thread(lambda: open(path, "rb").read())
                parts = [data[i:i + CHUNK] for i in range(0, len(data), CHUNK)]
                for i, part in enumerate(parts):
                    await self._send(c, {"op": "file", "name": os.path.basename(path), "i": i, "n": len(parts),
                                         "d": base64.b64encode(part).decode()})
            await self._send(c, {"op": "wake", "phrase": phrase, "files": [os.path.basename(p) for p in paths]})
        except Exception as e:
            await self._send(c, {"op": "wake", "error": str(e)[:200] or type(e).__name__})

    def put(self, data):
        """An event of the app (jarvis.emit: this sits among its clients): the chat's lines and Jarvis's state, shown
        on every connected phone as they happen."""
        if data.get("kind") in ("log", "state") and any(p["device"] for p in list(self.phones.values())):  # (a copy: the link's thread adds and drops phones meanwhile)
            event = {"op": "event", **{k: data[k] for k in ("kind", "who", "text", "state") if k in data}}
            if event.get("who") == "tool":
                event["text"] = self.label(event["text"])
            self._call(self._broadcast(event))

    async def _broadcast(self, message):
        for c, phone in list(self.phones.items()):
            if phone["device"]:
                await self._send(c, message)

    def _task(self, device, request, text):
        try:
            reply = self.brain.ask(REMOTE_NOTE + text, remote=True, label=text)
        except Exception as e:
            reply = f"The task failed: {e}"
        self.chat("jarvis", f"📱 {reply}")  # (the chat at the PC showed the question, never the answer)
        self._call(self._deliver(device, {"op": "reply", "id": request, "text": reply}))

    def push(self, text):
        """Something Jarvis did or found on its own (a scheduled task, a check), sent to every paired phone."""
        for device in list(self.state["devices"]):
            self._call(self._deliver(device, {"op": "reply", "text": text}))

    async def _deliver(self, device, message):
        c = next((c for c, p in self.phones.items() if p["device"] == device and p["channel"]), None)
        if c:
            await self._send(c, message)
        else:
            self.pending.setdefault(device, []).append(message)
            del self.pending[device][:-20]
