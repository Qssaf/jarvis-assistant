package transport

import (
	"sync"
	"testing"

	"github.com/pion/webrtc/v4"
)

// a relay's state, data channel and SSRCs are used from pion's callbacks, timers and the call's media goroutine at once
// (a new peer SSRC is set while subscriptions go out): every access goes through m.mu. Run with -race to see one that
// doesn't.
func TestRelayFieldsLocked(t *testing.T) {
	pc, err := webrtc.NewPeerConnection(webrtc.Configuration{})
	if err != nil {
		t.Fatal(err)
	}
	defer pc.Close()
	channel, err := pc.CreateDataChannel("test", nil)
	if err != nil {
		t.Fatal(err)
	}
	m := NewSctpRelayManager(nil)
	conn := &relayConnection{state: relayStateOpen, id: "r1", channel: channel, stopCh: make(chan struct{})}
	m.connections["r1"] = conn
	var wg sync.WaitGroup
	wg.Add(2)
	go func() {
		defer wg.Done()
		for i := 1; i <= 200; i++ {
			m.SetSsrc(uint32(i))
			m.SetSubscriptionSsrc(uint32(i))
			m.sendRaw(conn, []byte{0})
		}
	}()
	go func() {
		defer wg.Done()
		m.failConnection(conn)
		m.Cleanup()
	}()
	wg.Wait()
	if m.HasConnection() {
		t.Error("the failed relay is still counted")
	}
}
