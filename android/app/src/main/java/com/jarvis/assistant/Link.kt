package com.jarvis.assistant

import android.content.SharedPreferences
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.Base64
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import okio.ByteString.Companion.toByteString
import org.json.JSONObject
import java.math.BigInteger
import java.security.KeyFactory
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.interfaces.ECPublicKey
import java.security.spec.ECGenParameterSpec
import java.security.spec.ECPoint
import java.security.spec.ECPublicKeySpec
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

/** The pairing code from the PC's Settings: jarvis://pair#<base64url JSON {v, r: relay, s: PC id, k: PC key, p: secret}>. */
data class Pairing(val relay: String, val pc: String, val key: String, val secret: String) {
    companion object {
        fun parse(link: String): Pairing? = try {
            val j = JSONObject(String(Base64.decode(link.trim().substringAfter("#"), Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING)))
            Pairing(j.getString("r"), j.getString("s"), j.getString("k"), j.getString("p"))
        } catch (e: Exception) {
            null
        }
    }
}

enum class State { UNPAIRED, CONNECTING, ONLINE, PC_OFFLINE, NO_RELAY }

/** One connection to the PC through the relay, kept up while the app is open. */
class Link(private val prefs: SharedPreferences, private val onState: (State, String) -> Unit, private val onMessage: (JSONObject) -> Unit) {
    private val http = OkHttpClient.Builder().pingInterval(25, TimeUnit.SECONDS).build()
    private val main = Handler(Looper.getMainLooper())
    private var ws: WebSocket? = null
    private var channel: Channel? = null
    private var finish: ((ByteArray) -> Channel)? = null
    private var wait = 2000L
    private var running = false
    var state = State.UNPAIRED
        private set

    val paired get() = prefs.getString("pc", null) != null && (prefs.getString("token", null) != null || prefs.getString("secret", null) != null)

    fun pair(p: Pairing) {
        prefs.edit().putString("relay", p.relay).putString("pc", p.pc).putString("key", p.key).putString("secret", p.secret).remove("token").apply()
        restart()
    }

    fun unpair() {
        prefs.edit().remove("pc").remove("token").remove("secret").apply()
        stop()
        set(State.UNPAIRED, "")
    }

    fun start() {
        running = true
        if (ws == null) connect()
    }

    fun stop() {
        running = false
        main.removeCallbacksAndMessages(null)
        ws?.close(1000, null)
        ws = null
        channel = null
    }

    private fun restart() {
        stop()
        start()
    }

    fun send(message: JSONObject): Boolean {
        val ch = channel ?: return false
        if (state != State.ONLINE) return false
        return ws?.send(ch.seal(message).toByteString()) ?: false
    }

    private fun set(s: State, detail: String) {  // (always on the main thread: the socket's callbacks are posted there)
        state = s
        onState(s, detail)
    }

    private fun connect() {
        if (!paired) return set(State.UNPAIRED, "")
        set(State.CONNECTING, "")
        val url = "${prefs.getString("relay", "")}/phone?id=${prefs.getString("pc", "")}"
        ws = http.newWebSocket(Request.Builder().url(url).build(), object : WebSocketListener() {
            override fun onMessage(webSocket: WebSocket, text: String) {
                main.post { if (webSocket == ws) relayNote(JSONObject(text)) }
            }
            override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
                main.post { if (webSocket == ws) frame(bytes.toByteArray()) }
            }
            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                main.post { if (webSocket == ws) lost("") }
            }
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                main.post { if (webSocket == ws) lost(t.message ?: "no connection") }
            }
        })
    }

    private fun lost(why: String) {
        ws = null
        channel = null
        if (!running) return
        set(State.NO_RELAY, why)
        main.postDelayed({ if (running && ws == null) connect() }, wait)
        wait = minOf(wait * 2, 30_000)
    }

    private fun relayNote(m: JSONObject) {
        if (m.optString("t") != "host") return
        channel = null
        if (!m.optBoolean("up")) return set(State.PC_OFFLINE, "")
        val own = Crypto.fresh()
        val pcKey = Base64.decode(prefs.getString("key", ""), Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING)
        finish = { welcome -> Crypto.finish(own, pcKey, welcome) }
        ws?.send((byteArrayOf(Crypto.HELLO) + Crypto.raw(own.public as ECPublicKey)).toByteString())
    }

    private fun frame(data: ByteArray) {
        val done = finish
        try {
            if (done != null) {
                finish = null
                channel = done(data)
                val token = prefs.getString("token", null)
                val hello = if (token != null) JSONObject().put("op", "hello").put("token", token)
                    else JSONObject().put("op", "pair").put("secret", prefs.getString("secret", "")).put("name", "${Build.MANUFACTURER} ${Build.MODEL}")
                ws?.send(channel!!.seal(hello).toByteString())
                return
            }
            val m = channel?.open(data) ?: return
            when (m.optString("op")) {
                "paired" -> {
                    prefs.edit().putString("token", m.getString("token")).remove("secret").apply()
                    ws?.send(channel!!.seal(JSONObject().put("op", "hello").put("token", m.getString("token"))).toByteString())
                }
                "ready" -> {
                    wait = 2000L
                    set(State.ONLINE, m.optString("name"))
                }
                "error" -> if (m.optBoolean("unpaired") || prefs.getString("token", null) == null) {
                    prefs.edit().remove("token").remove("secret").apply()
                    stop()
                    set(State.UNPAIRED, m.optString("error"))
                } else onMessage(m)
                else -> onMessage(m)
            }
        } catch (e: Exception) {  // a frame that doesn't open: this isn't a trustworthy connection
            ws?.close(1000, null)
            lost(e.message ?: "bad frame")
        }
    }
}
