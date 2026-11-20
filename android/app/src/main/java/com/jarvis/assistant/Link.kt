package com.jarvis.assistant

import android.content.SharedPreferences
import android.os.Build
import android.os.Handler
import android.os.Looper
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.Dns
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import okio.ByteString.Companion.toByteString
import org.json.JSONArray
import org.json.JSONObject
import java.math.BigInteger
import java.security.KeyFactory
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.interfaces.ECPublicKey
import java.security.spec.ECGenParameterSpec
import java.security.spec.ECPoint
import java.security.spec.ECPublicKeySpec
import java.util.Base64
import java.util.concurrent.TimeUnit
import javax.crypto.Cipher
import javax.crypto.KeyAgreement
import javax.crypto.Mac
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

/** The same handshake and frames as phone.py on the PC (see there): the PC proves itself with its long-term key from
 *  the pairing code, and every frame after is AES-GCM with a counter for its nonce. */
object Crypto {
    const val HELLO: Byte = 1
    const val WELCOME: Byte = 2
    const val DATA: Byte = 3

    fun fresh(): KeyPair = KeyPairGenerator.getInstance("EC").apply { initialize(ECGenParameterSpec("secp256r1")) }.generateKeyPair()

    fun raw(key: ECPublicKey): ByteArray = byteArrayOf(4) + fixed(key.w.affineX) + fixed(key.w.affineY)

    private fun fixed(n: BigInteger): ByteArray = n.toByteArray().takeLast(32).toByteArray().let { ByteArray(32 - it.size) + it }

    fun point(raw: ByteArray, like: ECPublicKey): ECPublicKey = KeyFactory.getInstance("EC").generatePublic(ECPublicKeySpec(
        ECPoint(BigInteger(1, raw.copyOfRange(1, 33)), BigInteger(1, raw.copyOfRange(33, 65))), like.params)) as ECPublicKey

    fun ecdh(own: KeyPair, peer: ECPublicKey): ByteArray =
        KeyAgreement.getInstance("ECDH").run { init(own.private); doPhase(peer, true); generateSecret() }

    private fun hmac(key: ByteArray, data: ByteArray): ByteArray = Mac.getInstance("HmacSHA256").run { init(SecretKeySpec(key, "HmacSHA256")); doFinal(data) }

    fun hkdf(ikm: ByteArray, salt: ByteArray, info: ByteArray): ByteArray {  // 64 bytes
        val prk = hmac(salt, ikm)
        val t1 = hmac(prk, info + 1.toByte())
        return t1 + hmac(prk, t1 + info + 2.toByte())
    }

    fun gcm(mode: Int, key: ByteArray, counter: Long, data: ByteArray): ByteArray = Cipher.getInstance("AES/GCM/NoPadding").run {
        init(mode, SecretKeySpec(key, "AES"), GCMParameterSpec(128, ByteArray(4) + BigInteger.valueOf(counter).toByteArray().let { ByteArray(8 - it.size) + it }))
        doFinal(data)
    }

    /** The phone's side of the handshake, once the PC's welcome came: the PC's fresh key, then its sealed proof. */
    fun finish(own: KeyPair, pcKey: ByteArray, welcome: ByteArray): Channel {
        require(welcome.size > 66 && welcome[0] == WELCOME) { "not a welcome" }
        val like = own.public as ECPublicKey
        val pcFresh = welcome.copyOfRange(1, 66)
        val keys = hkdf(ecdh(own, point(pcKey, like)) + ecdh(own, point(pcFresh, like)), raw(like) + pcFresh, "jarvis-relay-v1".toByteArray())
        val toPc = keys.copyOfRange(0, 32)
        val toPhone = keys.copyOfRange(32, 64)
        require(String(gcm(Cipher.DECRYPT_MODE, toPhone, 0, welcome.copyOfRange(66, welcome.size))) == "jarvis") { "not your PC" }
        return Channel(toPc, toPhone)
    }
}

class Channel(private val sendKey: ByteArray, private val receiveKey: ByteArray) {
    private var sent = 0L
    private var got = 1L  // (the PC's frame 0 was its proof in the welcome)

    fun seal(message: JSONObject): ByteArray = byteArrayOf(Crypto.DATA) + Crypto.gcm(Cipher.ENCRYPT_MODE, sendKey, sent++, message.toString().toByteArray())

    fun open(frame: ByteArray): JSONObject {
        require(frame.isNotEmpty() && frame[0] == Crypto.DATA) { "not a data frame" }
        return JSONObject(String(Crypto.gcm(Cipher.DECRYPT_MODE, receiveKey, got++, frame.copyOfRange(1, frame.size))))
    }
}

/** The pairing code from the PC's Settings: jarvis://pair#<base64url JSON {v, r: relay or "", s: PC id, k: PC key,
 *  p: secret, d: ["ip:port", ...] where the PC listens on its own networks}>. */
data class Pairing(val relay: String, val pc: String, val key: String, val secret: String, val direct: List<String> = emptyList()) {
    companion object {
        fun parse(link: String): Pairing? = try {
            val j = JSONObject(String(Base64.getUrlDecoder().decode(link.trim().substringAfter("#"))))
            Pairing(j.optString("r"), j.getString("s"), j.getString("k"), j.getString("p"), addresses(j.optJSONArray("d"))).takeIf { it.sound() }
        } catch (e: Exception) {
            null
        }

        /** The "ip:port" entries the app could really dial (a list from the PC, or from a link any web page made). */
        fun addresses(list: JSONArray?): List<String> = (0 until (list?.length() ?: 0)).map { list!!.optString(it) }
            .filter { Regex("[\\w.-]{1,253}:\\d{1,5}").matches(it) && "http://$it/".toHttpUrlOrNull() != null }.take(6)
    }

    /** Any web page can open a jarvis://pair link: one with a relay address OkHttp can't use or a key that isn't a P-256
     *  point was saved, and the app crashed connecting to it at every start. A link needs a way to the PC: its relay,
     *  or an address on its own network. */
    private fun sound(): Boolean =
        (if (relay.isEmpty()) direct.isNotEmpty() else relay.startsWith("ws") && relay.replaceFirst("ws", "http").toHttpUrlOrNull() != null) &&
        Regex("[\\w-]{43}").matches(pc) && secret.isNotBlank() &&
        runCatching { Base64.getUrlDecoder().decode(key) }.getOrNull()?.let { it.size == 65 && it[0] == 4.toByte() } == true
}

enum class State { UNPAIRED, CONNECTING, ONLINE, PC_OFFLINE, NO_RELAY }

/** The connection to the PC, kept up while the app or its service runs. Every way to the PC is tried at once: its
 *  addresses on its own networks (the same Wi-Fi, a VPN) and the relay; a direct one wins when it answers. */
class Link(private val prefs: SharedPreferences, private val onState: (State, String) -> Unit, private val onMessage: (JSONObject) -> Unit,
           private val waiting: () -> List<Int> = { emptyList() }) {
    // (a write may wait 30 s: a phone's internet stalled for seconds at a time and the link dropped at the default 10 s;
    // the pings still find a connection that's really gone)
    private val http = OkHttpClient.Builder().pingInterval(25, TimeUnit.SECONDS).connectTimeout(6, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS).dns(KeptDns()).build()
    private val main = Handler(Looper.getMainLooper())

    private class Try(val direct: Boolean) {
        var ws: WebSocket? = null
        var finish: ((ByteArray) -> Channel)? = null
        var channel: Channel? = null  // the handshake is done: this way works
        var over = false              // failed, or the relay says the PC isn't there
        var hostDown = false
        var why = ""
    }

    private var tries = listOf<Try>()
    private var won: Try? = null
    private var wait = 2000L
    private var running = false
    var state = State.UNPAIRED
        private set
    val direct get() = won?.direct == true  // straight to the PC, not through the relay

    val paired get() = prefs.getString("pc", null) != null && (prefs.getString("token", null) != null || prefs.getString("secret", null) != null)

    fun pair(p: Pairing) {
        prefs.edit().putString("relay", p.relay).putString("pc", p.pc).putString("key", p.key).putString("secret", p.secret)
            .putString("direct", p.direct.joinToString(",")).remove("token").apply()
        restart()
    }

    fun unpair() {
        prefs.edit().remove("pc").remove("token").remove("secret").remove("direct").apply()
        stop()
        set(State.UNPAIRED, "")
    }

    fun start() {
        running = true
        if (tries.isEmpty()) connect()
    }

    fun stop() {
        running = false
        main.removeCallbacksAndMessages(null)
        close()
    }

    /** The network changed (Wi-Fi came or went): don't wait out the backoff. */
    fun retryNow() {
        if (!running || state == State.ONLINE || state == State.UNPAIRED) return
        main.removeCallbacksAndMessages(null)
        wait = 2000L
        close()
        connect()
    }

    private fun restart() {
        stop()
        start()
    }

    private fun close() {
        tries.forEach { it.ws?.close(1000, null) }
        tries = emptyList()
        won = null
    }

    fun send(message: JSONObject): Boolean {
        val t = won ?: return false
        if (state != State.ONLINE) return false
        return t.ws?.send(t.channel!!.seal(message).toByteString()) ?: false
    }

    private fun set(s: State, detail: String) {  // (always on the main thread: the sockets' callbacks are posted there)
        if (s != state || detail.isNotBlank()) Trace.log("link $s $detail")
        state = s
        onState(s, detail)
    }

    private fun connect() {
        if (!paired) return set(State.UNPAIRED, "")
        set(State.CONNECTING, "")
        val relay = prefs.getString("relay", "") ?: ""
        val urls = (prefs.getString("direct", "") ?: "").split(",").filter { it.isNotBlank() }.map { "ws://$it/" to true } +
            (if (relay.isBlank()) emptyList() else listOf("$relay/phone?id=${prefs.getString("pc", "")}" to false))
        tries = urls.mapNotNull { (url, direct) -> dial(url, direct) }
        if (tries.isEmpty()) set(State.NO_RELAY, "The pairing is damaged: unpair and pair again.")
    }

    private fun dial(url: String, direct: Boolean): Try? {
        val request = try {
            Request.Builder().url(url).build()
        } catch (e: IllegalArgumentException) {  // (a pairing saved before they were checked: skipped, not a crash)
            return null
        }
        val t = Try(direct)
        t.ws = http.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                main.post { if (t in tries && direct) hello(t) }  // (through the relay, its note that the PC is there comes first)
            }
            override fun onMessage(webSocket: WebSocket, text: String) {
                main.post { if (t in tries) runCatching { JSONObject(text) }.getOrNull()?.let { relayNote(t, it) } }
            }
            override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
                main.post { if (t in tries) frame(t, bytes.toByteArray()) }
            }
            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                main.post { if (t in tries) gone(t, "") }
            }
            override fun onFailure(webSocket: WebSocket, e: Throwable, response: Response?) {
                main.post { if (t in tries) gone(t, e.message ?: "no connection") }
            }
        })
        return t
    }

    private fun hello(t: Try) {
        val own = Crypto.fresh()
        val pcKey = runCatching { Base64.getUrlDecoder().decode(prefs.getString("key", "") ?: "") }.getOrNull() ?: return gone(t, "The pairing is damaged: unpair and pair again.")
        t.channel = null
        t.finish = { welcome -> Crypto.finish(own, pcKey, welcome) }
        t.ws?.send((byteArrayOf(Crypto.HELLO) + Crypto.raw(own.public as ECPublicKey)).toByteString())
    }

    private fun relayNote(t: Try, m: JSONObject) {
        if (m.optString("t") != "host") return
        if (!m.optBoolean("up")) {
            t.hostDown = true
            return gone(t, "")
        }
        if (t === won) {  // the PC's Jarvis restarted: the conversation starts over on this connection
            won = null
            set(State.CONNECTING, "")
        }
        hello(t)
    }

    /** This way to the PC is over. The connection in use: start again. One of several being tried: the others go on,
     *  and when none is left the app says why and tries again in a while. */
    private fun gone(t: Try, why: String) {
        Trace.log("link: a way closed (direct=${t.direct}, in use=${t === won}): $why")
        t.over = true
        t.why = why
        t.ws?.close(1000, null)
        if (t === won) {
            close()
            if (!running) return
            set(if (t.hostDown) State.PC_OFFLINE else State.CONNECTING, "")
            return retryLater()
        }
        if (won != null) return
        tries.firstOrNull { it.channel != null && !it.over }?.let { return win(it) }  // (the relay answered and was waiting for these)
        if (tries.any { !it.over }) return
        val relay = tries.firstOrNull { !it.direct }
        val (s, detail) = when {
            tries.any { it.hostDown } -> State.PC_OFFLINE to ""
            relay != null -> State.NO_RELAY to relay.why
            else -> State.PC_OFFLINE to "Your PC isn't on this network. Set up the relay in its Settings to reach it from anywhere."
        }
        close()
        if (!running) return
        set(s, detail)
        retryLater()
    }

    private fun retryLater() {
        main.postDelayed({ if (running && tries.isEmpty()) connect() }, wait)
        wait = minOf(wait * 2, 30_000)
    }

    /** This connection is the one: the others are dropped, and the app says who it is (its token, or the pairing secret). */
    private fun win(t: Try) {
        if (won != null) return
        won = t
        tries.filter { it !== t }.forEach { it.ws?.close(1000, null) }
        tries = listOf(t)
        val token = prefs.getString("token", null)
        val hello = if (token != null) greeting(token, waiting())
            else JSONObject().put("op", "pair").put("secret", prefs.getString("secret", "")).put("name", "${Build.MANUFACTURER} ${Build.MODEL}")
        t.ws?.send(t.channel!!.seal(hello).toByteString())
    }

    private fun frame(t: Try, data: ByteArray) {
        val done = t.finish
        try {
            if (done != null) {
                t.finish = null
                t.channel = done(data)
                // straight to the PC wins at once; the relay waits a moment for a direct way that's still answering
                if (t.direct || tries.none { it.direct && !it.over }) win(t)
                else main.postDelayed({ if (won == null && t in tries && !t.over) win(t) }, 1500)
                return
            }
            if (t !== won) return
            val m = t.channel?.open(data) ?: return
            when (m.optString("op")) {
                "paired" -> {
                    prefs.edit().putString("token", m.getString("token")).remove("secret").apply()
                    t.ws?.send(t.channel!!.seal(greeting(m.getString("token"), waiting())).toByteString())
                }
                "ready" -> {
                    wait = 2000L
                    // (where the PC is now: its address changes with its network)
                    m.optJSONArray("direct")?.let { prefs.edit().putString("direct", Pairing.addresses(it).joinToString(",")).apply() }
                    set(State.ONLINE, m.optString("name"))
                    onMessage(m)
                }
                "error" -> if (m.optBoolean("unpaired") || prefs.getString("token", null) == null) {
                    prefs.edit().remove("token").remove("secret").apply()
                    stop()
                    set(State.UNPAIRED, m.optString("error"))
                } else onMessage(m)
                else -> onMessage(m)
            }
        } catch (e: Exception) {  // a frame that doesn't open: this isn't a trustworthy connection
            gone(t, e.message ?: "bad frame")
        }
    }
}

/** Who the app is (its token), and the ids of what it asked and still waits for (the PC sends those answers again: the
 *  link may have dropped while they were on the way). An older PC ignores them. */
internal fun greeting(token: String, waiting: List<Int>): JSONObject =
    JSONObject().put("op", "hello").put("token", token).put("waiting", JSONArray(waiting))

/** The system's DNS, keeping each host's last answer for when a lookup fails: a phone's private DNS timed out for
 *  minutes while the relay's address stayed the same, and the app couldn't reconnect. */
class KeptDns(private val system: Dns = Dns.SYSTEM) : Dns {
    private val known = java.util.concurrent.ConcurrentHashMap<String, List<java.net.InetAddress>>()

    override fun lookup(hostname: String): List<java.net.InetAddress> = try {
        system.lookup(hostname).also { known[hostname] = it }
    } catch (e: java.net.UnknownHostException) {
        known[hostname] ?: throw e
    }
}
