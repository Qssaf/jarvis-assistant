package com.jarvis.assistant

import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions

/** The screens over [Jarvis] (which does the work, and outlives this while the service runs). */
class MainActivity : ComponentActivity() {
    private val scan = registerForActivityResult(ScanContract()) { result -> result.contents?.let(Jarvis::pair) }
    private var afterPermission: (() -> Unit)? = null
    private val permission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        // (notifications refused: Jarvis still works, just without them; the microphone refused: nothing to go on with)
        if (granted || askedFor == android.Manifest.permission.POST_NOTIFICATIONS) afterPermission?.invoke()
        afterPermission = null
    }
    private var askedFor = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge(SystemBarStyle.dark(Color.TRANSPARENT), SystemBarStyle.dark(Color.TRANSPARENT))
        super.onCreate(savedInstanceState)
        Jarvis.init(this)
        val actions = Actions(
            ask = Jarvis::ask, talk = Jarvis::talk, stop = Jarvis::stop,
            scan = { scan.launch(ScanOptions().setPrompt("Scan the code in Jarvis's Settings on your PC").setBeepEnabled(false).setOrientationLocked(false)) },
            pair = Jarvis::pair, saveKey = Jarvis::saveKey, unpair = Jarvis::unpair,
            setWake = Jarvis::setWake, setBackground = Jarvis::setBackground, media = Jarvis::media,
            loadToday = Jarvis::loadToday, loadPc = Jarvis::loadPc, loadScreen = Jarvis::loadScreen, newChat = Jarvis::newChat, stopJob = Jarvis::stopJob,
        )
        setContent { JarvisApp(Jarvis.ui, actions, level = { Jarvis.level.floatValue }) }
        opened(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        opened(intent)
    }

    /** What the app was opened with: a pairing link, something shared from another app, or the assistant gesture. */
    private fun opened(intent: Intent?) {
        when (intent?.action) {
            Intent.ACTION_VIEW -> intent.dataString?.takeIf { it.startsWith("jarvis://pair") }?.let(Jarvis::pairFromLink)
            Intent.ACTION_SEND -> intent.getStringExtra(Intent.EXTRA_TEXT)?.takeIf { it.isNotBlank() }?.let(Jarvis::share)
            Intent.ACTION_ASSIST, Intent.ACTION_VOICE_COMMAND -> if (Jarvis.ui.paired && Jarvis.ui.voice == Voice.OFF) Jarvis.talk()
        }
        intent?.action = null  // (a rotation mustn't share or pair again)
    }

    override fun onStart() {
        super.onStart()
        Jarvis.askPermission = { name, then ->
            if (checkSelfPermission(name) == PackageManager.PERMISSION_GRANTED) then()
            else {
                askedFor = name
                afterPermission = then
                permission.launch(name)
            }
        }
        Jarvis.foreground = true
        Jarvis.hold()
        Jarvis.syncService()  // (now the service may take the microphone for the wake word)
    }

    override fun onStop() {
        super.onStop()
        Jarvis.foreground = false
        Jarvis.askPermission = { _, _ -> }
        Jarvis.release()
    }
}
