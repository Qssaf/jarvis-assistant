// jarvis-wa: Jarvis's WhatsApp, as a linked device, without a browser. whatsapp.py starts it and talks JSON lines:
// commands on stdin ({"id": n, "cmd": ...}, answered {"id": n, "ok": ...} or {"id": n, "error": ...}; a command
// without an id gets no answer), events on stdout ({"ev": ...}); logs go to stderr. Messages go through whatsmeow and
// are kept in the same SQLite file as the login (whatsmeow keeps no history); calls through internal/voip (from WaCalls).
package main

import (
	"bufio"
	"context"
	"database/sql"
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"errors"
	"flag"
	"log/slog"
	"os"
	"strings"
	"sync"
	"time"

	"jarvis-wa/internal/voip/call"
	"jarvis-wa/internal/voip/core"
	"jarvis-wa/internal/voip/signaling"
	"jarvis-wa/internal/wa"

	"github.com/rs/zerolog"
	"go.mau.fi/whatsmeow"
	waBinary "go.mau.fi/whatsmeow/binary"
	"go.mau.fi/whatsmeow/proto/waE2E"
	"go.mau.fi/whatsmeow/proto/waHistorySync"
	"go.mau.fi/whatsmeow/store/sqlstore"
	"go.mau.fi/whatsmeow/types"
	"go.mau.fi/whatsmeow/types/events"
	waLog "go.mau.fi/whatsmeow/util/log"
	"google.golang.org/protobuf/proto"
	_ "modernc.org/sqlite"
)

const frame = 960 // samples per call audio frame (60 ms at 16 kHz)

var (
	cli    *whatsmeow.Client
	db     *sql.DB
	log    *slog.Logger
	outMu  sync.Mutex
	stdout = bufio.NewWriter(os.Stdout)

	callMu sync.Mutex
	calls  = map[string]*call.CallManager{}
	voice  []float32 // Jarvis's voice waiting to go into the call, 16 kHz (paced in real time by speak)

	synced = sync.NewCond(&sync.Mutex{}) // an on-demand history sync arrived
)

func emit(v map[string]any) {
	b, _ := json.Marshal(v)
	outMu.Lock()
	defer outMu.Unlock()
	stdout.Write(append(b, '\n'))
	stdout.Flush()
}

func main() {
	path := flag.String("db", "whatsapp.db", "the login and the messages")
	link := flag.Bool("link", false, "not linked yet: show QR codes until a phone links")
	flag.Parse()
	level := slog.LevelWarn // (JARVIS_WA_LOG=debug or info for more)
	level.UnmarshalText([]byte(os.Getenv("JARVIS_WA_LOG")))
	log = slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{Level: level}))
	waLevel, _ := zerolog.ParseLevel(strings.ToLower(level.String()))
	waLogger := waLog.Zerolog(zerolog.New(zerolog.ConsoleWriter{Out: os.Stderr, NoColor: true, PartsExclude: []string{zerolog.TimestampFieldName}}).Level(waLevel))
	ctx := context.Background()

	// (it holds the login's keys: owner only; SQLite gives the -wal and -shm files the database's permissions)
	f, err := os.OpenFile(*path, os.O_CREATE|os.O_RDONLY, 0o600)
	if err == nil {
		f.Close()
		err = os.Chmod(*path, 0o600)
	}
	if err != nil {
		fail("the database: " + err.Error())
	}
	db, err = sql.Open("sqlite", "file:"+*path+"?_pragma=foreign_keys(1)&_pragma=journal_mode(WAL)&_pragma=busy_timeout(5000)")
	if err == nil {
		_, err = db.Exec(`CREATE TABLE IF NOT EXISTS jarvis_msgs (chat TEXT, id TEXT, me INTEGER, sender TEXT, at INTEGER,
			text TEXT, kind TEXT, raw BLOB, PRIMARY KEY (chat, id));
			CREATE INDEX IF NOT EXISTS jarvis_msgs_at ON jarvis_msgs (chat, at);
			CREATE TABLE IF NOT EXISTS jarvis_chats (chat TEXT PRIMARY KEY, name TEXT, at INTEGER, unread INTEGER)`)
	}
	container := sqlstore.NewWithDB(db, "sqlite3", waLogger.Sub("db"))
	if err == nil {
		err = container.Upgrade(ctx)
	}
	if err != nil {
		fail("the database: " + err.Error())
	}
	device, err := container.GetFirstDevice(ctx)
	if err != nil {
		fail("the database: " + err.Error())
	}
	cli = whatsmeow.NewClient(device, waLogger)
	cli.AddEventHandler(handle)

	if cli.Store.ID == nil {
		if !*link {
			emit(map[string]any{"ev": "state", "state": "logged_out"})
			os.Exit(0)
		}
		qr, _ := cli.GetQRChannel(ctx)
		go func() {
			for item := range qr {
				switch item.Event {
				case "code":
					emit(map[string]any{"ev": "qr", "code": item.Code})
				case "success":
				default: // timeout, or the phone refused
					emit(map[string]any{"ev": "state", "state": "logged_out", "why": item.Event})
					os.Exit(0)
				}
			}
		}()
	}
	if err := cli.Connect(); err != nil {
		fail("connecting: " + err.Error())
	}
	go speak()
	commands() // until Jarvis closes stdin
	hangUpAll()
	cli.Disconnect()
}

func fail(why string) {
	emit(map[string]any{"ev": "error", "error": why})
	os.Exit(1)
}

// ---- events from WhatsApp

func handle(raw any) {
	switch e := raw.(type) {
	case *events.Connected:
		emit(map[string]any{"ev": "state", "state": "connected", "name": cli.Store.PushName})
	case *events.Disconnected, *events.KeepAliveTimeout:
		emit(map[string]any{"ev": "state", "state": "connecting"})
	case *events.LoggedOut:
		emit(map[string]any{"ev": "state", "state": "logged_out"})
	case *events.StreamReplaced:
		emit(map[string]any{"ev": "error", "error": "this WhatsApp login is in use somewhere else"})
	case *events.TemporaryBan:
		emit(map[string]any{"ev": "error", "error": "WhatsApp has banned this number for a while: " + e.String()})
	case *events.ClientOutdated:
		emit(map[string]any{"ev": "error", "error": "WhatsApp says this version is too old: Jarvis needs an update"})
	case *events.Message:
		chat := chatOf(e.Info.Chat)
		if !wanted(chat) {
			return
		}
		text, kind := describe(e.Message)
		if text == "" && kind == "" {
			return
		}
		save(chat, e)
		if !e.Info.IsGroup {
			emit(map[string]any{"ev": "msg", "id": e.Info.ID, "chat": chat.String(), "me": e.Info.IsFromMe, "text": text,
				"name": nameOf(chat), "contact": saved(chat)})
		}
	case *events.Receipt: // the user read a chat on another device
		if e.IsFromMe && e.Type == types.ReceiptTypeRead {
			db.Exec(`UPDATE jarvis_chats SET unread = 0 WHERE chat = ?`, chatOf(e.Chat).String())
		}
	case *events.HistorySync:
		history(e.Data)
	case *events.CallOffer:
		onOffer(e)
	case *events.UnknownCallEvent:
		log.Info("unknown call event", "node", e.Node.String())
	case *events.CallOfferNotice: // a group call: only told
		emit(map[string]any{"ev": "call", "id": e.CallID, "peer": e.From.String(), "name": nameOf(chatOf(e.From)),
			"contact": saved(chatOf(e.From)), "video": e.Media == "video", "group": true, "outgoing": false})
	case *events.CallAccept:
		onCall(e.CallID, func(m *call.CallManager, c *call.CallInfo) {
			if c.Direction == core.CallDirectionIncoming { // the user picked up on another device
				m.HandleCallTerminate(signalingNode(e.From, e.Data))
			} else {
				m.HandleCallAccept(context.Background(), signalingNode(e.From, e.Data), e.From)
			}
		})
	case *events.CallTransport:
		onCall(e.CallID, func(m *call.CallManager, _ *call.CallInfo) {
			m.HandleCallTransport(context.Background(), signalingNode(e.From, e.Data), e.From)
		})
	case *events.CallTerminate:
		onCall(e.CallID, func(m *call.CallManager, _ *call.CallInfo) { m.HandleCallTerminate(signalingNode(e.From, e.Data)) })
	case *events.CallReject:
		onCall(e.CallID, func(m *call.CallManager, _ *call.CallInfo) { m.HandleCallTerminate(signalingNode(e.From, e.Data)) })
	}
}

// chatOf: a chat by the contact's phone number where WhatsApp knows it (messages come from either), without a device
func chatOf(j types.JID) types.JID {
	j = j.ToNonAD()
	if j.Server == types.HiddenUserServer {
		if pn, err := cli.Store.LIDs.GetPNForLID(context.Background(), j); err == nil && !pn.IsEmpty() {
			return pn.ToNonAD()
		}
	}
	return j
}

func wanted(chat types.JID) bool {
	return chat.Server != types.BroadcastServer && chat.Server != types.NewsletterServer && !chat.IsEmpty()
}

func contactOf(j types.JID) types.ContactInfo {
	c, _ := cli.Store.Contacts.GetContact(context.Background(), j)
	return c
}

func saved(chat types.JID) bool { return contactOf(chat).FullName != "" } // (in the phone's address book)

func nameOf(chat types.JID) string {
	if chat.Server == types.GroupServer {
		var name string
		if db.QueryRow(`SELECT name FROM jarvis_chats WHERE chat = ?`, chat.String()).Scan(&name); name != "" {
			return name
		}
		if info, err := cli.GetGroupInfo(context.Background(), chat); err == nil {
			return info.Name
		}
		return chat.User
	}
	c := contactOf(chat)
	for _, n := range []string{c.FullName, c.FirstName, c.PushName, c.BusinessName} {
		if n != "" {
			return n
		}
	}
	return chat.User
}

// describe: a message as text ("[a photo] caption" for media), and its media kind; both "" for what isn't a message
// (reactions, edits, receipts...)
func describe(m *waE2E.Message) (string, string) {
	media := func(what, caption string) string {
		if caption != "" {
			return "[" + what + "] " + caption
		}
		return "[" + what + "]"
	}
	switch {
	case m == nil:
	case m.GetConversation() != "":
		return m.GetConversation(), ""
	case m.GetExtendedTextMessage() != nil:
		return m.GetExtendedTextMessage().GetText(), ""
	case m.GetImageMessage() != nil:
		return media("a photo", m.GetImageMessage().GetCaption()), "image"
	case m.GetAudioMessage() != nil:
		if m.GetAudioMessage().GetPTT() {
			return "[a voice message]", "ptt"
		}
		return "[an audio file]", "audio"
	case m.GetVideoMessage() != nil:
		if m.GetVideoMessage().GetGifPlayback() {
			return media("a GIF", m.GetVideoMessage().GetCaption()), "video"
		}
		return media("a video", m.GetVideoMessage().GetCaption()), "video"
	case m.GetPtvMessage() != nil:
		return "[a video message]", "video"
	case m.GetDocumentMessage() != nil:
		return media("a document", m.GetDocumentMessage().GetCaption()), "document"
	case m.GetStickerMessage() != nil:
		return "[a sticker]", "sticker"
	case m.GetLocationMessage() != nil || m.GetLiveLocationMessage() != nil:
		return "[a location]", "location"
	case m.GetContactMessage() != nil || m.GetContactsArrayMessage() != nil:
		return "[a contact card]", "vcard"
	}
	return "", ""
}

func save(chat types.JID, e *events.Message) {
	text, kind := describe(e.Message)
	var raw []byte
	if kind == "image" || kind == "audio" || kind == "ptt" { // (kept to download later)
		raw, _ = proto.Marshal(e.Message)
	}
	sender := ""
	if e.Info.IsGroup && !e.Info.IsFromMe {
		sender = chatOf(e.Info.Sender).String()
	}
	at := e.Info.Timestamp.Unix()
	r, err := db.Exec(`INSERT OR IGNORE INTO jarvis_msgs VALUES (?, ?, ?, ?, ?, ?, ?, ?)`, chat.String(), e.Info.ID,
		e.Info.IsFromMe, sender, at, text, kind, raw)
	if err != nil {
		log.Warn("saving a message", "err", err)
		return
	}
	if n, _ := r.RowsAffected(); n == 0 || e.SourceWebMsg != nil { // (history: its chat's unread count comes with it)
		db.Exec(`INSERT OR IGNORE INTO jarvis_chats VALUES (?, '', ?, 0)`, chat.String(), at)
		db.Exec(`UPDATE jarvis_chats SET at = max(at, ?) WHERE chat = ?`, at, chat.String())
		return
	}
	unread := 1
	if e.Info.IsFromMe {
		unread = 0
	}
	db.Exec(`INSERT INTO jarvis_chats VALUES (?, '', ?, ?) ON CONFLICT (chat) DO UPDATE SET at = max(at, excluded.at),
		unread = CASE WHEN ? THEN 0 ELSE unread + 1 END`, chat.String(), at, unread, e.Info.IsFromMe)
}

func history(h *waHistorySync.HistorySync) {
	for _, conv := range h.GetConversations() {
		j, err := types.ParseJID(conv.GetID())
		if err != nil {
			continue
		}
		chat := chatOf(j)
		if !wanted(chat) {
			continue
		}
		for _, m := range conv.GetMessages() {
			if e, err := cli.ParseWebMessage(j, m.GetMessage()); err == nil {
				if text, kind := describe(e.Message); text != "" || kind != "" {
					save(chat, e)
				}
			}
		}
		if h.GetSyncType() != waHistorySync.HistorySync_ON_DEMAND {
			db.Exec(`UPDATE jarvis_chats SET unread = ?, name = CASE WHEN ? != '' THEN ? ELSE name END WHERE chat = ?`,
				conv.GetUnreadCount(), conv.GetName(), conv.GetName(), chat.String())
		}
	}
	if h.GetSyncType() == waHistorySync.HistorySync_ON_DEMAND {
		synced.L.Lock()
		synced.Broadcast()
		synced.L.Unlock()
	}
}

// ---- commands from Jarvis

func commands() {
	in := bufio.NewScanner(os.Stdin)
	in.Buffer(make([]byte, 1<<20), 16<<20)
	for in.Scan() {
		var c map[string]any
		if json.Unmarshal(in.Bytes(), &c) != nil {
			continue
		}
		if c["cmd"] == "speak" || c["cmd"] == "hush" { // (in order, at once: call audio)
			run(c)
			continue
		}
		go run(c)
	}
}

func run(c map[string]any) {
	str := func(k string) string { s, _ := c[k].(string); return s }
	num := func(k string, def int) int {
		if f, ok := c[k].(float64); ok {
			return int(f)
		}
		return def
	}
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()
	var out any
	var err error
	switch str("cmd") {
	case "chats":
		out, err = chats(num("count", 10))
	case "history":
		out, err = messages(ctx, str("chat"), num("count", 15))
	case "media":
		out, err = mediaOf(ctx, str("chat"), str("msg"))
	case "send":
		out, err = send(ctx, str("chat"), str("text"))
	case "dial":
		out, err = dial(ctx, str("chat"))
	case "accept":
		err = withCall(str("call"), func(m *call.CallManager) error { return m.AcceptCall(ctx, str("call")) })
	case "decline": // (both send in the background: not with ctx, cancelled once this answers)
		err = withCall(str("call"), func(m *call.CallManager) error {
			return m.RejectCall(context.Background(), str("call"), core.EndCallReasonDeclined)
		})
	case "hangup":
		err = withCall(str("call"), func(m *call.CallManager) error {
			return m.EndCall(context.Background(), core.EndCallReasonUserEnded)
		})
	case "speak": // 16-bit mono PCM at "rate", queued after what's already waiting
		pcm, _ := base64.StdEncoding.DecodeString(str("pcm"))
		samples := resample(pcm, num("rate", 16000))
		callMu.Lock()
		voice = append(voice, samples...)
		callMu.Unlock()
	case "hush": // the caller talked over Jarvis
		callMu.Lock()
		voice = nil
		callMu.Unlock()
	case "logout":
		hangUpAll()
		err = cli.Logout(ctx)
	default:
		err = errors.New("unknown command")
	}
	if id, ok := c["id"]; ok {
		if err != nil {
			emit(map[string]any{"id": id, "error": err.Error()})
		} else {
			emit(map[string]any{"id": id, "ok": out})
		}
	}
}

func chats(n int) ([]map[string]any, error) {
	rows, err := db.Query(`SELECT chat, name, at, unread FROM jarvis_chats ORDER BY at DESC LIMIT ?`, n)
	if err != nil {
		return nil, err
	}
	type row struct {
		chat, name string
		at, unread int64
	}
	var all []row
	for rows.Next() {
		var r row
		rows.Scan(&r.chat, &r.name, &r.at, &r.unread)
		all = append(all, r)
	}
	rows.Close()
	out := []map[string]any{}
	for _, r := range all {
		j, err := types.ParseJID(r.chat)
		if err != nil {
			continue
		}
		group := j.Server == types.GroupServer
		last := ""
		var me bool
		var sender, text string
		if db.QueryRow(`SELECT me, sender, text FROM jarvis_msgs WHERE chat = ? ORDER BY at DESC LIMIT 1`, r.chat).
			Scan(&me, &sender, &text) == nil {
			switch {
			case me:
				last = "You: " + text
			case group && sender != "":
				last = senderName(sender) + ": " + text
			default:
				last = text
			}
		}
		out = append(out, map[string]any{"chat": r.chat, "name": nameOf(j), "unread": r.unread, "contact": !group && saved(j),
			"group": group, "last": last, "at": r.at})
	}
	return out, nil
}

func senderName(s string) string {
	if j, err := types.ParseJID(s); err == nil {
		return nameOf(j)
	}
	return s
}

// messages: a chat's last n messages, oldest first; with fewer here, the phone is asked for earlier ones (as opening
// the chat on WhatsApp Web does)
func messages(ctx context.Context, chat string, n int) ([]map[string]any, error) {
	read := func() ([]map[string]any, error) {
		rows, err := db.Query(`SELECT id, me, sender, text, at FROM (SELECT * FROM jarvis_msgs WHERE chat = ?
			ORDER BY at DESC LIMIT ?) ORDER BY at`, chat, n)
		if err != nil {
			return nil, err
		}
		defer rows.Close()
		out := []map[string]any{}
		for rows.Next() {
			var id, sender, text string
			var me bool
			var at int64
			rows.Scan(&id, &me, &sender, &text, &at)
			m := map[string]any{"id": id, "me": me, "text": text, "at": at, "by": nil}
			if sender != "" {
				m["by"] = senderName(sender)
			}
			out = append(out, m)
		}
		return out, nil
	}
	got, err := read()
	if err != nil || len(got) >= n || len(got) == 0 {
		return got, err
	}
	earlier(ctx, chat, got[0])
	return read()
}

func earlier(ctx context.Context, chat string, oldest map[string]any) {
	j, err := types.ParseJID(chat)
	if err != nil || cli.Store.ID == nil {
		return
	}
	info := &types.MessageInfo{MessageSource: types.MessageSource{Chat: j, IsFromMe: oldest["me"].(bool),
		IsGroup: j.Server == types.GroupServer}, ID: oldest["id"].(string), Timestamp: time.Unix(oldest["at"].(int64), 0)}
	if _, err := cli.SendPeerMessage(ctx, cli.BuildHistorySyncRequest(info, 50)); err != nil {
		return
	}
	done := make(chan struct{})
	go func() {
		synced.L.Lock()
		synced.Wait()
		synced.L.Unlock()
		close(done)
	}()
	select {
	case <-done:
	case <-time.After(10 * time.Second): // (the phone is offline, or it came before the wait began)
		synced.L.Lock()
		synced.Broadcast() // (lets the waiter go)
		synced.L.Unlock()
	}
}

// mediaOf: the newest (or that) voice message, audio or photo in a chat, decrypted, as base64; nil if there's none
func mediaOf(ctx context.Context, chat, id string) (map[string]any, error) {
	q := `SELECT id, me, sender, at, kind, raw FROM jarvis_msgs WHERE chat = ? AND kind IN ('image', 'audio', 'ptt')`
	args := []any{chat}
	if id != "" {
		q += ` AND id = ?`
		args = append(args, id)
	}
	var me bool
	var sender, kind string
	var at int64
	var raw []byte
	err := db.QueryRow(q+` ORDER BY at DESC LIMIT 1`, args...).Scan(&id, &me, &sender, &at, &kind, &raw)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	} else if err != nil {
		return nil, err
	}
	m := &waE2E.Message{}
	if err := proto.Unmarshal(raw, m); err != nil {
		return nil, err
	}
	var size uint64
	var mime, caption string
	switch {
	case m.GetImageMessage() != nil:
		size, mime, caption = m.GetImageMessage().GetFileLength(), m.GetImageMessage().GetMimetype(), m.GetImageMessage().GetCaption()
	case m.GetAudioMessage() != nil:
		size, mime = m.GetAudioMessage().GetFileLength(), m.GetAudioMessage().GetMimetype()
	}
	if size > 15e6 {
		return map[string]any{"error": "too big"}, nil
	}
	data, err := cli.DownloadAny(ctx, m)
	if err != nil {
		return map[string]any{"error": "not downloaded: " + err.Error()}, nil
	}
	by := any(nil)
	if !me {
		by = senderName(chat)
		if sender != "" {
			by = senderName(sender)
		}
	}
	return map[string]any{"id": id, "type": kind, "mime": strings.Split(mime, ";")[0], "at": at, "caption": caption,
		"by": by, "me": me, "data": base64.StdEncoding.EncodeToString(data)}, nil
}

func send(ctx context.Context, chat, text string) (string, error) {
	j, err := types.ParseJID(chat)
	if err != nil {
		return "", err
	}
	msg := &waE2E.Message{Conversation: proto.String(text)}
	r, err := cli.SendMessage(ctx, j, msg)
	if err != nil {
		return "", err
	}
	info := types.MessageInfo{MessageSource: types.MessageSource{Chat: j, IsFromMe: true, IsGroup: j.Server == types.GroupServer},
		ID: r.ID, Timestamp: r.Timestamp}
	save(j, &events.Message{Info: info, Message: msg})
	return r.ID, nil
}

// ---- calls

func newCall(id string) *call.CallManager {
	m := call.NewCallManager(wa.NewSocket(cli), log)
	m.OnStateChange = func(c *call.CallInfo) {
		state := "ringing"
		switch c.StateData.State {
		case core.CallStateActive:
			state = "active"
		case core.CallStateEnded: // (however it ended: hung up, declined, answered on the phone)
			state = "over"
			callMu.Lock()
			delete(calls, c.CallID)
			voice = nil
			callMu.Unlock()
		}
		emit(map[string]any{"ev": "callstate", "call": c.CallID, "state": state})
	}
	m.OnPeerAudio = func(pcm []float32) {
		b := make([]byte, 2*len(pcm))
		for i, s := range pcm {
			binary.LittleEndian.PutUint16(b[2*i:], uint16(int16(max(-1, min(1, s))*32767)))
		}
		emit(map[string]any{"ev": "audio", "call": id, "pcm": base64.StdEncoding.EncodeToString(b)})
	}
	callMu.Lock()
	calls[id] = m
	callMu.Unlock()
	return m
}

func onOffer(e *events.CallOffer) {
	log.Info("call offer", "from", e.From, "id", e.CallID)
	node := signalingNode(e.From, e.Data)
	m := newCall(e.CallID)
	m.HandleCallOffer(context.Background(), node, e.From)
	c := m.CurrentCall()
	if c == nil {
		log.Warn("a call offer that couldn't be read", "node", e.Data.String())
		return
	}
	peer := chatOf(e.From)
	emit(map[string]any{"ev": "call", "id": e.CallID, "peer": peer.String(), "name": nameOf(peer), "contact": saved(peer),
		"video": c.MediaType == core.CallMediaTypeVideo, "group": false, "outgoing": false})
}

func onCall(id string, fn func(*call.CallManager, *call.CallInfo)) {
	callMu.Lock()
	m := calls[id]
	callMu.Unlock()
	if m != nil {
		if c := m.CurrentCall(); c != nil {
			fn(m, c)
		}
	}
}

func withCall(id string, fn func(*call.CallManager) error) error {
	callMu.Lock()
	m := calls[id]
	callMu.Unlock()
	if m == nil {
		return errors.New("that call is over")
	}
	return fn(m)
}

func dial(ctx context.Context, chat string) (map[string]any, error) {
	j, err := types.ParseJID(chat)
	if err != nil {
		return nil, err
	}
	id := signaling.GenerateCallID()
	if err := newCall(id).StartCall(ctx, id, j, false); err != nil {
		callMu.Lock()
		delete(calls, id)
		callMu.Unlock()
		return nil, err
	}
	return map[string]any{"id": id}, nil
}

func hangUpAll() {
	callMu.Lock()
	all := make([]*call.CallManager, 0, len(calls))
	for _, m := range calls {
		all = append(all, m)
	}
	callMu.Unlock()
	for _, m := range all {
		m.EndCall(context.Background(), core.EndCallReasonUserEnded)
	}
}

// signalingNode: whatsmeow's call event as the <call> stanza it came in (what internal/voip reads)
func signalingNode(from types.JID, data *waBinary.Node) *waBinary.Node {
	node := &waBinary.Node{Tag: "call", Attrs: waBinary.Attrs{"from": from}, Content: []waBinary.Node{}}
	if data != nil {
		node.Content = []waBinary.Node{*data}
	}
	return node
}

// speak: Jarvis's voice into the call in real time, a frame every 60 ms (Gemini sends it faster than it's spoken; the
// call keeps itself alive with silence in between)
func speak() {
	tick := time.NewTicker(frame * time.Second / 16000)
	for range tick.C {
		callMu.Lock()
		if len(voice) == 0 {
			callMu.Unlock()
			continue
		}
		n := min(frame, len(voice))
		chunk := make([]float32, frame)
		copy(chunk, voice[:n])
		voice = voice[n:]
		all := make([]*call.CallManager, 0, 1)
		for _, m := range calls {
			all = append(all, m)
		}
		callMu.Unlock() // (before CurrentCall: a call's state change takes its own lock, then callMu)
		for _, m := range all {
			if c := m.CurrentCall(); c != nil && c.IsActive() {
				m.FeedCapturedPCM(chunk)
			}
		}
	}
}

// resample: 16-bit mono PCM at rate to float32 at 16 kHz (linear: speech, not music)
func resample(pcm []byte, rate int) []float32 {
	in := make([]float32, len(pcm)/2)
	for i := range in {
		in[i] = float32(int16(binary.LittleEndian.Uint16(pcm[2*i:]))) / 32768
	}
	if rate == 16000 || rate <= 0 || len(in) == 0 {
		return in
	}
	out := make([]float32, len(in)*16000/rate)
	step := float64(rate) / 16000
	for i := range out {
		x := float64(i) * step
		j := int(x)
		f := float32(x - float64(j))
		next := in[min(j+1, len(in)-1)]
		out[i] = in[j]*(1-f) + next*f
	}
	return out
}
