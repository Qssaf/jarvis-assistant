package main

import (
	"database/sql"
	"encoding/binary"
	"strconv"
	"testing"

	"go.mau.fi/whatsmeow/types"
	"go.mau.fi/whatsmeow/types/events"

	"go.mau.fi/whatsmeow/proto/waE2E"
	"google.golang.org/protobuf/proto"
)

func TestResample(t *testing.T) {
	pcm := make([]byte, 2*2400) // 100 ms at 24 kHz, a constant level
	for i := 0; i < 2400; i++ {
		binary.LittleEndian.PutUint16(pcm[2*i:], uint16(16384))
	}
	out := resample(pcm, 24000)
	if len(out) != 1600 {
		t.Fatalf("100 ms at 16 kHz is 1600 samples, got %d", len(out))
	}
	if out[0] != 0.5 || out[1599] != 0.5 {
		t.Fatalf("level changed: %v %v", out[0], out[1599])
	}
}

func TestDescribe(t *testing.T) {
	for _, c := range []struct {
		m          *waE2E.Message
		text, kind string
	}{
		{&waE2E.Message{Conversation: proto.String("hi")}, "hi", ""},
		{&waE2E.Message{ImageMessage: &waE2E.ImageMessage{Caption: proto.String("look")}}, "[a photo] look", "image"},
		{&waE2E.Message{AudioMessage: &waE2E.AudioMessage{PTT: proto.Bool(true)}}, "[a voice message]", "ptt"},
		{&waE2E.Message{DocumentMessage: &waE2E.DocumentMessage{Caption: proto.String("the schedule")}}, "[a document] the schedule", "document"},
		{&waE2E.Message{ReactionMessage: &waE2E.ReactionMessage{}}, "", ""}, // (not a message to answer)
	} {
		if text, kind := describe(c.m); text != c.text || kind != c.kind {
			t.Errorf("%v: got %q %q", c.m, text, kind)
		}
	}
	// a document can be fetched later, like a photo or a voice message (it couldn't: "unable to download the schedule")
	for kind, want := range map[string]bool{"document": true, "image": true, "ptt": true, "audio": true, "video": false, "": false} {
		if kept(kind) != want {
			t.Errorf("kept(%q) = %v", kind, !want)
		}
	}
}

// a call that only rang is in its chat's history (once), and the chat exists even for a number that never wrote
func TestRang(t *testing.T) {
	db, _ = sql.Open("sqlite", ":memory:")
	db.SetMaxOpenConns(1) // (each connection to :memory: is its own database)
	defer db.Close()
	if _, err := db.Exec(schema); err != nil {
		t.Fatal(err)
	}
	peer := types.NewJID("15550100", types.DefaultUserServer)
	rang(peer, "c1", false)
	rang(peer, "c1", false)
	rang(peer, "c2", true)
	var n, chats int
	var text string
	db.QueryRow(`SELECT count(*), max(text) FROM jarvis_msgs WHERE chat = ? AND me = 0`, peer.String()).Scan(&n, &text)
	db.QueryRow(`SELECT count(*) FROM jarvis_chats WHERE chat = ?`, peer.String()).Scan(&chats)
	if n != 2 || chats != 1 || text != "[a WhatsApp video call]" {
		t.Errorf("calls kept: %d rows, %d chats, %q", n, chats, text)
	}
}

func TestSearch(t *testing.T) {
	db, _ = sql.Open("sqlite", ":memory:")
	db.SetMaxOpenConns(1)
	defer db.Close()
	if _, err := db.Exec(schema); err != nil {
		t.Fatal(err)
	}
	group := types.NewJID("120363000000", types.GroupServer)
	db.Exec(`INSERT INTO jarvis_chats VALUES (?, 'Trip planning', 3, 0)`, group.String())
	for i, text := range []string{"The TRIP is on Friday", "trip: bring 100% of the snacks", "no plans", "[a WhatsApp call] trip"} {
		kind := "text"
		if i == 3 {
			kind = "call"
		}
		db.Exec(`INSERT INTO jarvis_msgs VALUES (?, ?, 1, '', ?, ?, ?, NULL)`, group.String(), strconv.Itoa(i), i, text, kind)
	}
	got, err := search("trip", 10)
	if err != nil || len(got) != 2 || got[0]["text"] != "trip: bring 100% of the snacks" || got[0]["name"] != "Trip planning" {
		t.Fatalf("search trip: %v %v", got, err)
	}
	if got, _ := search("100% snacks", 10); len(got) != 1 {
		t.Errorf("every word, %% taken literally: %v", got)
	}
	if got, _ := search("trip_", 10); len(got) != 0 {
		t.Errorf("_ is a letter, not a wildcard: %v", got)
	}
}

// a group with no name saved is asked of WhatsApp once, not at every list of chats (a round trip per group each time:
// a list of 500 held the offline lookup past its 10 s), and a rename WhatsApp tells of is kept
func TestGroupNameOnce(t *testing.T) {
	db, _ = sql.Open("sqlite", ":memory:")
	db.SetMaxOpenConns(1)
	defer db.Close()
	if _, err := db.Exec(schema); err != nil {
		t.Fatal(err)
	}
	group := types.NewJID("120363000001", types.GroupServer)
	db.Exec(`INSERT INTO jarvis_chats VALUES (?, '', 3, 0)`, group.String())
	asked, real := 0, groupName
	defer func() { groupName = real }()
	groupName = func(types.JID) string { asked++; return "Trip planning" }
	for i := 0; i < 3; i++ {
		if got := nameOf(group); got != "Trip planning" {
			t.Fatalf("named %q", got)
		}
	}
	if asked != 1 {
		t.Errorf("WhatsApp was asked %d times", asked)
	}
	handle(&events.GroupInfo{JID: group, Name: &types.GroupName{Name: "Trip, the sequel"}})
	if got := nameOf(group); got != "Trip, the sequel" {
		t.Errorf("after the rename: %q", got)
	}
	groupName = real // (not logged in, as here: WhatsApp isn't asked, and the number stands in)
	other := types.NewJID("120363000002", types.GroupServer)
	if got := nameOf(other); got != other.User {
		t.Errorf("logged out: %q", got)
	}
}
