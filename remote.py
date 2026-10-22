"""Jarvis from your phone, through a Telegram bot you make yourself: message it a task, the agent does it on the PC and
replies. Only the chat that paired with the code shown in Settings is answered; everyone else is ignored."""
import os, secrets, threading, time

import requests

import store

API = "https://api.telegram.org/bot{}/{}"
STATE_FILE = os.path.join(store.DATA, "telegram.json")  # {"chat": paired chat id, "name": who, "offset": next update}
LIMIT = 4000  # characters per Telegram message (its limit is 4096)
REMOTE_NOTE = ("[Sent from the user's phone: they're away from the PC, can't see the screen or answer out loud. Do the task, "
               "then reply in a few short sentences, as plain text; if you need them, end with the question.] ")


class Telegram:
    def __init__(self, brain, notify=print):
        self.brain, self.notify = brain, notify
        self.code = f"{secrets.randbelow(10 ** 6):06d}"  # what the user sends to pair, shown in Settings (new each run)
        self.state = store.read_json(STATE_FILE, {})
        self.error = ""
        self.wake = threading.Event()  # a new token: start polling with it at once
        self.tries = {}  # chat -> wrong pairing codes sent (after 5, that chat is ignored: no guessing the code)
        self.http = requests.Session()

    # ---- the Settings page
    def status(self):
        token = store.secret("telegram")
        return {"token": bool(token), "paired": self.state.get("name", "") if self.state.get("chat") else "",
                "code": self.code, "error": self.error}

    def set_token(self, token):
        token = token.strip()
        if token:
            me = self.http.get(API.format(token, "getMe"), timeout=10).json()
            if not me.get("ok"):
                raise ValueError("Telegram didn't accept that token: copy it again from @BotFather")
        store.set_secret("telegram", token)
        self.unpair()
        self.error = ""
        self.wake.set()

    def unpair(self):
        self.state = {}
        store.write_json(STATE_FILE, self.state, private=True)

    # ---- the loop
    def run(self):
        while True:
            token = store.secret("telegram")
            if not token:
                self.wake.wait(60)
                self.wake.clear()
                continue
            try:
                self.poll(token)
                self.error = ""
            except requests.RequestException as e:
                self.error = f"can't reach Telegram ({type(e).__name__})"
                time.sleep(15)
            except Exception as e:
                self.error = str(e)[:200]
                print(f"[telegram] {e}", flush=True)
                time.sleep(15)

    def poll(self, token):
        """One long poll: wait up to 50 s for messages and handle them."""
        r = self.http.get(API.format(token, "getUpdates"), timeout=60,
                          params={"timeout": 50, "offset": self.state.get("offset", 0), "allowed_updates": '["message"]'}).json()
        if not r.get("ok"):
            raise RuntimeError(f"Telegram: {r.get('description', 'refused')} (paste the bot's token again in Settings)")
        for update in r.get("result", []):
            self.state["offset"] = update["update_id"] + 1
            store.write_json(STATE_FILE, self.state, private=True)  # (each one handled once, even after a restart)
            msg = update.get("message") or {}
            chat, text = (msg.get("chat") or {}).get("id"), (msg.get("text") or "").strip()
            if chat is not None and text:
                self.handle(token, chat, text, (msg.get("from") or {}).get("first_name", ""))

    def handle(self, token, chat, text, name):
        if not self.state.get("chat"):
            if self.tries.get(chat, 0) >= 5:
                return
            if text in (f"/start {self.code}", self.code):
                self.state.update(chat=chat, name=name or "your phone")
                store.write_json(STATE_FILE, self.state, private=True)
                self.notify(f"Paired with {self.state['name']} on Telegram: messages from that chat now reach Jarvis.")
                self.send(token, chat, "Paired. Send me anything you'd ask Jarvis at the PC.")
            else:
                self.tries[chat] = self.tries.get(chat, 0) + (0 if text == "/start" else 1)
                self.send(token, chat, "Send the pairing code shown in Jarvis's Settings to connect this chat.")
            return
        if chat != self.state["chat"]:
            print("[telegram] ignored a message from a chat that isn't paired", flush=True)
            return
        if text == "/stop":
            self.brain.interrupt()
            self.send(token, chat, "Stopped.")
            return
        self.notify(f"📱 From your phone: {text}")
        if self.brain.ask_lock.locked():
            self.send(token, chat, "Jarvis is busy with another task; yours starts when it's done.")
        # (off the polling thread: while it runs, /stop and new messages still get read)
        threading.Thread(target=self._task, args=(token, chat, text), daemon=True).start()

    def _task(self, token, chat, text):
        try:
            reply = self.brain.ask(REMOTE_NOTE + text, remote=True)
        except Exception as e:
            reply = f"The task failed: {e}"
        try:
            self.send(token, chat, reply)
        except requests.RequestException as e:
            print(f"[telegram] couldn't send the reply: {e}", flush=True)

    def push(self, text):
        """Something Jarvis did or found on its own (a scheduled task, a check), sent to the paired chat."""
        token = store.secret("telegram")
        if token and self.state.get("chat"):
            self.send(token, self.state["chat"], text)

    def send(self, token, chat, text):
        for i in range(0, max(len(text), 1), LIMIT):
            self.http.post(API.format(token, "sendMessage"), json={"chat_id": chat, "text": text[i:i + LIMIT] or "Done."}, timeout=20)
