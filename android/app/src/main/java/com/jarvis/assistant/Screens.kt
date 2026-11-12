package com.jarvis.assistant


import android.view.HapticFeedbackConstants
import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.Crossfade
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicText
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.selection.LocalTextSelectionColors
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.text.selection.TextSelectionColors
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.minimumInteractiveComponentSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.time.LocalDate
import java.time.LocalTime
import java.time.format.DateTimeFormatter

enum class Who { YOU, JARVIS, PHONE, NOTE }
enum class Voice { OFF, STARTING, LISTENING }
enum class Tab { TALK, TODAY, PC }

data class Msg(val id: Int, val who: Who, val text: String)
data class Weather(val place: String, val icon: String, val temp: String, val condition: String)
data class Reminder(val text: String, val time: String)
data class Playing(val title: String, val artist: String, val app: String, val playing: Boolean)
data class Pc(val cpu: Int, val memory: Int, val disk: Int, val uptime: String)
data class Job(val n: Int, val label: String, val now: String, val minutes: Int)  // a task running on the PC: its number there, what it does right now

/** Everything the screens show: plain values, so they render the same from the app or from fake data. */
data class Ui(
    val paired: Boolean = false,
    val state: State = State.UNPAIRED,
    val note: String = "",  // why pairing failed, or why the PC can't be reached
    val pc: String = "",
    val relay: String = "",
    val direct: Boolean = false,  // connected straight to the PC (the same network), not through the relay
    val messages: List<Msg> = emptyList(),
    val working: Boolean = false,
    val activity: String = "",  // what the PC is doing for that task right now ("Reading your screen")
    val key: String = "",
    val version: String = "",
    val voice: Voice = Voice.OFF,
    val speaking: Boolean = false,
    val onPhone: Boolean = false,  // talking with Gemini on the phone, the PC being out of reach
    val wake: Boolean = false,
    val wakePhrase: String = "Hey Jarvis",
    val wakeNote: String = "",
    val background: Boolean = false,
    val weather: Weather? = null,
    val reminders: List<Reminder> = emptyList(),
    val playing: Playing? = null,
    val stats: Pc? = null,
    val jobs: List<Job> = emptyList(),
    val screen: ImageBitmap? = null,
    val screenLoading: Boolean = false,
    val loaded: Boolean = false,  // the PC has answered for the Today and PC pages
    val draft: String = "",  // shared from another app: waits in the box
)

class Actions(
    val ask: (String) -> Unit = {},
    val talk: () -> Unit = {},
    val stop: () -> Unit = {},
    val scan: () -> Unit = {},
    val pair: (String) -> Unit = {},
    val saveKey: (String) -> Unit = {},
    val unpair: () -> Unit = {},
    val setWake: (Boolean) -> Unit = {},
    val setBackground: (Boolean) -> Unit = {},
    val media: (String) -> Unit = {},
    val loadToday: () -> Unit = {},
    val loadPc: () -> Unit = {},
    val loadScreen: () -> Unit = {},
    val newChat: () -> Unit = {},
    val stopJob: (Int) -> Unit = {},
)

/** What an empty list on the Today or PC page says: there's nothing, or the PC hasn't answered (yet). */
internal fun emptyNote(ui: Ui, none: String) = when {
    ui.loaded -> none
    ui.state == State.ONLINE || ui.state == State.CONNECTING -> "Asking your PC…"
    else -> "Your PC is out of reach."
}

@Composable
fun JarvisApp(ui: Ui, act: Actions, sheetOpen: Boolean = false, tab: Tab = Tab.TALK, level: () -> Float = { 0f }) {
    var sheet by remember { mutableStateOf(sheetOpen) }
    CompositionLocalProvider(LocalTextSelectionColors provides TextSelectionColors(J.accent, J.accentSoft)) {
        Backdrop(working = ui.working || ui.speaking) {
            Crossfade(ui.paired, animationSpec = tween(200), label = "screen") { paired ->
                if (paired) Main(ui, act, tab, level) { sheet = true } else Onboarding(ui, act)
            }
            Sheet(sheet && ui.paired, { sheet = false }) { Settings(ui, act) { sheet = false } }
        }
    }
}

// ---- onboarding

@Composable
private fun Onboarding(ui: Ui, act: Actions) {
    BoxWithConstraints(Modifier.fillMaxSize().systemBarsPadding().imePadding()) {
        Column(
            Modifier.verticalScroll(rememberScrollState()).heightIn(min = maxHeight).padding(horizontal = 20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Spacer(Modifier.weight(1f).heightIn(min = 16.dp))
            Reactor(220.dp)
            Spacer(Modifier.height(12.dp))
            Text("Jarvis, on your phone", J.title, align = TextAlign.Center)
            Spacer(Modifier.height(10.dp))
            Text("Ask the Jarvis on your PC anything, from anywhere. Private, end to end.", J.body.copy(color = J.text2),
                align = TextAlign.Center, modifier = Modifier.widthIn(max = 300.dp))
            Spacer(Modifier.height(32.dp))
            Card {
                Step(1, md("On your PC, open\n**Settings → The Jarvis app**"))
                Divider()
                Step(2, md("Tap **Pair a phone**"))
                Divider()
                Step(3, md("Scan the code with this phone"))
            }
            Spacer(Modifier.weight(0.8f).heightIn(min = 28.dp))
            if (ui.note.isNotBlank()) {
                Text(ui.note, J.small.copy(color = J.warm), align = TextAlign.Center, modifier = Modifier.padding(bottom = 14.dp))
            }
            PastePair(act) { paste ->
                Primary("Scan pairing code", Ico.scan, Modifier.fillMaxWidth(), height = 48.dp, onClick = act.scan)
                Spacer(Modifier.height(6.dp))
                Ghost("Paste a pairing link", Modifier.fillMaxWidth(), paste)
            }
            Spacer(Modifier.height(12.dp))
        }
    }
}

@Composable
private fun Step(n: Int, text: AnnotatedString) {
    Row(Modifier.fillMaxWidth().padding(vertical = 14.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(28.dp).background(J.accentSoft, CircleShape), contentAlignment = Alignment.Center) {
            Text("$n", J.label.copy(color = J.accent, fontSize = 13.sp))
        }
        Spacer(Modifier.width(14.dp))
        BasicText(text, style = J.body.copy(color = J.text2))
    }
}

/** A pairing link pasted by hand: the field opens under [content]'s buttons, filled from the clipboard when it holds one. */
@Composable
private fun PastePair(act: Actions, content: @Composable ColumnScope.(paste: () -> Unit) -> Unit) {
    val clipboard = LocalClipboardManager.current
    var open by remember { mutableStateOf(false) }
    var link by remember { mutableStateOf("") }
    Column(Modifier.fillMaxWidth()) {
        AnimatedVisibility(open, enter = fadeIn(tween(160)) + expandVertically(tween(200)), exit = fadeOut(tween(140)) + shrinkVertically(tween(200))) {
            Row(Modifier.padding(bottom = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                Field(link, { link = it }, "jarvis://pair#…", Modifier.weight(1f), done = { act.pair(link) })
                Spacer(Modifier.width(10.dp))
                Primary("Pair", null, enabled = link.isNotBlank()) { act.pair(link); open = false }
            }
        }
        content {
            link = clipboard.getText()?.text?.trim()?.takeIf { it.startsWith("jarvis://pair") } ?: link
            open = !open
        }
    }
}

// ---- main

@Composable
private fun Main(ui: Ui, act: Actions, first: Tab, level: () -> Float, onMenu: () -> Unit) {
    var tab by remember { mutableStateOf(first) }
    LaunchedEffect(ui.draft) { if (ui.draft.isNotBlank()) tab = Tab.TALK }
    LaunchedEffect(tab, ui.state) {
        if (ui.state == State.ONLINE) when (tab) { Tab.TODAY -> act.loadToday(); Tab.PC -> act.loadPc(); Tab.TALK -> {} }
    }
    val ask = { text: String -> tab = Tab.TALK; act.ask(text) }
    Column(Modifier.fillMaxSize().statusBarsPadding().imePadding()) {
        TopBar(ui, onMenu)
        AnimatedVisibility(ui.state == State.PC_OFFLINE || ui.state == State.NO_RELAY,
            enter = fadeIn() + expandVertically(), exit = fadeOut() + shrinkVertically()) { Banner(ui, onMenu) }
        Crossfade(tab, Modifier.weight(1f).fillMaxWidth(), tween(160), label = "tab") { shown ->
            when (shown) {
                Tab.TALK -> Talk(ui, act, level)
                Tab.TODAY -> Today(ui, ask)
                Tab.PC -> PcPage(ui, act, ask)
            }
        }
        BottomNav(tab) { tab = it }
    }
}

@Composable
private fun TopBar(ui: Ui, onMenu: () -> Unit) {
    // (insets put the mini reactor's ring and the overflow dots on the 20dp gutter)
    Row(Modifier.fillMaxWidth().height(60.dp).padding(start = 18.dp, end = 7.dp), verticalAlignment = Alignment.CenterVertically) {
        val phoneOnly = ui.state != State.ONLINE && ui.key.isNotBlank()
        Reactor(24.dp, working = ui.working || ui.speaking, dim = !online(ui), mini = true, modifier = Modifier.graphicsLayer { alpha = if (phoneOnly) 0.5f else 1f })
        Spacer(Modifier.width(12.dp))
        Text("Jarvis", J.heading)
        Spacer(Modifier.weight(1f).widthIn(min = 12.dp))
        StatusChip(ui, Modifier.widthIn(max = 210.dp))
        Spacer(Modifier.width(6.dp))
        Box(Modifier.size(40.dp).minimumInteractiveComponentSize().clip(CircleShape).press(label = "Settings", onClick = onMenu), contentAlignment = Alignment.Center) {
            Icon(Ico.more, J.text2, 22.dp)
        }
    }
}

private fun online(ui: Ui) = ui.state == State.ONLINE || ui.key.isNotBlank()

private fun status(ui: Ui): Pair<Color, String> = when (ui.state) {
    State.ONLINE -> J.green to "Connected · ${ui.pc.ifBlank { "your PC" }}"
    State.CONNECTING -> J.text3 to "Connecting…"
    State.PC_OFFLINE -> if (ui.key.isNotBlank()) J.warm to "Phone only" else J.text3 to "PC out of reach"
    State.NO_RELAY -> J.red to "Relay unreachable"
    State.UNPAIRED -> J.text3 to "Not paired"
}

@Composable
private fun StatusChip(ui: Ui, modifier: Modifier = Modifier) {
    val (color, label) = status(ui)
    Row(modifier.height(32.dp).glass(CircleShape).padding(horizontal = 12.dp), verticalAlignment = Alignment.CenterVertically) {
        Dot(color, glow = ui.state == State.ONLINE)
        Spacer(Modifier.width(8.dp))
        Text(label, J.small, maxLines = 1)
    }
}

@Composable
private fun Dot(color: Color, glow: Boolean = false, pulse: Boolean = false) {
    val a = if (pulse) rememberInfiniteTransition(label = "dot").animateFloat(1f, 0.35f,
        infiniteRepeatable(tween(700, easing = FastOutSlowInEasing), RepeatMode.Reverse), label = "dot").value else 1f
    Box(Modifier.size(8.dp).drawBehind {
        if (glow) drawCircle(Brush.radialGradient(listOf(color.copy(alpha = 0.5f), Color.Transparent), center, size.minDimension * 1.3f), size.minDimension * 1.3f)
        drawCircle(color.copy(alpha = a))
    })
}

@Composable
private fun Banner(ui: Ui, openSettings: () -> Unit) {
    val relay = ui.state == State.NO_RELAY
    val key = ui.key.isNotBlank()
    val tint = if (relay) J.red else J.warm
    Row(Modifier.padding(start = 20.dp, end = 20.dp, bottom = 8.dp).fillMaxWidth().clip(RoundedCornerShape(20.dp))
        .background(tint.copy(alpha = 0.08f)).border(1.dp, tint.copy(alpha = 0.2f), RoundedCornerShape(20.dp))
        .then(if (key) Modifier else Modifier.press(onClick = openSettings)).padding(horizontal = 14.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically) {
        Icon(if (relay) Ico.cloudOff else Ico.power, tint, 18.dp)
        Spacer(Modifier.width(12.dp))
        val what = if (relay) "Can't reach your relay" + (if (ui.note.isNotBlank()) " (${ui.note})" else "") else "Your PC is out of reach"
        BasicText(buildAnnotatedString {
            withStyle(SpanStyle(color = J.text, fontWeight = FontWeight.Medium)) { append(what) }
            if (key) append(" — Gemini answers on the phone")
            else {
                append(". ${if (relay || ui.note.isBlank()) "Nothing can run until it's back." else ui.note} ")
                withStyle(SpanStyle(color = J.accent, fontWeight = FontWeight.Medium)) { append("Add a Gemini key") }
            }
        }, style = J.small.copy(color = J.text2))
    }
}

// ---- talk

@Composable
private fun Talk(ui: Ui, act: Actions, level: () -> Float) {
    Box(Modifier.fillMaxSize()) {
        if (ui.messages.isEmpty() && !ui.working) Empty(ui, act, level) else Conversation(ui, act.stop)
        Column(Modifier.align(Alignment.BottomCenter).fillMaxWidth()
            .background(Brush.verticalGradient(0f to Color.Transparent, 0.4f to J.bgBottom.copy(alpha = 0.85f), 1f to J.bgBottom))
            .padding(start = 20.dp, end = 20.dp, top = 20.dp, bottom = 12.dp)) {
            Crossfade(ui.voice != Voice.OFF, animationSpec = tween(160), label = "composer") { talking ->
                if (talking) VoiceBar(ui, act, level) else Composer(ui, act)
            }
        }
    }
}

private val SUGGESTIONS = listOf(
    Triple(Ico.calendar, "What's due soon?", "Classroom and calendar"),
    Triple(Ico.screen, "What's on my screen?", "A look at your PC"),
    Triple(Ico.mute, "Mute my PC", "Volume and media"),
    Triple(Ico.mail, "Any new emails?", "Your inbox, summed up"),
)

@Composable
private fun Empty(ui: Ui, act: Actions, level: () -> Float) {
    val hour = remember { LocalTime.now().hour }
    val talking = ui.voice != Voice.OFF
    // (fills the height so the group sits a little above centre, ending clear of the composer)
    BoxWithConstraints(Modifier.fillMaxSize()) { Column(Modifier.verticalScroll(rememberScrollState()).heightIn(min = maxHeight)
        .padding(start = 20.dp, end = 20.dp, top = 16.dp, bottom = 100.dp),
        horizontalAlignment = Alignment.CenterHorizontally) {
        Spacer(Modifier.weight(1f))
        // the orb is the way in to talking: it swells with the user's voice while Jarvis listens
        Box(Modifier.clip(CircleShape).press(label = if (talking) "Stop talking with Jarvis" else "Talk with Jarvis", onClick = act.talk)
            .graphicsLayer { val s = 1f + (if (talking) level() else 0f) * 0.12f; scaleX = s; scaleY = s }) {
            Reactor(150.dp, working = ui.working || ui.speaking, dim = !online(ui))
        }
        Spacer(Modifier.height(20.dp))
        Text(when {
            ui.speaking -> "Jarvis"
            ui.voice == Voice.LISTENING -> "Listening…"
            ui.voice == Voice.STARTING -> "One moment…"
            else -> when (hour) { in 5..11 -> "Good morning"; in 12..17 -> "Good afternoon"; else -> "Good evening" }
        }, J.display)
        Spacer(Modifier.height(8.dp))
        Text(when {
            talking -> "Tap the orb when you're done."
            ui.state != State.ONLINE -> "Ask anything. Jarvis answers as soon as it can."
            ui.wake -> "Say “${ui.wakePhrase}”, tap the orb, or type. Your PC does the work."
            else -> "Tap the orb to talk, or type. Your PC does the work."
        }, J.body.copy(color = J.text2), align = TextAlign.Center)
        Spacer(Modifier.height(36.dp))
        SUGGESTIONS.chunked(2).forEach { row ->
            Row(Modifier.fillMaxWidth().height(IntrinsicSize.Min).padding(bottom = 12.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                row.forEach { (icon, title, sub) ->
                    Column(Modifier.weight(1f).fillMaxHeight().glass(RoundedCornerShape(20.dp)).press { act.ask(title) }.padding(16.dp)) {
                        Box(Modifier.size(36.dp).background(J.accentSoft, CircleShape), contentAlignment = Alignment.Center) { Icon(icon, J.accent, 18.dp) }
                        Spacer(Modifier.weight(1f).heightIn(min = 14.dp))
                        Text(title, J.button.copy(lineHeight = 19.sp), maxLines = 1)
                        Spacer(Modifier.height(3.dp))
                        Text(sub, J.label.copy(fontWeight = FontWeight.Normal, letterSpacing = 0.sp), maxLines = 1)
                    }
                }
            }
        }
        Spacer(Modifier.weight(0.15f))
    } }
}

@Composable
private fun Conversation(ui: Ui, stop: () -> Unit) {
    val seen = remember { ui.messages.map { it.id }.toMutableSet() }  // (only messages that arrive later animate in)
    var wasWorking by remember { mutableStateOf(ui.working) }
    SideEffect { if (!ui.working) wasWorking = false }
    LazyColumn(Modifier.fillMaxSize(), reverseLayout = true,
        contentPadding = PaddingValues(start = 20.dp, end = 20.dp, top = 12.dp, bottom = 112.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp, Alignment.Bottom)) {
        if (ui.working) item(key = "working") { Arrive(!wasWorking) { Working(ui.activity, stop) } }
        items(ui.messages.asReversed(), key = { it.id }) { m ->
            Arrive(remember(m.id) { seen.add(m.id) }) { Message(m) }
        }
    }
}

@Composable
private fun Arrive(fresh: Boolean, content: @Composable () -> Unit) {
    if (!fresh) return content()
    val a = remember { Animatable(0f) }
    LaunchedEffect(Unit) { a.animateTo(1f, tween(220, easing = FastOutSlowInEasing)) }
    Box(Modifier.graphicsLayer { alpha = a.value; translationY = (1 - a.value) * 8.dp.toPx() }) { content() }
}

@Composable
private fun Message(m: Msg) {
    when (m.who) {
        Who.YOU -> Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.CenterEnd) {
            Box(Modifier.fillMaxWidth(0.8f), contentAlignment = Alignment.CenterEnd) {
                val shape = RoundedCornerShape(20.dp, 20.dp, 6.dp, 20.dp)
                SelectionContainer {
                    Text(m.text, J.chat, modifier = Modifier.clip(shape).background(J.accentSoft).border(1.dp, J.accent.copy(alpha = 0.25f), shape)
                        .padding(horizontal = 15.dp, vertical = 10.dp))
                }
            }
        }
        Who.NOTE -> Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
            Text(m.text, J.small.copy(color = J.text3), align = TextAlign.Center, modifier = Modifier.widthIn(max = 280.dp).padding(vertical = 4.dp))
        }
        else -> Row(Modifier.fillMaxWidth().padding(end = 12.dp)) {
            Reactor(24.dp, mini = true)
            Spacer(Modifier.width(12.dp))
            Column {
                SelectionContainer { BasicText(md(m.text), style = J.chat) }
                if (m.who == Who.PHONE) Row(Modifier.padding(top = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                    Icon(Ico.phone, J.text3, 12.dp)
                    Spacer(Modifier.width(4.dp))
                    Text("on phone", J.label.copy(color = J.text3, fontSize = 11.sp))
                }
            }
        }
    }
}

@Composable
private fun Working(activity: String, stop: () -> Unit) {
    val shift by rememberInfiniteTransition(label = "shimmer").animateFloat(-1f, 2f,
        infiniteRepeatable(tween(1600, easing = LinearEasing)), label = "shimmer")
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Reactor(24.dp, working = true, mini = true)
        Spacer(Modifier.width(12.dp))
        Row(Modifier.weight(1f, fill = false).height(32.dp).glass(CircleShape).padding(horizontal = 13.dp), verticalAlignment = Alignment.CenterVertically) {
            Dot(J.warm, glow = true, pulse = true)
            Spacer(Modifier.width(9.dp))
            BasicText(activity.ifBlank { "Working on it" } + "…", maxLines = 1, overflow = TextOverflow.Ellipsis, style = J.small.copy(brush = Brush.linearGradient(
                listOf(J.text2, J.text2, J.text, J.text2, J.text2), Offset(shift * 260f - 260f, 0f), Offset(shift * 260f + 260f, 0f))))
        }
        Spacer(Modifier.width(12.dp))
        StopChip(stop)
    }
}

@Composable
private fun StopChip(onClick: () -> Unit) {
    Row(Modifier.height(32.dp).glass(CircleShape).press(onClick = onClick).padding(horizontal = 14.dp),
        verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(8.dp).background(J.warm, RoundedCornerShape(2.dp)))
        Spacer(Modifier.width(8.dp))
        Text("Stop", J.button.copy(color = J.warm, fontSize = 13.sp))
    }
}

@Composable
private fun Composer(ui: Ui, act: Actions) {
    var text by remember(ui.draft) { mutableStateOf(ui.draft) }
    val view = LocalView.current
    val send = {
        if (text.isNotBlank()) {
            view.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
            act.ask(text.trim())
            text = ""
        }
    }
    Row(Modifier.fillMaxWidth().heightIn(min = 56.dp).floating(RoundedCornerShape(28.dp)).padding(start = 20.dp, end = 8.dp, top = 8.dp, bottom = 8.dp),
        verticalAlignment = Alignment.CenterVertically) {
        BasicTextField(text, { text = it }, Modifier.weight(1f).padding(vertical = 6.dp), textStyle = J.chat, maxLines = 5,
            cursorBrush = SolidColor(J.accent),
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send), keyboardActions = KeyboardActions(onSend = { send() }),
            decorationBox = { inner -> Box { if (text.isEmpty()) Text("Ask Jarvis", J.chat.copy(color = J.text2)); inner() } })
        Spacer(Modifier.width(8.dp))
        Round(Ico.mic, "Talk with Jarvis", Color(0x12FFFFFF), J.text, act.talk)
        AnimatedVisibility(text.isNotBlank(), enter = fadeIn(tween(140)) + scaleIn(tween(140), 0.6f), exit = fadeOut(tween(140)) + scaleOut(tween(140), 0.6f)) {
            Row { Spacer(Modifier.width(8.dp)); Round(Ico.send, "Send", J.accent, J.accentInk, send) }
        }
    }
}

/** In place of the composer while talking: what Jarvis is doing, a tap to cut in or to finish. */
@Composable
private fun VoiceBar(ui: Ui, act: Actions, level: () -> Float) {
    val label = when {
        ui.voice == Voice.STARTING -> "Reaching Jarvis…"
        ui.speaking -> "Jarvis is speaking · tap to cut in"
        ui.onPhone -> "Listening, on this phone"
        else -> "Listening…"
    }
    Row(Modifier.fillMaxWidth().height(56.dp).floating(RoundedCornerShape(28.dp)).press(label = label, onClick = act.talk).padding(start = 16.dp, end = 8.dp),
        verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.graphicsLayer { val s = 1f + level() * 0.5f; scaleX = s; scaleY = s }) { Reactor(26.dp, working = ui.speaking, mini = true) }
        Spacer(Modifier.width(14.dp))
        Text(label, J.chat.copy(color = if (ui.speaking) J.text else J.listen), Modifier.weight(1f), maxLines = 1)
        if (!ui.speaking) Round(Ico.close, "Stop talking with Jarvis", Color(0x12FFFFFF), J.text, act.talk)
    }
}

@Composable
private fun Round(icon: ImageVector, label: String, fill: Color, tint: Color, onClick: () -> Unit, size: Dp = 40.dp, iconSize: Dp = 20.dp) {
    Box(Modifier.minimumInteractiveComponentSize().size(size).clip(CircleShape).background(fill).press(label = label, onClick = onClick),
        contentAlignment = Alignment.Center) { Icon(icon, tint, iconSize) }
}

@Composable
private fun BottomNav(tab: Tab, onTab: (Tab) -> Unit) {
    Row(Modifier.fillMaxWidth().background(J.bgBottom).drawBehind { drawLine(J.stroke, Offset.Zero, Offset(size.width, 0f), 1.dp.toPx()) }
        .navigationBarsPadding().height(60.dp).selectableGroup()) {
        listOf(Triple(Tab.TALK, Ico.mic, "Talk"), Triple(Tab.TODAY, Ico.calendar, "Today"), Triple(Tab.PC, Ico.screen, "PC")).forEach { (t, icon, name) ->
            val tint by animateColorAsState(if (t == tab) J.accent else J.text2, tween(160), label = "tab")
            Column(Modifier.weight(1f).fillMaxHeight().selectable(t == tab, remember { MutableInteractionSource() }, null, role = Role.Tab) { onTab(t) },
                horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                Icon(icon, tint, 22.dp)
                Spacer(Modifier.height(4.dp))
                Text(name, J.label.copy(color = tint))
            }
        }
    }
}

// ---- today, and the PC

@Composable
private fun Page(content: @Composable ColumnScope.() -> Unit) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(start = 20.dp, end = 20.dp, top = 8.dp, bottom = 24.dp), content = content)
}

@Composable
private fun Heading(text: String) = Text(text, J.heading, Modifier.padding(top = 28.dp, bottom = 10.dp))

/** A row of a list card that does something when tapped. */
@Composable
private fun Do(icon: ImageVector, text: String, tint: Color = J.text, onClick: () -> Unit) {
    Row(Modifier.fillMaxWidth().heightIn(min = 52.dp).press(onClick = onClick), verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, if (tint == J.text) J.accent else tint, 20.dp)
        Spacer(Modifier.width(14.dp))
        Text(text, J.body.copy(color = tint), Modifier.weight(1f))
    }
}

@Composable
private fun OutOfReach(ui: Ui, what: String) {
    // (out of reach for good: the banner above says so, and why)
    if (ui.state == State.CONNECTING) Text("$what comes from your PC: reaching it…", J.body.copy(color = J.text2), Modifier.padding(top = 12.dp))
}

@Composable
private fun Today(ui: Ui, ask: (String) -> Unit) {
    val hour = remember { LocalTime.now().hour }
    Page {
        Text(when (hour) { in 5..11 -> "Good morning"; in 12..17 -> "Good afternoon"; else -> "Good evening" }, J.title)
        Spacer(Modifier.height(4.dp))
        Text(remember { LocalDate.now().format(DateTimeFormatter.ofPattern("EEEE d MMMM")) } +
            (ui.weather?.let { " · ${it.temp} ${it.condition.trim().lowercase()}" + (if (it.place.isBlank()) "" else " in ${it.place}") } ?: ""), J.body.copy(color = J.text2))
        OutOfReach(ui, "Today")
        Heading("Coming up")
        Card {
            if (ui.reminders.isEmpty()) Text(emptyNote(ui, "No reminders set."), J.body.copy(color = J.text2), Modifier.padding(vertical = 6.dp))
            ui.reminders.forEachIndexed { i, r ->
                if (i > 0) Divider()
                Column(Modifier.padding(vertical = 10.dp)) {
                    Text(r.text, J.body)
                    Spacer(Modifier.height(2.dp))
                    Text(r.time, J.small)
                }
            }
        }
        Heading("Ask Jarvis")
        Card {
            Do(Ico.calendar, "Give me my briefing") { ask("Give me my briefing") }
            Divider()
            Do(Ico.check, "What's due soon?") { ask("What's due soon?") }
            Divider()
            Do(Ico.mail, "Any new emails?") { ask("Any new emails?") }
            Divider()
            Do(Ico.phone, "Who's waiting on me?") { ask("Who's waiting on me?") }
        }
    }
}

@Composable
private fun PcPage(ui: Ui, act: Actions, ask: (String) -> Unit) {
    Page {
        Text(ui.pc.ifBlank { "Your PC" }, J.title)
        Spacer(Modifier.height(4.dp))
        Text(when {
            ui.state != State.ONLINE -> status(ui).second
            ui.direct -> "Connected directly, on the same network"
            else -> "Connected through your relay"
        }, J.body.copy(color = J.text2))
        OutOfReach(ui, "This page")
        if (ui.jobs.isNotEmpty()) {  // what Jarvis is doing there, each with its own Stop (the others carry on)
            Heading("Working on")
            Card {
                ui.jobs.forEachIndexed { i, job ->
                    if (i > 0) Divider()
                    Row(Modifier.fillMaxWidth().heightIn(min = 56.dp).padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(job.label, J.body, maxLines = 2)
                            Spacer(Modifier.height(2.dp))
                            Text(listOf(job.now, if (job.minutes > 0) "${job.minutes} min" else "Just started").filter { it.isNotBlank() }.joinToString(" · "), J.small, maxLines = 1)
                        }
                        Spacer(Modifier.width(8.dp))
                        Round(Ico.close, "Stop this task", J.glass, J.warm, { act.stopJob(job.n) }, size = 36.dp, iconSize = 16.dp)
                    }
                }
            }
        }
        Heading("Playing")
        Card {
            val p = ui.playing
            if (p == null) Text(emptyNote(ui, "Nothing is playing."), J.body.copy(color = J.text2), Modifier.padding(vertical = 6.dp))
            else {
                Text(p.title, J.heading.copy(fontSize = 15.sp), maxLines = 2)
                Spacer(Modifier.height(2.dp))
                Text(listOf(p.artist, p.app).filter { it.isNotBlank() }.joinToString(" · "), J.small, maxLines = 1)
                Row(Modifier.fillMaxWidth().padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterHorizontally),
                    verticalAlignment = Alignment.CenterVertically) {
                    Round(Ico.previous, "Previous", J.glass, J.text, { act.media("Previous") })
                    Round(if (p.playing) Ico.pause else Ico.play, if (p.playing) "Pause" else "Play", J.accent, J.accentInk, { act.media("PlayPause") }, size = 48.dp, iconSize = 22.dp)
                    Round(Ico.next, "Next", J.glass, J.text, { act.media("Next") })
                }
            }
        }
        Heading("Screen")
        Card {
            ui.screen?.let {
                Image(it, "Your PC's screen", Modifier.fillMaxWidth().aspectRatio(it.width.toFloat() / it.height.coerceAtLeast(1)).clip(RoundedCornerShape(10.dp)))
                Spacer(Modifier.height(12.dp))
            }
            Do(Ico.screen, if (ui.screenLoading) "Looking…" else if (ui.screen == null) "See what's on it now" else "Look again", onClick = act.loadScreen)
        }
        ui.stats?.let { stats ->
            Heading("Right now")
            Card {
                Meter("Processor", stats.cpu)
                Meter("Memory", stats.memory)
                Meter("Disk", stats.disk)
                Detail("Running for", stats.uptime)
            }
        }
        Heading("Do")
        Card {
            Do(Ico.power, "Lock my PC") { ask("Lock my PC") }
            Divider()
            Do(Ico.mute, "Mute it") { ask("Mute my PC") }
            Divider()
            Do(Ico.link, "Start a new conversation", onClick = act.newChat)
            Divider()
            Do(Ico.close, "Stop everything Jarvis is doing", J.warm, act.stop)
        }
    }
}

/** How full something is: its name, a thin bar, the number. */
@Composable
private fun Meter(name: String, percent: Int) {
    Row(Modifier.fillMaxWidth().height(44.dp).semantics(mergeDescendants = true) {}, verticalAlignment = Alignment.CenterVertically) {
        Text(name, J.body.copy(color = J.text2), Modifier.width(96.dp))
        Box(Modifier.weight(1f).height(4.dp).clip(CircleShape).background(Color(0x1FFFFFFF))) {
            Box(Modifier.fillMaxHeight().fillMaxWidth(percent.coerceIn(0, 100) / 100f).background(if (percent >= 90) J.warm else J.accent))
        }
        Text("$percent%", J.body, Modifier.width(52.dp), align = TextAlign.End)
    }
}

// ---- settings sheet

@Composable
private fun BoxScope.Sheet(visible: Boolean, onDismiss: () -> Unit, content: @Composable ColumnScope.() -> Unit) {
    BackHandler(visible, onDismiss)
    AnimatedVisibility(visible, Modifier.matchParentSize(), enter = fadeIn(tween(200)), exit = fadeOut(tween(200))) {
        Box(Modifier.fillMaxSize().background(Color(0x8C000000)).clickable(remember { MutableInteractionSource() }, null, onClick = onDismiss))
    }
    AnimatedVisibility(visible, Modifier.align(Alignment.BottomCenter),
        enter = slideInVertically(tween(260, easing = FastOutSlowInEasing)) { it } + fadeIn(tween(200)),
        exit = slideOutVertically(tween(220)) { it } + fadeOut(tween(200))) {
        val shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp)
        Column(Modifier.fillMaxWidth().statusBarsPadding().padding(top = 40.dp).clip(shape).background(J.sheet)
            .border(1.dp, Brush.verticalGradient(listOf(J.strokeStrong, Color.Transparent), endY = 120f), shape)
            .clickable(remember { MutableInteractionSource() }, null) {}
            .navigationBarsPadding().imePadding().verticalScroll(rememberScrollState()).padding(horizontal = 20.dp)) {
            Box(Modifier.fillMaxWidth().padding(top = 10.dp, bottom = 6.dp), contentAlignment = Alignment.Center) {
                Box(Modifier.size(36.dp, 4.dp).background(Color(0x33FFFFFF), CircleShape))
            }
            content()
        }
    }
}

@Composable
private fun ColumnScope.Settings(ui: Ui, act: Actions, close: () -> Unit) {
    Row(Modifier.fillMaxWidth().padding(top = 8.dp, bottom = 16.dp), verticalAlignment = Alignment.CenterVertically) {
        Text("Settings", J.title, modifier = Modifier.weight(1f))
        Round(Ico.close, "Close settings", J.glass, J.text2, close, size = 34.dp, iconSize = 16.dp)
    }
    val (color, label) = status(ui)
    Card {
        Row(Modifier.padding(top = 2.dp, bottom = 14.dp), verticalAlignment = Alignment.CenterVertically) {
            Dot(color, glow = ui.state == State.ONLINE)
            Spacer(Modifier.width(10.dp))
            Text(label.substringBefore(" · "), J.heading.copy(fontSize = 15.sp))
        }
        Divider()
        Detail("Your PC", ui.pc.ifBlank { "Not connected yet" })
        Divider()
        Detail("Reached", if (ui.state != State.ONLINE) "—" else if (ui.direct) "Directly, same network" else "Through ${ui.relay.ifBlank { "your relay" }}")
        Spacer(Modifier.height(14.dp))
        PastePair(act) { paste ->
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Secondary("Pair again", Ico.scan, Modifier.weight(1f)) { close(); act.scan() }
                Secondary("Paste link", Ico.link, Modifier.weight(1f), paste)
            }
        }
    }
    Spacer(Modifier.height(12.dp))
    Card {
        Switch("“${ui.wakePhrase}”", "Say it and Jarvis listens, even with the app closed. The phone itself recognises it: nothing is sent anywhere until you've said it.",
            ui.wake, onChange = act.setWake)
        if (ui.wakeNote.isNotBlank()) Text(ui.wakeNote, J.small.copy(color = J.warm), Modifier.padding(bottom = 10.dp))
        Divider()
        // (the wake word keeps the app in touch anyway)
        Switch("Stay in touch when closed", "Reminders and finished tasks from your PC arrive as notifications.", ui.background || ui.wake, enabled = !ui.wake,
            onChange = act.setBackground)
        Divider()
        Text("To start Jarvis with the assistant gesture, choose it in Android's Settings → Apps → Default apps → Digital assistant app.", J.small,
            Modifier.padding(vertical = 12.dp))
    }
    Spacer(Modifier.height(12.dp))
    var key by remember(ui.key) { mutableStateOf(ui.key) }
    var shown by remember { mutableStateOf(false) }
    Card {
        Text("Gemini key for when the PC is off", J.heading.copy(fontSize = 15.sp))
        Spacer(Modifier.height(4.dp))
        Text("Your own key from aistudio.google.com. It stays on this phone, and Jarvis only talks and answers with it while your PC can't be reached.", J.small)
        Spacer(Modifier.height(14.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Field(key, { key = it }, "Paste your API key", Modifier.weight(1f), secret = !shown, done = { act.saveKey(key) },
                trailing = { if (key.isNotEmpty()) Text(if (shown) "Hide" else "Show", J.label.copy(color = J.text2), modifier = Modifier.clickable { shown = !shown }.padding(8.dp)) })
            if (key.trim() != ui.key) {
                Spacer(Modifier.width(10.dp))
                Primary("Save", null) { act.saveKey(key) }
            }
        }
        if (ui.key.isNotBlank() && key.trim() == ui.key) Row(Modifier.padding(top = 10.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Ico.check, J.green, 14.dp)
            Spacer(Modifier.width(6.dp))
            Text("Saved", J.label.copy(color = J.green, letterSpacing = 0.sp))
        }
    }
    Spacer(Modifier.height(12.dp))
    Row(Modifier.fillMaxWidth().height(44.dp).glass(CircleShape).press { close(); act.unpair() }, horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically) {
        Text("Unpair this phone", J.button.copy(color = J.red))
    }
    Text("Jarvis ${ui.version} · end-to-end encrypted", J.small.copy(fontSize = 12.sp), align = TextAlign.Center,
        modifier = Modifier.fillMaxWidth().padding(top = 18.dp, bottom = 16.dp))
}

/** A setting that's on or off: the whole row is the switch. */
@Composable
private fun Switch(title: String, hint: String, on: Boolean, enabled: Boolean = true, onChange: (Boolean) -> Unit) {
    val x by animateFloatAsState(if (on) 1f else 0f, tween(160), label = "switch")
    Row(Modifier.fillMaxWidth().toggleable(on, remember { MutableInteractionSource() }, null, enabled, Role.Switch, onChange)
        .graphicsLayer { alpha = if (enabled) 1f else 0.6f }.padding(vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text(title, J.heading.copy(fontSize = 15.sp))
            Spacer(Modifier.height(3.dp))
            Text(hint, J.small)
        }
        Spacer(Modifier.width(16.dp))
        Box(Modifier.size(46.dp, 28.dp).clip(CircleShape).background(lerp(Color(0x1FFFFFFF), J.accent, x)).padding(3.dp)) {
            Box(Modifier.size(22.dp).graphicsLayer { translationX = x * 18.dp.toPx() }.background(lerp(J.text2, J.accentInk, x), CircleShape))
        }
    }
}

@Composable
private fun Detail(name: String, value: String) {
    Row(Modifier.fillMaxWidth().height(52.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(name, J.body.copy(color = J.text2))
        Spacer(Modifier.width(16.dp))
        Text(value, J.body, Modifier.weight(1f), align = TextAlign.End, maxLines = 1)
    }
}

// ---- pieces

/** Glass: a faint white fill, a hairline that catches more light along its top edge. */
private fun Modifier.glass(shape: Shape, fill: Color = J.glass) = clip(shape).background(fill)
    .border(1.dp, Brush.verticalGradient(listOf(J.stroke.copy(alpha = 0.16f), J.stroke, J.stroke)), shape)

/** Floating glass (composer): stronger and lifted by a soft shadow, since there's no blur behind it. */
private fun Modifier.floating(shape: Shape) = drawBehind {
    val y = 10.dp.toPx()
    for (i in 1..4) drawRoundRect(Color.Black.copy(alpha = 0.09f), Offset(-i * 2f, y - i * 2f + 4f), Size(size.width + i * 4f, size.height + i * 4f), CornerRadius(size.height / 2 + i * 2f))
}.glass(shape, J.glassStrong).border(1.dp, Brush.verticalGradient(listOf(J.strokeStrong, J.stroke)), shape)

/** Something to tap: it gives a little under the finger. [label] is what a screen reader calls it (icon-only buttons). */
private fun Modifier.press(enabled: Boolean = true, label: String? = null, onClick: () -> Unit) = composed {
    val source = remember { MutableInteractionSource() }
    val down by source.collectIsPressedAsState()
    val s by animateFloatAsState(if (down) 0.97f else 1f, tween(140), label = "press")
    graphicsLayer { scaleX = s; scaleY = s; alpha = if (down) 0.85f else 1f }
        .clickable(source, null, enabled, role = Role.Button, onClick = onClick)
        .then(if (label != null) Modifier.semantics { contentDescription = label } else Modifier)
}

@Composable
private fun Card(content: @Composable ColumnScope.() -> Unit) {
    Column(Modifier.fillMaxWidth().glass(RoundedCornerShape(20.dp)).padding(horizontal = 16.dp, vertical = 14.dp), content = content)
}

@Composable
private fun Divider() = Box(Modifier.fillMaxWidth().height(1.dp).background(J.stroke))

@Composable
private fun Text(text: String, style: TextStyle, modifier: Modifier = Modifier, align: TextAlign = TextAlign.Start, maxLines: Int = Int.MAX_VALUE) =
    BasicText(text, modifier, style.copy(textAlign = align), maxLines = maxLines, overflow = TextOverflow.Ellipsis)

@Composable
private fun Icon(icon: ImageVector, tint: Color, size: Dp) = Image(icon, null, Modifier.size(size), colorFilter = ColorFilter.tint(tint))

@Composable
private fun Primary(text: String, icon: ImageVector?, modifier: Modifier = Modifier, height: Dp = 44.dp, enabled: Boolean = true, onClick: () -> Unit) {
    Row(modifier.height(height).then(if (enabled) Modifier.clip(CircleShape).background(J.accent) else Modifier.glass(CircleShape))
        .press(enabled, onClick = onClick).padding(horizontal = 20.dp), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
        val ink = if (enabled) J.accentInk else J.text3
        if (icon != null) { Icon(icon, ink, 20.dp); Spacer(Modifier.width(10.dp)) }
        Text(text, J.button.copy(color = ink))
    }
}

@Composable
private fun Secondary(text: String, icon: ImageVector, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Row(modifier.height(44.dp).glass(CircleShape).press(onClick = onClick).padding(horizontal = 16.dp),
        horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, J.text2, 18.dp)
        Spacer(Modifier.width(8.dp))
        Text(text, J.button)
    }
}

@Composable
private fun Ghost(text: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Box(modifier.height(44.dp).clip(CircleShape).press(onClick = onClick), contentAlignment = Alignment.Center) {
        Text(text, J.button.copy(color = J.text2))
    }
}

@Composable
private fun Field(value: String, onChange: (String) -> Unit, placeholder: String, modifier: Modifier = Modifier, secret: Boolean = false,
                  done: () -> Unit = {}, trailing: @Composable () -> Unit = {}) {
    var focused by remember { mutableStateOf(false) }
    val shape = RoundedCornerShape(12.dp)
    BasicTextField(value, onChange, modifier.height(44.dp).onFocusChanged { focused = it.isFocused }
        .drawBehind {
            if (focused) drawRoundRect(J.accentSoft, Offset(-1.5.dp.toPx(), -1.5.dp.toPx()), Size(size.width + 3.dp.toPx(), size.height + 3.dp.toPx()),
                CornerRadius(13.5.dp.toPx()), style = Stroke(3.dp.toPx()))
        }
        .clip(shape).background(J.glass).border(1.dp, if (focused) J.accent else J.stroke, shape),
        textStyle = J.body, singleLine = true, cursorBrush = SolidColor(J.accent),
        visualTransformation = if (secret) PasswordVisualTransformation() else VisualTransformation.None,
        keyboardOptions = KeyboardOptions(keyboardType = if (secret) KeyboardType.Password else KeyboardType.Uri, imeAction = ImeAction.Done),
        keyboardActions = KeyboardActions(onDone = { done() }),
        decorationBox = { inner ->
            Row(Modifier.fillMaxSize().padding(start = 14.dp, end = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.weight(1f)) { if (value.isEmpty()) Text(placeholder, J.body.copy(color = J.text3), maxLines = 1); inner() }
                trailing()
            }
        })
}

/** **bold** spans, the only markdown replies use. */
private fun md(text: String) = buildAnnotatedString {
    text.split("**").forEachIndexed { i, part -> if (i % 2 == 1) withStyle(SpanStyle(fontWeight = FontWeight.SemiBold, color = J.text)) { append(part) } else append(part) }
}
