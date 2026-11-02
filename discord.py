"""Jarvis on the user's own Discord, through Vesktop (Discord with Vencord built in): Jarvis reads and sends messages
inside the running client, through Chromium's debugging port (Vesktop started with PORT, see system.restart_vesktop),
using the stores Vencord exposes (Vencord.Webpack.Common). It's the user's own client doing what they'd do by hand:
no bot, no token copied out, nothing on screen. The port only listens on 127.0.0.1, and it gives what the user's
files already do (the login sits in Vesktop's folder): anything running as the user can use it.

Not an official API: Discord bans accounts that act like bots, so Jarvis only sends what the user asked for."""
import json, time, urllib.request

import brain
import system

PORT = 47652
FLAG = f"--remote-debugging-port={PORT}"
LIMIT = 2000  # characters in one Discord message (without Nitro)

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
    const id = a.kind === "friend" ? C.ChannelStore.getDMFromUserId(a.id) : a.id;
    if (!id) return [];
    const g = C.ChannelStore.getChannel(id)?.guild_id;
    const r = await C.RestAPI.get({url: `/channels/${id}/messages`, query: {limit: a.count}});
    return r.body.reverse().map(m => ({me: m.author.id === me, by: who(m.author, g), text: text(m, g), at: Date.parse(m.timestamp) / 1000}));
  }
  if (cmd === "send") {
    const id = await dm(a.id), c = C.ChannelStore.getChannel(id);
    if (c?.guild_id && !C.PermissionStore.can(C.PermissionsBits.SEND_MESSAGES, c)) return {error: "the user can't write in that channel"};
    try {
      await C.MessageActions.sendMessage(id, {content: ping(a.text, c), tts: false, invalidEmojis: [], validNonShortcutEmojis: []}, undefined, {});
    } catch (e) { return {error: `Discord refused it (${e?.body?.message || e?.message || e})`}; }
    return {ok: true};
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
    return [{"from": "the user" if m["me"] else m["by"], "text": m["text"], "at": time.strftime("%a %d %b %H:%M", time.localtime(m["at"]))}
            for m in call("history", id=target["id"], kind=target["kind"], count=min(int(count), 50))]


def send(target, text):
    call("send", id=target["id"], kind=target["kind"], text=text)
