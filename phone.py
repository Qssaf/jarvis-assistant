"""Jarvis in its own phone app, through your private relay (relay/worker.js, on your own Cloudflare account). The PC and
the phone both dial out to the relay, so nothing on the PC is open to the internet, and everything between them is
end-to-end encrypted: the relay only ever forwards ciphertext. Pairing is a QR code in Settings carrying the relay's
address, this PC's id and public key (what the phone trusts) and a one-time secret; the phone trades the secret for
its own token, which every later connection shows.

The handshake: the phone sends a fresh P-256 key; the PC answers with its own fresh key and a short sealed proof.
Both sides derive one AES-256-GCM key each way from ECDH(PC's long-term key, phone's fresh key) + ECDH(both fresh
keys), so only the PC holding its private key can answer, and a recorded session can't be read later. Frames are
counted, never sent twice, in order (the relay keeps them in order), and the counter is the nonce."""
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
    def __init__(self, brain, notify=print):
        self.brain, self.notify = brain, notify
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
        self.phones = {}  # relay connection id -> {"channel": Channel, "device": paired device id or None, "tries": n}
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
        return {"relay": self.state.get("relay", ""), "connected": self.connected, "error": self.error, "pairing": pairing,
                "devices": [{"id": d, "name": v["name"]} for d, v in self.state["devices"].items()],
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
        try:
            # a copy of the relay folder: wrangler writes its own files next to the worker, and Jarvis's may be read-only
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
                shutil.copytree(RELAY_FOLDER, folder, dirs_exist_ok=True)
                said = []  # (not shown: it names the account)
                system.run_lines(npx + ["whoami"], said.append, cwd=folder, timeout=120)
                if "not authenticated" in "\n".join(said):
                    show("Sign in to Cloudflare in your browser…")
                    if system.run_lines(npx + ["login"], show, cwd=folder):
                        raise RuntimeError("the Cloudflare sign-in didn't finish")
                show("Putting the relay online…")
                code = system.run_lines(npx + ["deploy"], lambda line: show(line) or deployed.append(line), cwd=folder)
            urls = re.findall(r"https://[\w.-]+\.workers\.dev\b", "\n".join(deployed))
            if code or not urls:
                raise RuntimeError(next((line for line in reversed(log) if "ERROR" in line), "wrangler didn't print the relay's address"))
            self.set_relay(urls[-1])
            show(f"The relay is online at {urls[-1]}")
            self.setup["running"] = False
        except Exception as e:
            self.setup.update(running=False, error=str(e)[:300] or type(e).__name__)

    def start_pairing(self):
        if not self.state.get("relay"):
            raise ValueError("add your relay's address first")
        self.pairing = {"secret": b64url(secrets.token_bytes(16)), "until": time.time() + PAIR_SECONDS}
        return self.status()

    def pair_link(self):
        payload = {"v": 1, "r": self.state["relay"], "s": self.id, "k": b64url(raw(self.enc_key.public_key())),
                   "p": self.pairing["secret"]}
        return "jarvis://pair#" + b64url(json.dumps(payload, separators=(",", ":")).encode())  # (a fragment: never sent on)

    def unpair(self, device):
        self.state["devices"].pop(device, None)
        self.pending.pop(device, None)
        self.save()
        for c, phone in list(self.phones.items()):
            if phone["device"] == device:
                self._call(self._drop(c))

    # ---- the connection to the relay
    def run(self):
        asyncio.run(self._main())

    async def _main(self):
        import websockets
        self.loop, self.changed, wait = asyncio.get_running_loop(), asyncio.Event(), 2
        while True:
            relay = self.state.get("relay")
            if relay:
                started = time.time()
                try:
                    async with websockets.connect(self.host_url(relay), max_size=2 ** 20, ping_interval=20, open_timeout=15) as ws:
                        self.ws, self.connected, self.error, self.phones = ws, True, "", {}
                        async for frame in ws:
                            await self._frame(frame)
                except Exception as e:
                    self.error = "another Jarvis with this identity took over" if getattr(getattr(e, "rcvd", None), "code", 0) == 4001 \
                        else f"can't reach the relay ({str(e)[:120] or type(e).__name__})"
                    print(f"[phone] {self.error}", flush=True)
                self.ws, self.connected, self.phones = None, False, {}
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

    async def _frame(self, frame):
        if isinstance(frame, str):  # the relay: a phone came or went
            m = json.loads(frame)
            if m.get("t") in ("open", "close"):
                self.phones.pop(m.get("c"), None)
            return
        c, data = frame[:36].decode(errors="replace"), frame[36:]
        phone = self.phones.setdefault(c, {"channel": None, "device": None, "tries": 0})
        try:
            if data[:1] == bytes([HELLO]):  # (a new handshake starts the conversation over)
                welcome, phone["channel"] = accept(self.enc_key, data)
                phone["device"] = None
                return await self.ws.send(c.encode() + welcome)
            message = phone["channel"].open(data)
        except Exception:  # not from a phone that did the handshake: it gets nothing
            return await self._drop(c)
        await self._handle(c, phone, message)

    async def _send(self, c, message):
        phone = self.phones.get(c)
        if phone and phone["channel"] and self.ws:
            await self.ws.send(c.encode() + phone["channel"].seal(message))

    async def _drop(self, c):
        self.phones.pop(c, None)
        if self.ws:
            await self.ws.send(json.dumps({"t": "close", "c": c}))

    async def _refuse(self, c, phone, error, unpaired=False):
        phone["tries"] += 1  # (five wrong secrets or tokens and that connection is cut: no guessing)
        await self._send(c, {"op": "error", "error": error, "unpaired": unpaired})
        if phone["tries"] >= 5:
            await self._drop(c)

    async def _handle(self, c, phone, m):
        op, devices = m.get("op"), self.state["devices"]
        if op == "pair":
            p = self.pairing
            if not (p and time.time() < p["until"] and hmac.compare_digest(str(m.get("secret", "")), p["secret"])):
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
            await self._send(c, {"op": "ready", "name": socket.gethostname(), "busy": self.brain.ask_lock.locked()})
            for reply in self.pending.pop(device, []):
                await self._send(c, reply)
            return
        if not phone["device"] or phone["device"] not in devices:
            return await self._refuse(c, phone, "This phone isn't paired with Jarvis any more: pair it again.", unpaired=True)
        if op == "ask" and str(m.get("text", "")).strip():
            text = str(m["text"]).strip()
            self.notify(f"📱 From your phone: {text}")
            await self._send(c, {"op": "working", "id": m.get("id"), "queued": self.brain.ask_lock.locked()})
            threading.Thread(target=self._task, args=(phone["device"], m.get("id"), text), daemon=True).start()
        elif op == "stop":
            self.brain.interrupt()
            await self._send(c, {"op": "stopped"})

    def _task(self, device, request, text):
        try:
            reply = self.brain.ask(REMOTE_NOTE + text, remote=True)
        except Exception as e:
            reply = f"The task failed: {e}"
        self._call(self._deliver(device, {"op": "reply", "id": request, "text": reply}))

    def push(self, text):
        """Something Jarvis did or found on its own (a scheduled task, a check), sent to every paired phone."""
        for device in self.state["devices"]:
            self._call(self._deliver(device, {"op": "reply", "text": text}))

    async def _deliver(self, device, message):
        c = next((c for c, p in self.phones.items() if p["device"] == device and p["channel"]), None)
        if c:
            await self._send(c, message)
        else:
            self.pending.setdefault(device, []).append(message)
            del self.pending[device][:-20]
