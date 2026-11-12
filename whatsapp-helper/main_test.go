package main

import (
	"database/sql"
	"encoding/binary"
	"testing"

	"go.mau.fi/whatsmeow/types"

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
