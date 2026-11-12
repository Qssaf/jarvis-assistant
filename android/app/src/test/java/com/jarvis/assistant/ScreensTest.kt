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

    @Test fun settings() = paparazzi.snapshot {
        JarvisApp(online.copy(messages = chat.take(2), key = "fake-key-for-the-picture", direct = true, wake = true), Actions(), sheetOpen = true)
    }

    @Test fun listening() = paparazzi.snapshot { JarvisApp(online.copy(voice = Voice.LISTENING, wake = true), Actions(), level = { 0.6f }) }

    @Test fun speaking() = paparazzi.snapshot {
        JarvisApp(online.copy(messages = chat.take(5), voice = Voice.LISTENING, speaking = true), Actions())
    }

    @Test fun today() = paparazzi.snapshot {
        JarvisApp(online.copy(loaded = true, weather = Weather("Lisbon", "", "19°C", "Partly cloudy"), reminders = listOf(
            Reminder("Start the Calculus problem set", "Wed 11 Nov, 18:00"), Reminder("Call the dentist", "Thu 12 Nov, 09:30"),
            Reminder("Water the plants", "Sat 14 Nov, 10:00 · weekly"))), Actions(), tab = Tab.TODAY)
    }

    @Test fun pc() = paparazzi.snapshot {
        JarvisApp(online.copy(loaded = true, direct = true, playing = Playing("Midnight City", "M83", "Spotify", true),
            stats = Pc(cpu = 12, memory = 46, disk = 91, uptime = "3 days"), jobs = listOf(
                Job(3, "Find flights to Lisbon for the first week of June", "Searching the web", 3), Job(4, "Fix the failing date test", "", 24))),
            Actions(), tab = Tab.PC)
    }

    @Test fun outOfReach() = paparazzi.snapshot {
        JarvisApp(online.copy(state = State.PC_OFFLINE, relay = "", note = "Your PC isn't on this network. Set up the relay in its Settings to reach it from anywhere."),
            Actions(), tab = Tab.PC)
    }
}
