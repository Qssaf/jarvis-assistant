package com.jarvis.assistant

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.BitmapFactory
import android.net.ConnectivityManager
import android.net.Network
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Base64
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import org.json.JSONObject
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.concurrent.thread
import kotlin.math.sqrt

/** The app behind its screens: the link to the PC, the conversation, the microphone and Jarvis's voice. One for the
 *  whole process, so the screen and the background service (JarvisService) share it. Everything here runs on the main
 *  thread except [heard] (the microphone's). */
object Jarvis {
    private lateinit var app: Context
    private val main = Handler(Looper.getMainLooper())
    private val prefs by lazy { app.getSharedPreferences("jarvis", Context.MODE_PRIVATE) }
    private lateinit var link: Link

    val messages = mutableStateListOf<Msg>()
    var ui by mutableStateOf(Ui())
        private set
    val level = mutableFloatStateOf(0f)  // how loud the microphone is, 0-1 (the orb follows it)
    var foreground = false               // the app is on screen: otherwise news comes as notifications
    /** Set by the screen: asks for a permission, then goes on if it was given. */
    var askPermission: (permission: String, then: () -> Unit) -> Unit = { _, _ -> }

    private var users = 0  // the screen while it shows, the service while it runs: the link is up while either is
    private var nextId = 1  // (an ask's id: kept from one start to the next, so a late answer can't land on another)
    private var nextMsg = 1
    private val asks = Asks()  // asked, not answered yet
    private val held = mutableListOf<String>()  // asked while still connecting
    private val callbacks = mutableMapOf<Int, (JSONObject?, String) -> Unit>()  // get/post -> what to do with the answer
    private val player by lazy { Player() }
    private val mic = Mic(::heard)
    private val gemini by lazy {
        Gemini({ prefs.getString("gemini_key", "") ?: "" }, { prefs.getString("live_model", null) ?: "gemini-3.8-live" },
            { prefs.getString("voice_name", null) ?: "Charon" })
    }

    private enum class Via { PC, PHONE }
    @Volatile private var via: Via? = null       // who the microphone is talking with now
    @Volatile private var gate: WakeGate? = null  // the wake word, once its models are here
    @Volatile private var wakeListening = false   // the service is up with the microphone: the wake word is listened for
    @Volatile private var lastWake = 0L
    @Volatile private var lastVoice = 0L          // (phone-only talk) when either side last spoke
    private var voice = Voice.OFF
    private var speaking = false
    private var note = ""
    private var activity = ""
    private var wakeNote = ""
    private var draft = ""
    private var weather: Weather? = null
    private var reminders = listOf<Reminder>()
    private var playing: Playing? = null
    private var stats: Pc? = null
    private var jobs = listOf<Job>()
    private var screen: ImageBitmap? = null
    private var screenLoading = false
    private var loaded = false  // the Today and PC pages have their first answer

    fun init(context: Context) {
        if (::app.isInitialized) return
        app = context.applicationContext
        Trace.start(app.filesDir)
        nextId = prefs.getInt("next_id", 1)
        link = Link(prefs, ::showState, ::received, asks::hello)
        app.getSystemService(ConnectivityManager::class.java)?.registerDefaultNetworkCallback(object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                main.post { link.retryNow() }  // (home Wi-Fi just came: the direct way may work now)
            }
        })
        loadWake()
        refresh()
    }

    /** The screen came up, or the service started. */
    fun hold() {
        if (users++ == 0) link.start()
    }

    fun release() {
        if (--users > 0) return
        users = 0
        endVoice()
        link.stop()
    }

    private fun granted(permission: String) = app.checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED
    private val key get() = prefs.getString("gemini_key", "") ?: ""
    private val wakeWanted get() = prefs.getBoolean("wake", false)
    private val wakeFiles get() = (prefs.getString("wake_files", "") ?: "").split(",").filter { it.isNotBlank() }.map { File(wakeDir, it) }
    private val wakeDir get() = File(app.filesDir, "wake").apply { mkdirs() }

    private fun refresh() {
        ui = Ui(
            paired = link.paired, state = link.state, note = note, pc = prefs.getString("pc_name", "") ?: "",
            relay = Uri.parse(prefs.getString("relay", "") ?: "").host ?: "", direct = link.direct, messages = messages,
            working = asks.any && link.state == State.ONLINE, activity = activity, key = key, version = BuildConfig.VERSION_NAME,
            voice = voice, speaking = speaking, onPhone = via == Via.PHONE,
            wake = wakeWanted, wakePhrase = prefs.getString("wake_phrase", null) ?: "Hey Jarvis", wakeNote = wakeNote,
            background = prefs.getBoolean("background", false), weather = weather, reminders = reminders, playing = playing, stats = stats, jobs = jobs,
            screen = screen, screenLoading = screenLoading, loaded = loaded, draft = draft,
        )
    }

    private fun say(text: String, who: Who) {
        messages.add(Msg(nextMsg++, who, text))
        if (messages.size > 300) messages.removeRange(0, 100)
    }

    // ---- the link

    private fun showState(state: State, detail: String) {
        if (state == State.UNPAIRED) asks.clear()
        else if (state != State.ONLINE && asks.dropped()) say("The link to your PC dropped while it was working on that. It carries on, and its answer comes here once the link is back.", Who.NOTE)
        if (state == State.ONLINE && detail.isNotBlank()) prefs.edit().putString("pc_name", detail).apply()
        note = if (state == State.ONLINE) "" else detail
        if (state != State.ONLINE) {
            activity = ""
            jobs = emptyList()
            callbacks.clear()
            if (via == Via.PC) endVoice(tell = false)
        }
        if (state != State.CONNECTING) held.toList().also { held.clear() }.forEach(::send)
        refresh()
        syncService()
    }

    fun pair(code: String) {
        val p = Pairing.parse(code)
        if (p == null) {
            if (link.paired) say("That isn't a Jarvis pairing code.", Who.NOTE) else note = "That isn't a Jarvis pairing code."
            return refresh()
        }
        say("Pairing with your PC…", Who.NOTE)
        link.pair(p)
    }

    /** A jarvis://pair link (the PC's code scanned with the camera app) pairs only an unpaired app: any web page can open
     *  one, and it mustn't switch a paired app over to someone else's PC. Pairing again is unpair, then scan in the app. */
    fun pairFromLink(code: String) {
        if (link.paired) say("Already paired with your PC. To pair with another, unpair in Settings, then scan its code here.", Who.NOTE)
        else pair(code)
    }

    fun unpair() {
        endVoice()
        asks.clear()
        link.unpair()
        messages.clear()
        syncService()
    }

    fun saveKey(value: String) {
        prefs.edit().putString("gemini_key", value.trim()).apply()
        refresh()
    }

    // ---- asking

    fun ask(text: String) {
        draft = ""
        when {
            link.state == State.CONNECTING -> {
                say(text, Who.YOU)
                held.add(text)
            }
            else -> send(text)
        }
        refresh()
    }

    private fun send(text: String) {
        val id = nextId++
        prefs.edit().putInt("next_id", nextId).apply()
        if (link.send(JSONObject().put("op", "ask").put("id", id).put("text", text))) {
            asks.sent(id)  // (the PC's chat shows the question, and sends it back as an event: not added twice)
        } else {
            if (messages.lastOrNull()?.let { it.who == Who.YOU && it.text == text } != true) say(text, Who.YOU)
            if (key.isBlank()) say("Your PC can't be reached right now, so nothing was done. Add a Gemini key in Settings to get answers on the phone meanwhile.", Who.NOTE)
            else gemini.answer(text) { say(it, Who.PHONE) }
        }
        refresh()
    }

    fun stop() {
        post("/api/stop")
        endVoice()
    }

    fun newChat() {
        post("/api/new") { _, error -> if (error.isEmpty()) messages.clear() }
    }

    /** Something shared to Jarvis from another app: it waits in the box for what to do with it. */
    fun share(text: String) {
        draft = text.take(4000)
        refresh()
    }

    private fun get(path: String, then: (JSONObject?, String) -> Unit) = request("get", path, then)
    private fun post(path: String, then: (JSONObject?, String) -> Unit = { _, _ -> }) = request("post", path, then)

    private fun request(op: String, path: String, then: (JSONObject?, String) -> Unit) {
        val id = nextId++
        if (link.send(JSONObject().put("op", op).put("id", id).put("path", path))) callbacks[id] = then
        else then(null, "Your PC can't be reached right now.")
    }

    private fun received(m: JSONObject) {
        if (m.optString("op") !in setOf("audio", "event", "file")) Trace.log("got ${m.optString("op")} on=${m.opt("on")} why=${m.optString("why")}")
        when (m.optString("op")) {
            "ready" -> {
                prefs.edit().putString("live_model", m.optString("live").ifBlank { null }).putString("voice_name", m.optString("voice_name").ifBlank { null }).apply()
                val phrase = m.optString("wake")
                if (phrase.isNotBlank() && phrase != prefs.getString("wake_phrase", null)) {  // (the PC listens for another word now)
                    prefs.edit().putString("wake_phrase", phrase).remove("wake_files").apply()
                    gate = null
                }
                if (wakeWanted && gate == null) fetchWake()
                val unknown = lost(m)
                get("/api/conversation") { data, _ ->
                    data?.optJSONArray("messages")?.let { list ->
                        messages.clear()
                        for (i in 0 until list.length()) list.optJSONObject(i)?.let { shown(it.optString("who"), it.optString("text")) }
                    }
                    // (after the PC's chat, which replaces what's shown; the answers it still had came right after the ready)
                    if (asks.back(unknown).isNotEmpty()) say(
                        if (unknown != null) "Your PC lost what you asked before it could answer (it restarted). It may have done it already: check on the PC before asking again."
                        else "Your PC is back, but can't say whether it still has what you asked. If no answer comes, check on the PC before asking again.", Who.NOTE)
                }
                if (loaded) loadToday()
            }
            "reply" -> {
                val text = m.optString("text")
                asks.answered(m.optInt("id"))
                if (!asks.any) activity = ""
                if (messages.takeLast(6).none { it.who == Who.JARVIS && it.text == text }) say(text, Who.JARVIS)  // (unless its event came)
                if (!foreground) notify(text)
                if (loaded) loadJobs()
            }
            "event" -> if (m.optString("kind") == "log") shown(m.optString("who"), m.optString("text"))
            "stopped" -> {
                asks.clear()
                activity = ""
                if (loaded) loadJobs()
            }
            "error" -> say(m.optString("error"), Who.NOTE)
            "got" -> callbacks.remove(m.optInt("id"))?.invoke(m.optJSONObject("data"), m.optString("error"))
            "voice" -> if (m.optBoolean("on")) {
                voice = Voice.LISTENING
            } else if (via == Via.PC) {
                endVoice(tell = false, hush = false)  // (Jarvis's last words are still playing)
                m.optString("why").takeIf { it.isNotBlank() }?.let { say(it, Who.NOTE) }
            }
            "audio" -> if (via == Via.PC) spoke(Base64.decode(m.optString("d"), Base64.DEFAULT))
            "hush" -> player.hush()
            "file" -> runCatching {
                val part = File(wakeDir, File(m.optString("name")).name + ".part")
                if (m.optInt("i") == 0) part.delete()
                part.appendBytes(Base64.decode(m.optString("d"), Base64.DEFAULT))
                if (m.optInt("i") == m.optInt("n") - 1) part.renameTo(File(wakeDir, part.name.removeSuffix(".part")))
            }
            "wake" -> {
                val files = m.optJSONArray("files")
                if (files != null && files.length() == 3) {
                    prefs.edit().putString("wake_files", (0 until 3).joinToString(",") { File(files.optString(it)).name })
                        .putString("wake_phrase", m.optString("phrase").ifBlank { "Hey Jarvis" }).apply()
                    wakeNote = ""
                    loadWake()
                } else wakeNote = "The wake word couldn't be fetched: ${m.optString("error").ifBlank { "try again" }}"
            }
        }
        refresh()
    }

    /** A line of the PC's chat, as the app shows it. */
    private fun shown(who: String, line: String) {
        val text = line.removePrefix("📱 ")
        when (who) {
            "you" -> say(text, Who.YOU)
            "jarvis" -> say(text, Who.JARVIS)
            "system" -> say(text, Who.NOTE)
            "tool" -> activity = text
        }
    }

    private fun notify(text: String) {
        val manager = app.getSystemService(NotificationManager::class.java) ?: return
        manager.createNotificationChannel(NotificationChannel("news", "From Jarvis", NotificationManager.IMPORTANCE_DEFAULT))
        val open = PendingIntent.getActivity(app, 0, Intent(app, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        manager.notify(nextMsg++, Notification.Builder(app, "news").setSmallIcon(R.drawable.ic_launcher_monochrome).setContentTitle("Jarvis")
            .setContentText(text).setStyle(Notification.BigTextStyle().bigText(text)).setContentIntent(open).setAutoCancel(true).build())
    }

    // ---- talking

    /** The orb, the mic button, the assistant gesture: start talking, interrupt Jarvis, or stop. */
    fun talk() {
        when {
            voice == Voice.OFF -> askPermission(Manifest.permission.RECORD_AUDIO) { startVoice("tap") }
            player.busy -> {
                player.hush()
                if (via == Via.PC) link.send(JSONObject().put("op", "barge"))
            }
            else -> endVoice()
        }
    }

    private fun startVoice(how: String) {
        Trace.log("voice start ($how), now $voice, link ${link.state}")
        if (voice != Voice.OFF) return
        when {
            link.state == State.ONLINE -> {
                via = Via.PC
                link.send(JSONObject().put("op", "voice").put("on", true).put("how", how))
            }
            key.isNotBlank() -> {
                via = Via.PHONE
                lastVoice = SystemClock.elapsedRealtime()
                gemini.talk(::spoke, { player.hush() }, { user, text -> say(text, if (user) Who.YOU else Who.PHONE) }) { why ->
                    if (via == Via.PHONE) {
                        endVoice()
                        if (why.isNotBlank()) say(why, Who.NOTE)
                    }
                }
            }
            else -> return say("Your PC can't be reached right now. Add a Gemini key in Settings to talk with Jarvis on the phone meanwhile.", Who.NOTE).also { refresh() }
        }
        voice = if (via == Via.PC) Voice.STARTING else Voice.LISTENING
        if (!mic.start()) {
            endVoice()
            say("The microphone couldn't be opened.", Who.NOTE)
        }
        refresh()
    }

    private fun endVoice(tell: Boolean = true, hush: Boolean = true) {
        if (voice == Voice.OFF && via == null) return
        Trace.log("voice end (tell=$tell) from ${Throwable().stackTrace.getOrNull(1)?.methodName}, was $voice")
        if (via == Via.PC && tell) link.send(JSONObject().put("op", "voice").put("on", false))
        if (via == Via.PHONE) gemini.hangUp()
        via = null
        voice = Voice.OFF
        level.floatValue = 0f
        if (hush) player.hush()
        if (!wakeListening) mic.stop()
        gate?.reset()
        refresh()
    }

    /** Jarvis's voice arrived (any thread). */
    private fun spoke(pcm: ByteArray) {
        player.play(pcm)
        lastVoice = SystemClock.elapsedRealtime()
        main.post {
            if (speaking) return@post
            speaking = true
            refresh()
            watchSpeaking()
        }
    }

    private fun watchSpeaking() {
        main.postDelayed({
            if (player.busy) return@postDelayed watchSpeaking()
            speaking = false
            refresh()
        }, 250)
    }

    /** 80 ms from the microphone (its own thread): to whoever is being talked with, else to the wake word. */
    private var sentFrames = 0
    private fun heard(frame: ShortArray) {
        when (via) {
            Via.PC -> {
                meter(frame)
                val bytes = ByteBuffer.allocate(frame.size * 2).order(ByteOrder.LITTLE_ENDIAN).apply { asShortBuffer().put(frame) }.array()
                val message = JSONObject().put("op", "audio").put("d", Base64.encodeToString(bytes, Base64.NO_WRAP))
                main.post { if (via == Via.PC && !link.send(message)) Trace.log("audio not sent: link ${link.state}") else if (++sentFrames % 50 == 1) Trace.log("audio frames sent: $sentFrames") }
            }
            Via.PHONE -> {
                val loud = meter(frame) > 0.15f
                val now = SystemClock.elapsedRealtime()
                if (loud) lastVoice = now
                if (!player.busy) gemini.hear(frame)  // (its own voice, from the speaker next to the microphone, isn't the user)
                if (now - lastVoice > 20_000) main.post { if (via == Via.PHONE) endVoice() }  // nobody's talking any more
            }
            null -> {
                val wake = gate ?: return
                if (!wakeListening || player.busy) return
                val now = SystemClock.elapsedRealtime()
                if (wake.score(frame) >= WakeGate.BAR && now - lastWake > 2000) {
                    lastWake = now
                    wake.reset()
                    main.post {
                        player.chime()
                        startVoice("wake")
                    }
                }
            }
        }
    }

    private fun meter(frame: ShortArray): Float {
        var sum = 0.0
        for (s in frame) sum += s.toDouble() * s
        return (sqrt(sum / frame.size) / 3000).toFloat().coerceIn(0f, 1f).also { level.floatValue = it }
    }

    // ---- the wake word and the background service

    fun setWake(on: Boolean) {
        if (!on) {
            prefs.edit().putBoolean("wake", false).apply()
            wakeNote = ""
            refresh()
            return syncService()
        }
        askPermission(Manifest.permission.RECORD_AUDIO) {
            val go = {
                prefs.edit().putBoolean("wake", true).apply()
                if (gate == null) fetchWake()
                refresh()
                syncService()
            }
            if (Build.VERSION.SDK_INT >= 33) askPermission(Manifest.permission.POST_NOTIFICATIONS, go) else go()
        }
    }

    fun setBackground(on: Boolean) {
        val go = {
            prefs.edit().putBoolean("background", on).apply()
            refresh()
            syncService()
        }
        if (on && Build.VERSION.SDK_INT >= 33) askPermission(Manifest.permission.POST_NOTIFICATIONS, go) else go()
    }

    private fun fetchWake() {
        wakeNote = if (link.send(JSONObject().put("op", "wake"))) "Getting the wake word from your PC…"
            else "The wake word comes from your PC: it starts working once the app has reached it."
    }

    private fun loadWake() {
        val files = wakeFiles
        if (files.size != 3 || files.any { !it.exists() }) return
        thread(name = "wake-load") {  // (opening the models takes a moment)
            val loaded = runCatching { WakeGate(Wake(files[0], files[1], files[2])) }.getOrNull()
            main.post {
                gate = loaded
                if (loaded == null) wakeNote = "The wake word's models couldn't be opened: switch it off and on again."
                refresh()
                syncService()
            }
        }
    }

    /** The service runs while it has something to do: the wake word, or staying in touch for notifications. */
    val serviceWanted get() = ::app.isInitialized && link.paired && (wakeWanted || prefs.getBoolean("background", false))
    val micWanted get() = wakeWanted && gate != null && granted(Manifest.permission.RECORD_AUDIO)

    fun syncService() {
        val intent = Intent(app, JarvisService::class.java)
        if (!serviceWanted) {
            app.stopService(intent)
            return
        }
        // (a service with the microphone can only be started while the app is on screen: from the background it keeps what it has)
        if (foreground || !JarvisService.running) runCatching { app.startForegroundService(intent) }
    }

    /** From the service: it's up (with the microphone or without), or gone. */
    fun serviceIs(up: Boolean, withMic: Boolean) {
        wakeListening = up && withMic
        if (wakeListening) keepListening() else if (via == null) mic.stop()
    }

    /** The wake word needs the microphone the whole time: opened again if a call or another app took it away. */
    private fun keepListening() {
        main.removeCallbacks(listenAgain)
        if (!wakeListening) return
        if (!mic.on) mic.start()
        main.postDelayed(listenAgain, 30_000)
    }

    private val listenAgain = Runnable { keepListening() }

    // ---- the Today and PC pages

    fun loadToday() {
        get("/api/today") { data, _ ->
            loaded = true
            data?.let { today ->
                weather = today.optJSONObject("weather")?.let { Weather(it.optString("place"), it.optString("icon"), it.optString("temp"), it.optString("condition")) }
                reminders = today.optJSONArray("reminders")?.let { list -> (0 until list.length()).mapNotNull { list.optJSONObject(it) }.map { Reminder(it.optString("text"), it.optString("when")) } } ?: emptyList()
            }
            refresh()
        }
    }

    /** The tasks running on the PC (an older Jarvis there doesn't say: none shown). */
    private fun loadJobs() {
        get("/api/jobs") { data, _ ->
            jobs = data?.optJSONArray("jobs")?.let { list -> (0 until list.length()).mapNotNull { list.optJSONObject(it) }
                .map { Job(it.optInt("n"), it.optString("label"), it.optString("now"), it.optInt("minutes")) } } ?: emptyList()
            refresh()
        }
    }

    /** Stops that task only: the others carry on. */
    fun stopJob(n: Int) {
        post("/api/jobs/$n/stop") { _, _ -> loadJobs() }
    }

    fun loadPc() {
        loadJobs()
        get("/api/media") { data, _ ->
            playing = data?.takeIf { it.optString("title").isNotBlank() }?.let { Playing(it.optString("title"), it.optString("artist"), it.optString("app"), it.optString("status") == "Playing") }
            refresh()
        }
        get("/api/system") { data, _ ->
            loaded = true
            stats = data?.let {
                val percent = { used: String, total: String -> (100 * it.optDouble(used, 0.0) / it.optDouble(total, 1.0).coerceAtLeast(1.0)).toInt() }
                val hours = (it.optDouble("uptime", 0.0) / 3600).toInt()
                Pc(it.optDouble("cpu", 0.0).toInt(), percent("mem_used", "mem_total"), percent("disk_used", "disk_total"),
                    if (hours >= 48) "${hours / 24} days" else if (hours >= 1) "$hours h" else "${(it.optDouble("uptime", 0.0) / 60).toInt()} min")
            }
            refresh()
        }
    }

    fun loadScreen() {
        screenLoading = true
        refresh()
        get("/api/screen") { data, error ->
            screenLoading = false
            val jpeg = data?.optString("jpeg")?.takeIf { it.isNotEmpty() }?.let { Base64.decode(it, Base64.DEFAULT) }
            jpeg?.let { BitmapFactory.decodeByteArray(it, 0, it.size) }?.let { screen = it.asImageBitmap() }
            if (jpeg == null) say(error.ifBlank { "Your PC couldn't show its screen." }, Who.NOTE)
            refresh()
        }
    }

    fun media(action: String) {
        post("/api/media/$action") { _, _ -> main.postDelayed(::loadPc, 700) }
    }
}

/** What the app asked the PC and has no answer for yet, across drops of the link. The PC carries on meanwhile and keeps
 *  its answers, so asking again would do it twice (an event made, a message sent): once the link is back the hello names
 *  what's still waited for, the PC sends those answers again, and its ready says which it doesn't know (it restarted).
 *  Only those are let go, or all the hello named when an older PC can't say ("Working on it…" mustn't stay for good). */
internal class Asks {
    private val waiting = mutableSetOf<Int>()
    private val told = mutableSetOf<Int>()  // the app said their answers come once the link is back
    private var named = emptySet<Int>()     // what the last hello named: the ready that follows answers for these

    val any get() = waiting.isNotEmpty()

    fun sent(id: Int) {
        waiting += id
    }

    fun answered(id: Int) {
        waiting -= id
        told -= id
    }

    fun clear() {
        waiting.clear()
        told.clear()
        named = emptySet()
    }

    /** The link is down: true the first time these are left waiting (the app says their answers will come). */
    fun dropped(): Boolean = (waiting - told).isNotEmpty().also { told += waiting }

    /** For the hello, once the link is back: what the app still waits for. */
    fun hello(): List<Int> = waiting.sorted().also { named = it.toSet() }

    /** The PC's ready: [lost] what it doesn't know of what the hello named (null: an older PC, which doesn't say).
     *  Returns the ones no answer will come for, waited for no more. */
    fun back(lost: Collection<Int>?): List<Int> {
        val gone = named.filter { it in waiting && (lost == null || it in lost) }
        gone.forEach(::answered)
        named = emptySet()
        return gone
    }
}

/** A ready's `lost` (what the PC doesn't know of what the app waits for); null from an older PC, which doesn't say. */
internal fun lost(ready: JSONObject): List<Int>? = ready.optJSONArray("lost")?.let { a -> (0 until a.length()).map { a.optInt(it) } }
