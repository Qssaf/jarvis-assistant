"""Jarvis on the user's own Discord, through Vesktop (Discord with Vencord built in): Jarvis reads and sends messages
inside the running client, through Chromium's debugging port (Vesktop started with PORT, see system.restart_vesktop),
using the stores Vencord exposes (Vencord.Webpack.Common). It's the user's own client doing what they'd do by hand:
no bot, no token copied out, nothing on screen. The port only listens on 127.0.0.1, and it gives what the user's
files already do (the login sits in Vesktop's folder): anything running as the user can use it.

Not an official API: Discord bans accounts that act like bots, so Jarvis sends what the user asks for and, only if they
turn it on, short answers to their friends' DMs (Listener), within WhatsApp's limits."""
import base64, collections, hashlib, json, threading, time, urllib.request

import requests

import brain
import people
import store
import system
import whatsapp

PORT = 47652
FLAG = f"--remote-debugging-port={PORT}"
LIMIT = 2000  # characters in one Discord message (without Nitro)
MEDIA_LIMIT = 20 * 1024 * 1024  # bytes of a photo or voice message Jarvis downloads to look at or listen to

# One call into the page: (cmd, args) -> JSON. Names: a DM by the person's name, a group DM by its name (or members),
# a server channel as "Server #channel", a server by its name, a friend with no DM yet by their name.
JS = r"""async (cmd, a) => {
  const C = window.Vencord?.Webpack?.Common, me = C?.UserStore?.getCurrentUser()?.id;
  if (!me) return {error: "Discord is still starting"};
  const R = C.ReadStateStore;
  const who = (u, g) => (g && C.GuildMemberStore.getNick(g, u.id)) || C.RelationshipStore.getNickname(u.id) || u.globalName || u.global_name || u.username;
  const title = c => c.guild_id ? `${C.GuildStore.getGuild(c.guild_id)?.name} #${c.name}`
    : c.name || c.recipients.map(id => C.UserStore.getUser(id)).filter(Boolean).map(u => who(u)).join(", ");
  const muted = c => C.UserGuildSettingsStore.isChannelMuted(c.guild_id ?? null, c.id) || (c.guild_id && C.UserGuildSettingsStore.isMuted(c.guild_id));
  const channels = g => C.GuildChannelStore.getChannels(g).SELECTABLE.map(s => s.channel);
  const text = (m, g) => [m.content
      .replace(/<@!?(\d+)>/g, (_, id) => "@" + (C.UserStore.getUser(id) ? who(C.UserStore.getUser(id), g) : "someone"))
      .replace(/<#(\d+)>/g, (_, id) => "#" + (C.ChannelStore.getChannel(id)?.name ?? "channel"))
      .replace(/<a?(:\w+:)\d+>/g, "$1"),
    ...m.attachments.map(f => `[file: ${f.filename}]`), ...(m.sticker_items || []).map(s => `[sticker: ${s.name}]`),
    ...m.embeds.filter(e => e.title).map(e => `[link: ${e.title}]`)].filter(Boolean).join(" ");
  // "@kanzoid" -> a real mention: a server member (as Discord has loaded them) or a DM member, by username, display name or nickname
  const ping = (t, c) => t.replace(/(^|\s)@(\w[\w.]{0,30}\w)/g, (all, sp, n) => {
    const people = (c?.guild_id ? C.GuildMemberStore.getMemberIds(c.guild_id) : c?.recipients || []).map(id => C.UserStore.getUser(id));
    const u = people.find(u => u && [u.username, u.globalName, c.guild_id && C.GuildMemberStore.getNick(c.guild_id, u.id)]
      .some(x => x?.toLowerCase() === n.toLowerCase()));
    return u ? `${sp}<@${u.id}>` : all;
  });
  const dm = id => a.kind === "friend" ? C.ChannelActionCreators.getOrEnsurePrivateChannel(id) : id;
  const chan = () => a.kind === "friend" ? C.ChannelStore.getDMFromUserId(a.id) : a.id;  // (a friend's DM, if there is one)
  const recent = async id => (await C.RestAPI.get({url: `/channels/${id}/messages`, query: {limit: a.count || 30}})).body;
  // a message by id, or with "last" (or none) the newest from someone else
  const message = async (id, ref) => (await recent(id)).find(m => ref && ref !== "last" ? m.id === ref : m.author.id !== me);
  if (cmd === "chats") {
    const dms = C.PrivateChannelSortStore.getPrivateChannelIds().slice(0, a.count).map(id => C.ChannelStore.getChannel(id))
      .filter(Boolean).map(c => ({name: title(c), group: c.type === 3 || undefined, unread: R.getUnreadCount(c.id) || undefined}));
    const mentions = Object.keys(C.GuildStore.getGuilds()).flatMap(channels).filter(c => R.getMentionCount(c.id))
      .map(c => ({name: title(c), mentions: R.getMentionCount(c.id)}));
    return {direct_messages: dms, server_mentions: mentions};
  }
  if (cmd === "targets") {
    const out = C.PrivateChannelSortStore.getPrivateChannelIds().map(id => C.ChannelStore.getChannel(id)).filter(Boolean)
      .map(c => ({id: c.id, name: title(c), also: c.type === 1 ? [C.UserStore.getUser(c.getRecipientId())?.username] : [], kind: "dm"}));
    for (const id of C.RelationshipStore.getFriendIDs()) {
      const u = C.UserStore.getUser(id);
      if (u && !C.ChannelStore.getDMFromUserId(id)) out.push({id, name: who(u), also: [u.username], kind: "friend"});
    }
    for (const g of Object.values(C.GuildStore.getGuilds())) {
      out.push({id: g.id, name: g.name, kind: "server"});
      for (const c of channels(g.id)) out.push({id: c.id, name: title(c), kind: "channel"});
    }
    return out;
  }
  if (cmd === "server") return channels(a.id).map(c => ({name: title(c),
    unread: (R.hasUnread(c.id) && !muted(c)) || undefined, mentions: R.getMentionCount(c.id) || undefined}));
  if (cmd === "history") {
    const id = chan();
    if (!id) return [];
    const g = C.ChannelStore.getChannel(id)?.guild_id;
    return (await recent(id)).reverse().map(m => ({id: m.id, me: m.author.id === me, by: who(m.author, g), text: text(m, g),
      at: Date.parse(m.timestamp) / 1000}));
  }
  if (cmd === "media") {  // the newest (or that) photo, voice message or audio in a chat: where to download it
    const id = chan(), g = C.ChannelStore.getChannel(id)?.guild_id;
    for (const m of id ? await recent(id) : []) {
      const f = (!a.msg || m.id === a.msg) && m.attachments.find(f => /^(image|audio)\//.test(f.content_type || ""));
      if (f) return {url: f.url, mime: f.content_type.split(";")[0], name: f.filename, id: m.id, me: m.author.id === me,
                     by: who(m.author, g), caption: m.content, at: Date.parse(m.timestamp) / 1000};
    }
    return null;
  }
  if (cmd === "react") {
    const id = chan(), m = id && await message(id, a.msg);
    if (!m) return {error: "no such message there"};
    await C.RestAPI.put({url: `/channels/${id}/messages/${m.id}/reactions/${encodeURIComponent(a.emoji)}/@me`});
    return {to: who(m.author), text: text(m)};
  }
  if (cmd === "waiting") {  // one-to-one DMs whose last message (in the last three days) isn't the user's
    const made = id => Number((BigInt(id) >> 22n) + 1420070400000n), recentEnough = id => made(id) > Date.now() - 3 * 86400e3;
    const chats = C.PrivateChannelSortStore.getPrivateChannelIds().slice(0, 30).map(id => C.ChannelStore.getChannel(id))
      .filter(c => c?.type === 1 && c.lastMessageId && recentEnough(c.lastMessageId) && !C.UserGuildSettingsStore.isChannelMuted(null, c.id));
    const last = await Promise.all(chats.map(async c => C.MessageStore.getMessage(c.id, c.lastMessageId)
      || (await C.RestAPI.get({url: `/channels/${c.id}/messages`, query: {limit: 1}})).body[0]));
    return chats.map((c, i) => ({c, m: last[i]})).filter(({m}) => m && m.author.id !== me)
      .map(({c, m}) => ({name: title(c), text: text(m), at: made(m.id) / 1000}));
  }
  if (cmd === "listen") {  // DMs and pings to the page binding jarvisDiscord, once (again after Discord reloads)
    if (window.__jarvisListen === a.v) return true;
    window.__jarvisOff?.();
    const on = e => { try {
      const m = e.message, c = C.ChannelStore.getChannel(e.channelId);
      if (e.optimistic || !m?.author || !c || !window.jarvisDiscord) return;
      const mine = m.author.id === me;
      if (c.guild_id ? mine || !(m.mentions || []).some(u => u.id === me) : C.MessageRequestStore.isMessageRequest(c.id)) return;
      window.jarvisDiscord(JSON.stringify({id: m.id, channel: c.id, chat: title(c), server: !!c.guild_id, group: c.type === 3,
        me: mine, from: who(m.author, c.guild_id), user: m.author.username, friend: C.RelationshipStore.isFriend(m.author.id),
        muted: !!muted(c), text: text(m, c.guild_id)}));
    } catch (err) { console.error("[jarvis]", err); } };
    C.FluxDispatcher.subscribe("MESSAGE_CREATE", on);
    window.__jarvisOff = () => C.FluxDispatcher.unsubscribe("MESSAGE_CREATE", on);
    window.__jarvisListen = a.v;
    return true;
  }
  if (cmd === "send") {
    const id = await dm(a.id), c = C.ChannelStore.getChannel(id);
    if (c?.guild_id && !C.PermissionStore.can(C.PermissionsBits.SEND_MESSAGES, c)) return {error: "the user can't write in that channel"};
    const to = a.reply ? await message(id, a.reply) : null;
    if (a.reply && !to) return {error: "no such message to reply to"};
    try {
      await C.MessageActions.sendMessage(id, {content: ping(a.text, c), tts: false, invalidEmojis: [], validNonShortcutEmojis: []}, undefined,
        to ? {messageReference: {channel_id: id, message_id: to.id, guild_id: c?.guild_id ?? undefined}} : {});
    } catch (e) { return {error: `Discord refused it (${e?.body?.message || e?.message || e})`}; }
    return to ? {replied_to: `${who(to.author)}: ${text(to)}`.slice(0, 200)} : {ok: true};
  }
  return {error: `unknown command ${cmd}`};
}"""


def _page():
    """The Discord window's debugger address, or a RuntimeError saying what the user can do."""
    try:
        pages = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list", timeout=3))
    except OSError:
        raise RuntimeError("Discord isn't connected: open Vesktop, or connect it in Settings → Discord" if system.vesktop()
                           else "Vesktop isn't running: start it (Jarvis uses Discord through Vesktop)") from None
    for p in pages:
        if p["type"] == "page" and "discord.com/" in p["url"] and "/popout" not in p["url"]:
            return p["webSocketDebuggerUrl"]
    raise RuntimeError("Discord is still starting")


def call(cmd, **args):
    from websockets.sync.client import connect
    with connect(_page(), max_size=None, open_timeout=5) as ws:
        ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {
            "expression": f"({JS})({json.dumps(cmd)}, {json.dumps(args)})", "awaitPromise": True, "returnByValue": True}}))
        while (m := json.loads(ws.recv(timeout=30))).get("id") != 1:
            pass
    r = m.get("result") or {}
    if "exceptionDetails" in r or "error" in m:
        raise RuntimeError(f"Discord: {(r.get('exceptionDetails') or {}).get('exception', {}).get('description') or m.get('error')}"[:300])
    v = r["result"].get("value")
    if isinstance(v, dict) and "error" in v:
        raise RuntimeError(v["error"])
    return v


def status():
    if not system.vesktop():
        return {"state": "off"}
    try:
        _page()
        return {"state": "connected"}
    except RuntimeError as e:
        return {"state": "starting" if "starting" in str(e) else "restart"}


def chats(count=15):
    return call("chats", count=min(int(count), 40))


def find(name):
    """The one DM, friend, server or channel by that name, or an error listing close ones."""
    return brain.pick(name, call("targets"))


def history(target, count=20):
    if target["kind"] == "server":
        return {"server": target["name"], "channels": call("server", id=target["id"]),
                "note": "read one with discord_read and its full name (Server #channel)"}
    return [{"id": m["id"], "from": "the user" if m["me"] else m["by"], "text": m["text"],
             "at": time.strftime("%a %d %b %H:%M", time.localtime(m["at"]))}
            for m in call("history", id=target["id"], kind=target["kind"], count=min(int(count), 50))]


def send(target, text, reply=""):
    """reply: a message id, or "last" (their newest message), to answer as a Discord reply."""
    return call("send", id=target["id"], kind=target["kind"], text=text, reply=reply)


def react(target, emoji, msg=""):
    return call("react", id=target["id"], kind=target["kind"], emoji=emoji, msg=msg)


def media(target, msg=""):
    """The newest (or that) photo or voice message in a chat, with its bytes as base64 (as WhatsApp.media); None if none."""
    m = call("media", id=target["id"], kind=target["kind"], msg=msg)
    if m:
        r = requests.get(m["url"], timeout=30, stream=True)
        r.raise_for_status()
        data = r.raw.read(MEDIA_LIMIT + 1, decode_content=True)
        if len(data) > MEDIA_LIMIT:
            raise RuntimeError("that file is too big to look at")
        m["data"] = base64.b64encode(data).decode()
        m["type"] = "image" if m["mime"].startswith("image/") else "audio"
    return m


class Listener:
    """Discord's new messages, as they come into Vesktop: direct messages and pings. The user's people rules (Settings →
    Discord, or "don't answer Sam" by voice) decide: "always" is said out loud (even in quiet hours) and never answered,
    "never" only goes in the chat. Muted chats stay quiet. With discord_replies on "friends", Jarvis answers a friend's
    DM that doesn't need the user, like WhatsApp's auto-replies and within the same limits (it's off by default:
    Discord bans accounts that act like bots)."""

    def __init__(self, brain, notify=print, tell=lambda text, **kw: print(text), wa=None):
        self.brain, self.notify, self.tell = brain, notify, tell
        self.wa = wa  # the WhatsApp link: what Jarvis tells people and the user's name are shared with it
        self.pending, self.user_wrote, self.replies = {}, {}, []
        self.mine = collections.deque(maxlen=200)  # (chat, text) Jarvis wrote on its own: not the user talking

    def run(self):
        from websockets.sync.client import connect
        version = hashlib.sha1(JS.encode()).hexdigest()[:12]
        while True:
            try:
                with connect(_page(), max_size=None, open_timeout=5) as ws:
                    ws.send(json.dumps({"id": 1, "method": "Runtime.addBinding", "params": {"name": "jarvisDiscord"}}))
                    print("[discord] listening for messages", flush=True)
                    while True:  # (the listener goes when Discord reloads: put it back every half minute)
                        ws.send(json.dumps({"id": 2, "method": "Runtime.evaluate", "params": {
                            "expression": f"({JS})('listen', {json.dumps({'v': version})})", "awaitPromise": True}}))
                        end = time.time() + 30
                        while (left := end - time.time()) > 0:
                            try:
                                m = json.loads(ws.recv(timeout=left))
                            except TimeoutError:
                                break
                            if m.get("method") == "Runtime.bindingCalled" and m["params"]["name"] == "jarvisDiscord":
                                threading.Thread(target=self.message, args=(json.loads(m["params"]["payload"]),), daemon=True).start()
            except Exception as e:  # Vesktop closed or restarting: wait for it
                if not isinstance(e, RuntimeError):
                    print(f"[discord] {e}", flush=True)
            time.sleep(10)

    def message(self, e):
        one = not (e["server"] or e["group"])  # (a person's page: one-to-one DMs only)
        if e["me"]:
            if (e["channel"], e["text"]) not in self.mine:
                self.user_wrote[e["channel"]] = time.time()
                self._cancel(e["channel"])
                if one:
                    people.talked(e["chat"], "discord", True)
                    people.tracker[0] and people.tracker[0].heard("discord", e["chat"], e["text"])
            return
        if one and e["friend"]:
            people.talked(e["from"], "discord", False, aka=e["user"])
        rule = whatsapp.contact_rule([e["from"], e["user"]], "discord")
        said = f"Discord from {e['from']}" + (f" in {e['chat']}" if e["server"] or e["group"] else "") + f": {e['text'][:300]}"
        if rule == "always":
            self.tell(said, loud=True)
            return
        if e["muted"] and rule != "never":
            return
        print(f"[discord] message from {e['from']}", flush=True)
        if rule == "never" or e["server"] or e["group"] or not e["friend"] or store.settings()["discord_replies"] != "friends":
            self.notify(f"💬 {said}")
            return
        self._cancel(e["channel"])
        timer = threading.Timer(whatsapp.SETTLE, self._answer, args=(e,))
        timer.daemon = True
        self.pending[e["channel"]] = timer
        timer.start()

    def _cancel(self, chat):
        timer = self.pending.pop(chat, None)
        if timer:
            timer.cancel()

    def _answer(self, e):
        chat, name = e["channel"], e["from"]
        self.pending.pop(chat, None)
        history = call("history", id=chat, kind="dm", count=20)
        said = " / ".join(m["text"] for m in [m for m in history if not m["me"]][-3:])[:300]
        if time.time() - self.user_wrote.get(chat, 0) < whatsapp.QUIET:
            self.notify(f"💬 Discord from {name}: {said} (you're chatting with them, so Jarvis left it)")
            return
        self.replies = [r for r in self.replies if r[0] > time.time() - 3600]
        if len(self.replies) >= whatsapp.REPLY_LIMIT or sum(c == chat for _, c in self.replies) >= whatsapp.CHAT_LIMIT:
            self.notify(f"💬 Discord from {name}: {said} (Jarvis has answered a lot this hour, so it left this one)")
            return
        me = self.wa._me() if self.wa else "the user"
        lines = "\n".join(f"{'Jarvis (you)' if (chat, m['text']) in self.mine else me if m['me'] else name}: {m['text'][:1000]}"
                          for m in history)
        decision = whatsapp.decide(self.brain, "Discord", me, name, lines, *((self.wa._note(), self.wa._free()) if self.wa else ()))
        reply, urgent = decision.get("reply", "").strip()[:LIMIT], decision.get("tell_user", "").strip()
        if reply:
            self.mine.append((chat, reply))
            call("send", id=chat, kind="dm", text=reply)
            self.replies.append((time.time(), chat))
        self.notify(f"💬 Discord from {name}: {said}" + (f"\nJarvis replied: {reply}" if reply else ""))
        if urgent:
            self.tell(f"Discord from {name}: {urgent}")
