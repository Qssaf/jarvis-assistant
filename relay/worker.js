// Jarvis's private relay: the PC and the phone both dial out to it, so nothing on the PC is open to the internet. It
// only forwards encrypted frames between them (the keys live on the PC and the phone, never here). One Durable Object
// per PC; the PC proves who it is by signing the time with its key, so nobody else can take its place. Between the
// relay and the PC, a binary frame is a phone's 36-character connection id followed by its bytes; text frames say a
// phone came or went.
const enc = new TextEncoder()
const b64url = bytes => btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
const unb64url = s => Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0))
const MAX_PHONES = 8

async function hostAllowed(url) {
  const id = url.searchParams.get('id'), pub = url.searchParams.get('pub'), ts = Number(url.searchParams.get('ts'))
  const sig = url.searchParams.get('sig')
  if (!id || !pub || !sig || !(Math.abs(Date.now() - ts) < 300_000)) return false
  try {
    const raw = unb64url(pub)
    if (b64url(await crypto.subtle.digest('SHA-256', raw)) !== id) return false  // the id is the key's hash
    const key = await crypto.subtle.importKey('raw', raw, { name: 'ECDSA', namedCurve: 'P-256' }, false, ['verify'])
    return await crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }, key, unb64url(sig), enc.encode(`jarvis-relay:${id}:${ts}`))
  } catch {
    return false
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url)
    if (request.headers.get('Upgrade') !== 'websocket' || !['/host', '/phone'].includes(url.pathname))
      return new Response('Jarvis relay', { status: url.pathname === '/' ? 200 : 404 })
    const id = url.searchParams.get('id') || ''
    if (!/^[\w-]{43}$/.test(id)) return new Response('bad id', { status: 400 })
    if (url.pathname === '/host' && !(await hostAllowed(url))) return new Response('not allowed', { status: 403 })
    return env.ROOMS.get(env.ROOMS.idFromName(id)).fetch(request)
  },
}

export class Room {
  constructor(state) {
    this.state = state
  }

  host(except) {
    return this.state.getWebSockets('host').find(ws => ws !== except)
  }

  phones(except) {
    return this.state.getWebSockets('phone').filter(ws => ws !== except)
  }

  async fetch(request) {
    const [client, server] = Object.values(new WebSocketPair())
    if (new URL(request.url).pathname === '/host') {
      for (const old of this.state.getWebSockets('host')) old.close(4001, 'another connection took over')
      this.state.acceptWebSocket(server, ['host'])
      for (const phone of this.phones()) {
        phone.send(JSON.stringify({ t: 'host', up: true }))  // (the phone starts its handshake over)
        server.send(JSON.stringify({ t: 'open', c: phone.deserializeAttachment().c }))
      }
    } else {
      if (this.phones().length >= MAX_PHONES) return new Response('too many phones', { status: 429 })
      const c = crypto.randomUUID()
      server.serializeAttachment({ c })
      this.state.acceptWebSocket(server, ['phone', `c:${c}`])
      server.send(JSON.stringify({ t: 'host', up: !!this.host() }))
      this.host()?.send(JSON.stringify({ t: 'open', c }))
    }
    return new Response(null, { status: 101, webSocket: client })
  }

  webSocketMessage(ws, message) {
    if (this.state.getTags(ws).includes('host')) {
      if (typeof message === 'string') {
        let m
        try {
          m = JSON.parse(message)
        } catch {
          return
        }
        if (m.t === 'close') this.state.getWebSockets(`c:${m.c}`)[0]?.close(1000, 'closed by the PC')
      } else if (message.byteLength > 36) {
        const c = new TextDecoder().decode(message.slice(0, 36))
        this.state.getWebSockets(`c:${c}`)[0]?.send(message.slice(36))
      }
    } else if (typeof message !== 'string') {  // phones only send encrypted (binary) frames
      const frame = new Uint8Array(36 + message.byteLength)
      frame.set(enc.encode(ws.deserializeAttachment().c))
      frame.set(new Uint8Array(message), 36)
      this.host()?.send(frame)
    }
  }

  webSocketClose(ws, code) {
    if (this.state.getTags(ws).includes('host')) {
      if (!this.host(ws)) for (const phone of this.phones()) phone.send(JSON.stringify({ t: 'host', up: false }))
    } else {
      this.host()?.send(JSON.stringify({ t: 'close', c: ws.deserializeAttachment().c }))
    }
    try {
      ws.close(code === 1005 ? 1000 : code)
    } catch {}
  }

  webSocketError(ws) {
    this.webSocketClose(ws, 1011)
  }
}
