package com.jarvis.assistant

import android.os.Handler
import android.os.Looper
import android.util.Base64
import okhttp3.Call
import okhttp3.Callback
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.TimeUnit

/** Jarvis on the phone alone, while the PC can't be reached: Gemini with the user's own key, typed or spoken (Gemini
 *  Live, the PC's own voice model). It can't do anything on the PC or in the user's accounts, and says so. */
class Gemini(private val key: () -> String, private val liveModel: () -> String, private val voice: () -> String) {
    private val http = OkHttpClient.Builder().readTimeout(60, TimeUnit.SECONDS).pingInterval(20, TimeUnit.SECONDS).build()
    private val main = Handler(Looper.getMainLooper())
    private var ws: WebSocket? = null
    @Volatile private var ready = false

    /** A typed question: [done] gets the answer, or what went wrong (on the main thread). */
    fun answer(text: String, done: (reply: String) -> Unit) {
        val body = JSONObject().put("systemInstruction", parts("$PROMPT Reply in a few short plain sentences, no markdown."))
            .put("contents", JSONArray().put(parts(text).put("role", "user")))
        val request = Request.Builder().url("https://generativelanguage.googleapis.com/v1beta/models/$TEXT_MODEL:generateContent")
            .header("x-goog-api-key", key()).post(body.toString().toRequestBody("application/json".toMediaType())).build()
        http.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                main.post { done("No internet: ${e.message}") }
            }
            override fun onResponse(call: Call, response: Response) {
                val reply = response.use {
                    val j = runCatching { JSONObject(it.body?.string() ?: "{}") }.getOrDefault(JSONObject())
                    j.optJSONArray("candidates")?.optJSONObject(0)?.optJSONObject("content")?.optJSONArray("parts")?.optJSONObject(0)?.optString("text")
                        ?: "Gemini didn't answer: ${j.optJSONObject("error")?.optString("message") ?: it.code}"
                }
                main.post { done(reply.trim()) }
            }
        })
    }

    /** A spoken conversation. [onAudio] gets Jarvis's voice (24 kHz PCM, on the socket's thread), [onHush] means stop
     *  playing (the user spoke over it), [onSaid] a finished line of the user's (true) or Jarvis's, [onEnd] why it's over. */
    fun talk(onAudio: (ByteArray) -> Unit, onHush: () -> Unit, onSaid: (user: Boolean, text: String) -> Unit, onEnd: (why: String) -> Unit) {
        hangUp()
        val heard = StringBuilder()
        val said = StringBuilder()
        val url = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key=${key()}"
        lateinit var socket: WebSocket
        socket = http.newWebSocket(Request.Builder().url(url).build(), object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                webSocket.send(JSONObject().put("setup", JSONObject()
                    .put("model", "models/${liveModel()}")
                    .put("generationConfig", JSONObject().put("responseModalities", JSONArray().put("AUDIO"))
                        .put("speechConfig", JSONObject().put("voiceConfig", JSONObject().put("prebuiltVoiceConfig", JSONObject().put("voiceName", voice())))))
                    .put("systemInstruction", parts("$PROMPT You are speaking: short, natural answers."))
                    .put("inputAudioTranscription", JSONObject()).put("outputAudioTranscription", JSONObject())).toString())
            }

            override fun onMessage(webSocket: WebSocket, text: String) = message(text)
            override fun onMessage(webSocket: WebSocket, bytes: ByteString) = message(bytes.utf8())  // (it sends its JSON as binary)

            private fun message(text: String) {
                val m = runCatching { JSONObject(text) }.getOrNull() ?: return
                if (m.has("setupComplete")) ready = true
                val content = m.optJSONObject("serverContent") ?: return
                content.optJSONObject("modelTurn")?.optJSONArray("parts")?.let { parts ->
                    for (i in 0 until parts.length()) parts.optJSONObject(i)?.optJSONObject("inlineData")?.optString("data")
                        ?.takeIf { it.isNotEmpty() }?.let { onAudio(Base64.decode(it, Base64.DEFAULT)) }
                }
                content.optJSONObject("inputTranscription")?.optString("text")?.let(heard::append)
                content.optJSONObject("outputTranscription")?.optString("text")?.let(said::append)
                val interrupted = content.optBoolean("interrupted")
                if (interrupted || content.optBoolean("turnComplete")) {
                    val (user, jarvis) = heard.toString().trim() to said.toString().trim()
                    heard.clear()
                    said.clear()
                    main.post {
                        if (socket !== ws) return@post
                        if (interrupted) onHush()
                        if (user.isNotEmpty()) onSaid(true, user)
                        if (jarvis.isNotEmpty()) onSaid(false, jarvis)
                    }
                }
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) = over(webSocket, reason)
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) =
                over(webSocket, if (response?.code == 400 || response?.code == 403) "Gemini refused the key: check it in Settings." else t.message ?: "no connection")

            private fun over(webSocket: WebSocket, why: String) {
                main.post {
                    if (webSocket !== ws) return@post
                    ws = null
                    ready = false
                    onEnd(why)
                }
            }
        })
        ws = socket
    }

    /** 80 ms from the microphone. */
    fun hear(frame: ShortArray) {
        val socket = ws ?: return
        if (!ready) return
        val bytes = ByteBuffer.allocate(frame.size * 2).order(ByteOrder.LITTLE_ENDIAN).apply { asShortBuffer().put(frame) }.array()
        socket.send(JSONObject().put("realtimeInput", JSONObject().put("audio", JSONObject()
            .put("data", Base64.encodeToString(bytes, Base64.NO_WRAP)).put("mimeType", "audio/pcm;rate=16000"))).toString())
    }

    val talking get() = ws != null

    fun hangUp() {
        ws?.close(1000, null)
        ws = null
        ready = false
    }

    private fun parts(text: String) = JSONObject().put("parts", JSONArray().put(JSONObject().put("text", text)))

    companion object {
        const val TEXT_MODEL = "gemini-3.5-flash-lite"
        const val PROMPT = "You are Jarvis, the user's assistant, answering on their phone while their PC can't be reached: you can't do " +
            "anything on the PC or in their accounts right now, so say so if they ask for that."
    }
}
