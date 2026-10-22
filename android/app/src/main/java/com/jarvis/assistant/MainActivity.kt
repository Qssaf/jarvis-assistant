package com.jarvis.assistant

import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.speech.RecognizerIntent
import android.speech.tts.TextToSpeech
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions
import okhttp3.Call
import okhttp3.Callback
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

class MainActivity : ComponentActivity() {
    private lateinit var link: Link
    private var tts: TextToSpeech? = null
    private var nextId = 1  // request ids
    private var nextMsg = 1
    private val messages = mutableStateListOf<Msg>()
    private var ui by mutableStateOf(Ui())
    private val waiting = mutableMapOf<Int, Boolean>()  // request id -> it was spoken (so the reply is read out)
    private val held = mutableListOf<Pair<String, Boolean>>()  // asked while still connecting (back from the speech screen)
    private val http = OkHttpClient.Builder().readTimeout(60, TimeUnit.SECONDS).build()
    private val prefs by lazy { getSharedPreferences("jarvis", MODE_PRIVATE) }

    private val scan = registerForActivityResult(ScanContract()) { result -> result.contents?.let { pairWith(it) } }
    private val listen = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull()?.let { ask(it, spoken = true) }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge(SystemBarStyle.dark(Color.TRANSPARENT), SystemBarStyle.dark(Color.TRANSPARENT))
        super.onCreate(savedInstanceState)
        link = Link(prefs, ::showState, ::received)
        val actions = Actions(
            ask = { ask(it, spoken = false) },
            listen = {
                try {
                    listen.launch(Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM))
                } catch (e: Exception) {
                    say("This phone has no speech recognition app.", Who.NOTE)
                }
            },
            stop = { link.send(JSONObject().put("op", "stop")) },
            scan = { scan.launch(ScanOptions().setPrompt("Scan the code in Jarvis's Settings on your PC").setBeepEnabled(false).setOrientationLocked(false)) },
            pair = ::pairWith,
            saveKey = {
                prefs.edit().putString("gemini_key", it.trim()).apply()
                refresh()
            },
            unpair = { link.unpair() },
        )
        setContent { JarvisApp(ui, actions) }
        fromLink(intent)
        showState(link.state, "")
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        fromLink(intent)
    }

    /** A jarvis://pair link (the PC's code scanned with the camera app) pairs only an unpaired app: any web page can open
     *  one, and it mustn't switch a paired app over to someone else's PC. Pairing again is unpair, then scan in the app. */
    private fun fromLink(intent: Intent?) {
        val code = intent?.dataString?.takeIf { it.startsWith("jarvis://pair") } ?: return
        if (link.paired) say("Already paired with your PC. To pair with another, unpair in Settings, then scan its code here.", Who.NOTE)
        else pairWith(code)
    }

    // connected only while the app is open: replies that finish meanwhile wait on the PC and arrive when it's opened again
    override fun onStart() {
        super.onStart()
        link.start()
    }

    override fun onStop() {
        super.onStop()
        link.stop()
    }

    override fun onDestroy() {
        tts?.shutdown()
        super.onDestroy()
    }

    private fun refresh(note: String = ui.note) {
        ui = Ui(
            paired = link.paired,
            state = link.state,
            note = note,
            pc = prefs.getString("pc_name", "") ?: "",
            relay = Uri.parse(prefs.getString("relay", "") ?: "").host ?: "",
            messages = messages,
            working = waiting.isNotEmpty() && link.state == State.ONLINE,
            key = prefs.getString("gemini_key", "") ?: "",
            version = BuildConfig.VERSION_NAME,
        )
    }

    private fun showState(state: State, detail: String) {
        if (state == State.ONLINE && detail.isNotBlank()) prefs.edit().putString("pc_name", detail).apply()
        refresh(if (state == State.ONLINE) "" else detail)
        if (state != State.CONNECTING) held.toList().also { held.clear() }.forEach { (text, spoken) -> send(text, spoken) }
    }

    private fun pairWith(code: String) {
        val p = Pairing.parse(code) ?: return if (link.paired) say("That isn't a Jarvis pairing code.", Who.NOTE) else refresh("That isn't a Jarvis pairing code.")
        say("Pairing with your PC…", Who.NOTE)
        link.pair(p)
    }

    private fun ask(text: String, spoken: Boolean) {
        say(text, Who.YOU)
        if (link.state == State.CONNECTING) held.add(text to spoken) else send(text, spoken)
    }

    private fun send(text: String, spoken: Boolean) {
        val id = nextId++
        if (link.send(JSONObject().put("op", "ask").put("id", id).put("text", text))) {
            waiting[id] = spoken
            refresh()
        } else {
            offline(text, spoken)
        }
    }

    private fun received(m: JSONObject) {
        when (m.optString("op")) {
            "working" -> if (m.optBoolean("queued")) say("Busy with another task — yours is next.", Who.NOTE)
            "reply" -> {
                val spoken = waiting.remove(m.optInt("id")) ?: false
                say(m.optString("text"), Who.JARVIS)
                if (spoken) speak(m.optString("text"))
            }
            "stopped" -> {
                waiting.clear()
                say("Stopped.", Who.NOTE)
            }
            "error" -> say(m.optString("error"), Who.NOTE)
        }
        refresh()
    }

    /** The PC can't be reached: answer from Gemini on the phone, with the user's own key, if they gave one. */
    private fun offline(text: String, spoken: Boolean) {
        val key = prefs.getString("gemini_key", "") ?: ""
        if (key.isBlank()) return say("Your PC can't be reached right now, so nothing was done. Add a Gemini key in Settings to get answers on the phone meanwhile.", Who.NOTE)
        val body = JSONObject()
            .put("systemInstruction", JSONObject().put("parts", JSONArray().put(JSONObject().put("text",
                "You are Jarvis, the user's assistant, answering on their phone while their PC is off: you can't do anything on the PC " +
                    "or in their accounts right now, so say so if they ask for that. Reply in a few short plain sentences, no markdown."))))
            .put("contents", JSONArray().put(JSONObject().put("role", "user").put("parts", JSONArray().put(JSONObject().put("text", text)))))
        val request = Request.Builder().url("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent")
            .header("x-goog-api-key", key).post(body.toString().toRequestBody("application/json".toMediaType())).build()
        http.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) = runOnUiThread { say("No internet: ${e.message}", Who.NOTE) }
            override fun onResponse(call: Call, response: Response) {
                val reply = response.use {
                    val j = JSONObject(it.body?.string() ?: "{}")
                    j.optJSONArray("candidates")?.optJSONObject(0)?.optJSONObject("content")?.optJSONArray("parts")?.optJSONObject(0)?.optString("text")
                        ?: "Gemini didn't answer: ${j.optJSONObject("error")?.optString("message") ?: it.code}"
                }
                runOnUiThread {
                    say(reply.trim(), Who.PHONE)
                    if (spoken) speak(reply)
                }
            }
        })
    }

    private fun speak(text: String) {
        val engine = tts
        if (engine != null) {
            engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "reply")
            return
        }
        tts = TextToSpeech(this) { ok -> if (ok == TextToSpeech.SUCCESS) tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "reply") }
    }

    private fun say(text: String, who: Who) {
        messages.add(Msg(nextMsg++, who, text))
    }
}
