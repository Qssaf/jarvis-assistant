# jarvis-wa

Jarvis's WhatsApp without a browser (~30 MB instead of ~1 GB of headless Chromium). `whatsapp.py` starts it and talks
JSON lines with it (see `main.go`'s top comment). Messages use [whatsmeow](https://github.com/tulir/whatsmeow).

`internal/` is the call code of [WaCalls](https://github.com/JotaDev66/WaCalls) (MIT, `LICENSE.WaCalls`) at
edeb31f, its MLow codec a port of [whatsapp-rust](https://github.com/oxidezap/whatsapp-rust)'s
(MIT, `internal/voip/media/mlow/LICENSE`). Changes from upstream:
- received packets are decoded once: every relay forwards the same ones, and they were played twice;
- the SRTP rollover counter is guessed from the newest packet (RFC 3711), not the last one: a late packet from before
  a sequence wrap-around moved it back, garbling the rest of the call;
- one received packet at a time: each relay delivers on its own goroutine, and both used the same decoder at once;
- its tests that need the upstream test vectors (6 MB) are left out, and the files are gofmt'ed.

Build: `go build -trimpath -ldflags="-s -w" -o jarvis-wa .` (Jarvis also builds it itself when it's missing or older
than this source).
