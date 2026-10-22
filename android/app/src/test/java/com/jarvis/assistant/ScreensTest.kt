package com.jarvis.assistant

import app.cash.paparazzi.DeviceConfig
import app.cash.paparazzi.Paparazzi
import com.android.resources.NightMode
import org.junit.Rule
import org.junit.Test

/** Renders the screens with made-up data (build/reports/paparazzi), for design work: nothing is compared. */
class ScreensTest {
    @get:Rule
    val paparazzi = Paparazzi(deviceConfig = DeviceConfig.PIXEL_6.copy(nightMode = NightMode.NIGHT), theme = "android:Theme.Material.NoActionBar", useDeviceResolution = true)

    private val online = Ui(paired = true, state = State.ONLINE, pc = "studio-pc", relay = "jarvis-relay.example.workers.dev", version = "1.14.0")
    private val chat = listOf(
        Msg(1, Who.YOU, "What's due this week?"),
        Msg(2, Who.JARVIS, "Two things: the **Calculus problem set** on Wednesday at 11:59 pm, and the History essay draft on Friday. " +
            "The problem set is the bigger one, about 12 questions."),
        Msg(3, Who.YOU, "Remind me tomorrow at 6 to start it"),
        Msg(4, Who.NOTE, "Busy with another task — yours is next."),
        Msg(5, Who.JARVIS, "Done. I'll remind you tomorrow at six."),
        Msg(6, Who.YOU, "Find me a good lo-fi playlist and play it on the PC"),
    )

    @Test fun onboarding() = paparazzi.snapshot { JarvisApp(Ui(version = "1.14.0"), Actions()) }

    @Test fun empty() = paparazzi.snapshot { JarvisApp(online, Actions()) }

    @Test fun conversation() = paparazzi.snapshot { JarvisApp(online.copy(messages = chat.take(5)), Actions()) }

    @Test fun working() = paparazzi.snapshot { JarvisApp(online.copy(messages = chat, working = true), Actions()) }

    @Test fun offline() = paparazzi.snapshot {
        JarvisApp(online.copy(state = State.PC_OFFLINE, key = "fake-key", messages = listOf(
            Msg(1, Who.YOU, "How long should I boil an egg for a jammy yolk?"),
            Msg(2, Who.PHONE, "About six and a half minutes from boiling water, then straight into ice water for a minute. " +
                "I can't reach your PC right now, so I can't set a timer there."),
        )), Actions())
    }

    @Test fun settings() = paparazzi.snapshot { JarvisApp(online.copy(messages = chat.take(2), key = "fake-key-for-the-picture"), Actions(), sheetOpen = true) }
}
