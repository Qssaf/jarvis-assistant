package media

import "testing"

// Every relay forwards the same packets: each must be decoded once, and a late one from before a sequence wrap-around
// must not move the rollover counter back for what follows.
func TestRecvDedupAndRollover(t *testing.T) {
	c := &SrtpContext{}
	take := func(seq uint16) (uint64, bool) {
		i := c.recvIndex(seq)
		return i, c.fresh(i)
	}
	if _, ok := take(65534); !ok {
		t.Fatal("first packet dropped")
	}
	if _, ok := take(65534); ok {
		t.Fatal("a duplicate went through")
	}
	if i, ok := take(1); !ok || i != 1<<16|1 {
		t.Fatalf("after the wrap: index %d, fresh %v", i, ok)
	}
	if i, ok := take(65535); !ok || i != 65535 {
		t.Fatalf("a late packet from before the wrap: index %d, fresh %v", i, ok)
	}
	if i, ok := take(2); !ok || i != 1<<16|2 {
		t.Fatalf("the late packet moved the rollover counter: index %d", i)
	}
	if _, ok := take(1); ok {
		t.Fatal("a duplicate after the wrap went through")
	}
}
