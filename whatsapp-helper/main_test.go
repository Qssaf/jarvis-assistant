package main

import (
	"encoding/binary"
	"testing"

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
		{&waE2E.Message{ReactionMessage: &waE2E.ReactionMessage{}}, "", ""}, // (not a message to answer)
	} {
		if text, kind := describe(c.m); text != c.text || kind != c.kind {
			t.Errorf("%v: got %q %q", c.m, text, kind)
		}
	}
}
