import QtCore
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import Jarvis

// Settings save themselves as you change them.
ScrollPage {
    id: page
    title: "Settings"
    hint: "Changes are saved at once. Models and API keys are on the Models page."
    property var s: ({})
    property var voices: []
    property var languages: ({})
    property var wakeWords: ({})
    property bool learned: false  // a verifier is learned for the chosen wake word
    property bool passphraseSet: false
    property bool ownWake: false  // "Your own model" picked, before its path is in
    readonly property bool customWake: !!page.s.wake_word && !(page.s.wake_word in page.wakeWords)
    property bool confirmDelete: false
    property var remote: ({})
    property var phone: ({})
    property var wa: ({})
    property bool changingRelay: false
    function setRelay(url) {
        Api.post("/api/phone/relay", { relay: url }, d => { phone = d; relayUrl.text = ""; changingRelay = false }, e => Backend.toast(e.error, true))
    }
    function setToken(token) {
        Api.post("/api/remote/token", { token: token }, d => { remote = d; tgToken.text = "" }, e => Backend.toast(e.error, true))
    }
    property var avail: ({ backends: [], live: [] })  // for the voice models (asked for separately: it's slower)
    property bool looking: false
    signal setupAgain()
    property var update: ({})
    property bool updating: false
    property string step: ""   // how the update is going, or why it failed
    function checkUpdate() { Api.get("/api/update", d => { update = d; step = "" }, e => Backend.toast(e.error, true)) }
    function installUpdate() {
        updating = true
        step = "Checking…"
        Api.post("/api/update", {}, () => Backend.toast("Updated: Jarvis is restarting", false),
                 e => { updating = false; step = "Couldn't update: " + e.error; Backend.toast(e.error, true) })
    }
    Connections {
        target: Backend
        function onEvent(json) { const e = JSON.parse(json); if (e.kind === "update") page.step = e.step }
    }

    function load() {
        Api.get("/api/settings", d => { took(d); voices = d.voices; languages = d.languages })
        Api.get("/api/remote", d => remote = d)
        Api.get("/api/phone", d => phone = d)
        Api.get("/api/whatsapp", d => wa = d)
        lookUp()
    }
    function lookUp() {
        looking = true
        Api.get("/api/models/available", d => { avail = d; looking = false }, e => { looking = false; Backend.toast(e.error, true) })
    }
    function options(list, current) {  // [{value, label}] for a Select, keeping the current choice even if it isn't listed
        const all = current && list.indexOf(current) < 0 ? [current].concat(list) : list
        return all.map(v => ({ value: v, label: v }))
    }
    function took(d) { s = d.settings; wakeWords = d.wake_words; learned = d.voice_learned; passphraseSet = d.passphrase }
    function set(key, value) {
        const change = {}
        change[key] = value
        Api.post("/api/settings", change, d => { took(d); Theme.scale = d.settings.text_size || 1 }, e => { Backend.toast(e.error, true); load() })
    }
    function setPassphrase(text) {
        Api.post("/api/passphrase", { passphrase: text }, d => { passphraseSet = d.passphrase; passphrase.text = ""
                 Backend.toast(d.passphrase ? "Passphrase saved" : "Passphrase removed", false) }, e => Backend.toast(e.error, true))
    }
    Component.onCompleted: load()


    Section {
        title: "Voice"
        description: "How Jarvis sounds and talks to you. Changes apply from the next conversation."
        Row2 {
            Setting { label: "Jarvis's voice"
                Select { Layout.fillWidth: true; model: page.voices.map(v => ({ value: v, label: v })); value: page.s.voice || ""; onPicked: v => page.set("voice", v) } }
            Setting { label: "Voice model"
                Select { Layout.fillWidth: true; visible: page.avail.live.length > 0; model: page.options(page.avail.live, page.s.live_model)
                         value: page.s.live_model || ""; onPicked: v => page.set("live_model", v) }
                Field { Layout.fillWidth: true; visible: !page.avail.live.length; text: page.s.live_model || ""
                        onEditingFinished: if (text !== page.s.live_model) page.set("live_model", text) } }
        }
        Row2 {
            Setting { label: "Personality"
                Select { Layout.fillWidth: true; value: page.s.personality || "jarvis"; onPicked: v => page.set("personality", v)
                         model: [{ value: "jarvis", label: "Jarvis: refined, dry wit" }, { value: "friendly", label: "Friendly: warm and casual" },
                                 { value: "brief", label: "Brief: just the answer" }] } }
            Setting { label: "Language Jarvis speaks and listens for"
                Select { Layout.fillWidth: true; model: Object.keys(page.languages).map(k => ({ value: k, label: page.languages[k] }))
                         value: page.s.language || "en-US"; onPicked: v => page.set("language", v) } }
        }
        Setting { label: "Also speaks and understands, when you (or someone on WhatsApp) speak them. Anything else is taken as mishearing."
            Flow {
                Layout.fillWidth: true
                spacing: 8
                Repeater {
                    model: Object.keys(page.languages).filter(k => page.languages[k].split(" (")[0]  // (English (UK) is still English)
                                                                    !== (page.languages[page.s.language || "en-US"] || "").split(" (")[0])
                    Chip { required property string modelData; text: page.languages[modelData]
                           checked: (page.s.languages || []).indexOf(modelData) >= 0
                           onClicked: page.set("languages", checked ? page.s.languages.filter(k => k !== modelData)
                                                                     : (page.s.languages || []).concat([modelData])) }
                }
            }
        }
        Switches {
            Toggle { Layout.fillWidth: true; text: "Fast voice"; hint: "Answer without thinking first: about 0.3 s quicker, a little less sharp"
                     checked: !!page.s.fast_voice; onToggled: page.set("fast_voice", checked) }
            Line {}
            Toggle { Layout.fillWidth: true; text: "Speak replies to typed messages"; checked: !!page.s.speak_typed_replies
                     onToggled: page.set("speak_typed_replies", checked) }
            Line {}
            Toggle { Layout.fillWidth: true; text: "Always use the backup voice"
                     hint: "Hear and speak with the models on the Models page instead of Gemini Live, for keys without it. Off, the backup voice only answers while Gemini Live can't be reached"
                     checked: !!page.s.always_backup_voice; onToggled: page.set("always_backup_voice", checked) }
        }
    }

    Section {
        title: "Listening"
        description: "When Jarvis wakes up, and how long it keeps listening."
        Row2 {
            Setting { label: "Wake word"
                Select { Layout.fillWidth: true; value: page.customWake || page.ownWake ? "custom" : (page.s.wake_word || "hey_jarvis")
                         model: Object.keys(page.wakeWords).map(k => ({ value: k, label: page.wakeWords[k] }))
                                .concat([{ value: "custom", label: "Your own model…" }])
                         onPicked: v => { page.ownWake = v === "custom"; if (v !== "custom") page.set("wake_word", v); else ownModel.forceActiveFocus() } } }
            Setting { label: "Path of your own openWakeWord .onnx model"
                visible: page.customWake || page.ownWake
                Field { id: ownModel; Layout.fillWidth: true; text: page.customWake ? page.s.wake_word : ""
                        placeholderText: "Full path, e.g. /home/you/hey_computer.onnx"
                        onEditingFinished: if (text.trim() && text !== page.s.wake_word) page.set("wake_word", text.trim()) } }
            Item { Layout.fillWidth: true; visible: !page.customWake && !page.ownWake }
        }
        Row2 {
            Slide { label: "Pause before Jarvis answers"; key: "end_of_speech_ms"; from: 200; to: 2000; step: 50; unit: " ms"
                    hint: "Lower is snappier; higher cuts you off less" }
            Slide { label: "Wake word sensitivity"; key: "wake_threshold"; from: 0.05; to: 0.95; step: 0.05; unit: ""; decimals: 2
                    hint: "Lower wakes more easily" }
        }
        Row2 {
            Slide { label: "Keep listening after a reply"; key: "follow_up_seconds"; from: 0; to: 60; step: 1; unit: " s"
                    hint: "How long Jarvis waits for a follow-up" }
            Slide { label: "Stay connected after a conversation"; key: "keep_session_seconds"; from: 0; to: 600; step: 30; unit: " s"
                    hint: "Makes the next wake-up instant" }
        }
        Switches {
            Toggle { Layout.fillWidth: true; text: "Learn my voice"; hint: "Wake-ups you dismiss teach Jarvis what isn't you"
                     checked: !!page.s.learn_my_voice; onToggled: page.set("learn_my_voice", checked) }
            Line {}
            Toggle { Layout.fillWidth: true; text: "Only wake for my voice"
                     hint: !page.learned ? "Nothing learned for this wake word yet (Learn my voice needs a few wake-ups first): until then anyone can wake Jarvis"
                           : !page.s.learn_my_voice ? "Needs Learn my voice on: until then anyone can wake Jarvis"
                           : "Someone else saying the wake word doesn't wake Jarvis. Talk and push to talk always work"
                     checked: !!page.s.only_my_voice; onToggled: page.set("only_my_voice", checked) }
            Line {}
            Toggle { Layout.fillWidth: true; text: "Echo cancelling"; hint: "Keeps the PC's own sound (Jarvis, games, videos, calls) out of the mic, so it isn't heard as you, and you can talk over Jarvis ("
                           + (Qt.platform.os === "windows" ? "experimental on Windows: Health says if it's working" : "PipeWire") + "; restart Jarvis to apply)"
                     checked: !!page.s.echo_cancel; onToggled: page.set("echo_cancel", checked) }
        }
        Setting { label: "Spoken passphrase: asked for with every yes said out loud (sends, calls, account changes, risky commands). Never shown or said back"
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Field { id: passphrase; Layout.fillWidth: true; echoMode: TextInput.Password
                        placeholderText: page.passphraseSet ? "Passphrase set · type a new one to replace it" : "A few words only you know"
                        onAccepted: if (text.trim()) page.setPassphrase(text) }
                Pill { implicitHeight: 44; text: "Save"; kind: passphrase.text.trim() !== "" ? "primary" : ""; enabled: passphrase.text.trim() !== ""
                       onClicked: page.setPassphrase(passphrase.text) }
                Pill { implicitHeight: 44; kind: "ghost"; text: "Remove"; visible: page.passphraseSet; onClicked: page.setPassphrase("") }
            }
        }
        ColumnLayout {  // push to talk
            Layout.fillWidth: true
            spacing: 12
            Line {}
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Txt { text: "Push to talk"; Layout.fillWidth: true }
                Txt { kind: "small"; Layout.fillWidth: true
                      text: "Bind these to keyboard shortcuts (KDE: System Settings → Keyboard → Shortcuts → Add New → Command)." }
            }
            Command { code: "jarvis --listen"; text: "Start listening" }
            Command { code: "jarvis --region"; text: "Drag over part of the screen and ask about it" }
        }
    }

    Section {
        title: "Your day"
        description: "The weather, briefings and heads-ups Jarvis gives you."
        Setting { label: "Home city, for the weather (empty: guess from your network)"
            Field { Layout.fillWidth: true; text: page.s.home_city || ""; placeholderText: "e.g. London"
                    onEditingFinished: if (text !== page.s.home_city) page.set("home_city", text) } }
        Switches {
            Toggle { Layout.fillWidth: true; text: "Morning briefing"; hint: "The first time Jarvis starts in a morning, it tells you about your day"
                     checked: !!page.s.morning_briefing; onToggled: page.set("morning_briefing", checked) }
            Line {}
            Toggle { Layout.fillWidth: true; text: "Do not disturb"; hint: "Jarvis doesn't speak up on its own: reminders, results and messages only go to the chat, notifications and your phone. It still answers you (also in the tray menu)"
                     checked: !!page.s.do_not_disturb; onToggled: page.set("do_not_disturb", checked) }
            Line {}
            Toggle { Layout.fillWidth: true; text: "Classroom deadlines"; hint: "Reminders a day and two hours before work is due (skipped once you've turned it in)"
                     checked: !!page.s.deadline_reminders; onToggled: page.set("deadline_reminders", checked) }
            Line {}
            Toggle { Layout.fillWidth: true; text: "Calendar heads-up"; hint: "A reminder ten minutes before each Google Calendar event"
                     checked: !!page.s.calendar_reminders; onToggled: page.set("calendar_reminders", checked) }
        }
        Row2 {
            Setting { label: "Quiet hours from (empty: none)"
                Field { Layout.fillWidth: true; text: page.s.quiet_from || ""; placeholderText: "e.g. 22:00"
                        onEditingFinished: if (text !== page.s.quiet_from) page.set("quiet_from", text) } }
            Setting { label: "Until (the morning briefing waits for it)"
                Field { Layout.fillWidth: true; text: page.s.quiet_until || ""; placeholderText: "e.g. 07:00"
                        onEditingFinished: if (text !== page.s.quiet_until) page.set("quiet_until", text) } }
        }
    }

    Section {
        title: "Window & behavior"
        description: "How the window looks, and what Jarvis may do on its own."
        Row2 {
            Slide { label: "Text size"; key: "text_size"; from: 0.9; to: 1.5; step: 0.05; unit: "×"; decimals: 2
                    hint: "Bigger text across the window" }
            Item { Layout.fillWidth: true }
        }
        Switches {
            Toggle { Layout.fillWidth: true; text: "Show Jarvis's thinking in the chat"; checked: !!page.s.show_thinking
                     onToggled: page.set("show_thinking", checked) }
            Line {}
            Toggle { Layout.fillWidth: true; text: "Start Jarvis when I log in"; checked: !!page.s.start_at_login
                     onToggled: page.set("start_at_login", checked) }
            Line {}
            Toggle { Layout.fillWidth: true; text: "Ask before risky actions"
                     hint: "Commands that delete, install or shut down, and account changes (sending email, new events), wait for your yes unless you asked for exactly that"
                     checked: page.s.safety !== "full"; onToggled: page.set("safety", checked ? "ask" : "full") }
        }
    }

    Section {
        title: "Your instructions"
        description: "How Jarvis should behave, and things it should know about you."
        Area { text: page.s.extra_instructions || ""; onDone: v => page.set("extra_instructions", v) }
    }

    Section {
        title: "Jarvis on Telegram"
        description: "Send Jarvis tasks from anywhere through Telegram."
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 8
            Step { number: 1; format: Text.StyledText
                   text: "In Telegram, message <a href=\"https://t.me/BotFather\">@BotFather</a>, send /newbot and copy the token it gives you." }
            Step { number: 2; text: "Paste it here." }
            Step { number: 3; text: "Send your new bot the code below. Only that chat is answered." }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Field { id: tgToken; Layout.fillWidth: true; echoMode: TextInput.Password
                    placeholderText: page.remote.token ? "Bot token saved · paste a new one to replace it" : "Paste your bot's token"
                    onAccepted: page.setToken(text) }
            Pill { implicitHeight: 44; text: "Save"; kind: tgToken.text.trim() !== "" ? "primary" : ""; enabled: tgToken.text.trim() !== ""; onClicked: page.setToken(tgToken.text) }
        }
        Status {
            visible: !!page.remote.token
            status: page.remote.paired ? "ok" : "working"
            format: Text.StyledText
            text: page.remote.paired ? `Paired with ${page.remote.paired}.`
                  : `Send your bot this code: <font face="${Theme.mono}" color="${Theme.accent}">${page.remote.code}</font>`
        }
        Txt { kind: "small"; visible: !!page.remote.error; text: page.remote.error || ""; color: Theme.red; Layout.fillWidth: true }
        RowLayout {
            visible: !!page.remote.token
            spacing: 10
            Pill { visible: !!page.remote.paired; text: "Unpair"; onClicked: Api.post("/api/remote/unpair", {}, d => page.remote = d) }
            Pill { kind: "danger"; text: "Remove the bot"; onClicked: page.setToken("") }
        }
    }

    Section {
        title: "The Jarvis app"
        description: "The Jarvis Android app reaches this PC from anywhere through your own private relay. It's end-to-end encrypted: "
                     + "the relay only passes on scrambled data, and nothing on this PC is open to the internet."
        ColumnLayout {  // setting the relay up, until there is one
            Layout.fillWidth: true
            spacing: 8
            visible: !page.phone.relay || page.changingRelay
            Step { number: 1; text: "In the relay folder of Jarvis's files, sign in to a free Cloudflare account:"; code: "npx wrangler login" }
            Step { number: 2; text: "Put the relay online:"; code: "npx wrangler deploy" }
            Step { number: 3; text: "Paste the address it prints here." }
        }
        RowLayout {
            Layout.fillWidth: true
            visible: !page.phone.relay || page.changingRelay
            spacing: 10
            Field { id: relayUrl; Layout.fillWidth: true
                    placeholderText: "Your relay's address, like https://jarvis-relay.you.workers.dev"
                    onAccepted: page.setRelay(text) }
            Pill { implicitHeight: 44; text: "Save"; kind: relayUrl.text.trim() !== "" ? "primary" : ""; enabled: relayUrl.text.trim() !== ""; onClicked: page.setRelay(relayUrl.text) }
            Pill { implicitHeight: 44; kind: "ghost"; text: "Cancel"; visible: page.changingRelay
                   onClicked: { page.changingRelay = false; relayUrl.text = "" } }
        }
        RowLayout {  // the relay in use and whether it's reachable
            Layout.fillWidth: true
            visible: !!page.phone.relay && !page.changingRelay
            spacing: 14
            Rectangle {
                Layout.preferredWidth: 36; Layout.preferredHeight: 36; radius: 18
                color: Theme.accentSoft
                Icon { anchors.centerIn: parent; name: "link"; size: 18; color: Theme.accent }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Txt { text: page.phone.relay || ""; font.family: Theme.mono; font.pixelSize: Theme.px(13)
                      wrapMode: Text.NoWrap; elide: Text.ElideMiddle; Layout.fillWidth: true }
                Status {
                    status: page.phone.connected ? "ok" : "working"
                    text: page.phone.connected ? "Connected" : (page.phone.error || "Connecting…")
                }
            }
            Pill { kind: "ghost"; text: "Change"; onClicked: { page.changingRelay = true; relayUrl.forceActiveFocus() } }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            visible: (page.phone.devices || []).length > 0
            Repeater {
                model: page.phone.devices || []
                ColumnLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 0
                    Line {}
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.minimumHeight: 56
                        spacing: 14
                        Rectangle {
                            Layout.preferredWidth: 36; Layout.preferredHeight: 36; radius: 18
                            color: Theme.accentSoft
                            Icon { anchors.centerIn: parent; name: "phone"; size: 18; color: Theme.accent }
                        }
                        Txt { text: modelData.name; weight: 500; Layout.fillWidth: true }
                        Pill { kind: "ghost"; text: "Unpair"; onClicked: Api.post("/api/phone/unpair", { device: modelData.id }, d => page.phone = d) }
                    }
                }
            }
            Line {}
        }
        Pill { visible: !!page.phone.relay && !page.phone.pairing; symbol: "phone"
               kind: (page.phone.devices || []).length ? "" : "primary"
               text: (page.phone.devices || []).length ? "Pair another phone" : "Pair a phone"
               onClicked: Api.post("/api/phone/pair", {}, d => page.phone = d, e => Backend.toast(e.error, true)) }
        RowLayout {
            visible: !!page.phone.pairing
            Layout.fillWidth: true
            spacing: 24
            Rectangle {  // (a QR code needs its light background to scan)
                Layout.preferredWidth: 224; Layout.preferredHeight: 224
                radius: 16
                color: "white"
                Image { anchors.centerIn: parent; width: 204; height: 204; smooth: false
                        source: page.phone.pairing ? page.phone.pairing.qr : "" }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6
                Txt { kind: "heading"; text: "Scan to pair"; Layout.fillWidth: true }
                Txt { kind: "small"; Layout.fillWidth: true
                      text: "In the Jarvis app, tap Pair and scan this code. It works once, for ten minutes." }
            }
        }
        Timer {  // while a code is up: notice when the phone has paired, and keep the relay's status fresh
            interval: 2000; repeat: true; running: !!page.phone.pairing || (!!page.phone.relay && !page.phone.connected)
            onTriggered: Api.get("/api/phone", d => page.phone = d)
        }
    }

    Section {
        title: "WhatsApp"
        description: "Jarvis links to your own WhatsApp like WhatsApp Web. It answers your contacts' messages that don't need you, "
                     + "saying it's your assistant, and picks up calls you miss to take a message. It's not an official "
                     + "WhatsApp feature: WhatsApp may block numbers that act like bots, so Jarvis answers only saved contacts, never groups."
        Pill { visible: !page.wa.linked && page.wa.state === "off"; kind: "primary"; symbol: "chats"; text: "Link WhatsApp"
               onClicked: Api.post("/api/whatsapp/link", {}, d => page.wa = d, e => Backend.toast(e.error, true)) }
        Status { visible: page.wa.state === "starting" || page.wa.state === "connecting"; status: "working"
                 text: page.wa.linked ? "Connecting to WhatsApp…" : "Getting a code from WhatsApp…" }
        RowLayout {
            visible: page.wa.state === "qr" && !!page.wa.qr
            Layout.fillWidth: true
            spacing: 24
            Rectangle {  // (a QR code needs its light background to scan)
                Layout.preferredWidth: 224; Layout.preferredHeight: 224
                radius: 16
                color: "white"
                Image { anchors.centerIn: parent; width: 204; height: 204; smooth: false; source: page.wa.qr || "" }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6
                Txt { kind: "heading"; text: "Scan with WhatsApp"; Layout.fillWidth: true }
                Txt { kind: "small"; Layout.fillWidth: true
                      text: "On your phone: WhatsApp → Settings → Linked devices → Link a device, then scan this code. It renews itself." }
            }
        }
        RowLayout {
            visible: page.wa.state === "connected"
            spacing: 14
            Status { status: page.wa.on_call ? "working" : "ok"
                     text: page.wa.on_call ? `On a call with ${page.wa.on_call}` : `Linked${page.wa.name ? " as " + page.wa.name : ""}` }
            Pill { kind: "ghost"; text: "Unlink"; onClicked: Api.post("/api/whatsapp/unlink", {}, d => page.wa = d) }
        }
        Txt { kind: "small"; visible: !!page.wa.error; text: page.wa.error || ""; color: Theme.red; Layout.fillWidth: true }
        Row2 {
            Setting { label: "Messages"
                Select { Layout.fillWidth: true; value: page.s.whatsapp_replies || "contacts"; onPicked: v => page.set("whatsapp_replies", v)
                         model: [{ value: "contacts", label: "Answer my contacts" }, { value: "off", label: "Just show them to me" }] } }
            Setting { label: "Calls"
                Select { Layout.fillWidth: true; value: page.s.whatsapp_calls || "answer"; onPicked: v => page.set("whatsapp_calls", v)
                         model: [{ value: "answer", label: "Pick up if I don't (20 s)" }, { value: "decline", label: "Decline them" },
                                 { value: "off", label: "Let them ring" }] } }
        }
        Row2 {
            Setting { label: "Always let through (one name per line, as WhatsApp shows it): never answered by Jarvis, always told to you out loud, even in quiet hours"
                Area { text: (page.s.whatsapp_always || []).join("\n"); placeholder: "e.g. Alex"; onDone: v => page.set("whatsapp_always", v) } }
            Setting { label: "Never answer (one name per line): Jarvis never replies or picks up, and only shows their messages in the chat"
                Area { text: (page.s.whatsapp_never || []).join("\n"); placeholder: "e.g. Sam"; onDone: v => page.set("whatsapp_never", v) } }
        }
        Setting { label: "What Jarvis tells people"
            Area { text: page.s.whatsapp_note || ""; placeholder: "e.g. I'm in class until 5, I'll answer after"
                   onDone: v => page.set("whatsapp_note", v) } }
        Timer {  // while it's starting or showing a code: notice when the phone has linked
            interval: 2000; repeat: true; running: page.wa.state === "qr" || page.wa.state === "starting" || page.wa.state === "connecting" || !!page.wa.on_call
            onTriggered: Api.get("/api/whatsapp", d => page.wa = d)
        }
    }

    Section {
        title: "Your data"
        description: "On this PC Jarvis keeps what it remembers about you, your conversations, reminders and routines, short clips "
                     + "of your wake word (to learn your voice) and a log. What you say after the wake word, and screenshots when a "
                     + "task needs the screen, go to Google Gemini; account actions go through Composio."
        Row2 {
            Setting { label: "Keep conversations and logs for"
                Select { Layout.fillWidth: true; value: String(page.s.keep_days || 0); onPicked: v => page.set("keep_days", v)
                         model: [{ value: "7", label: "A week" }, { value: "30", label: "A month" }, { value: "90", label: "3 months" },
                                 { value: "365", label: "A year" }, { value: "0", label: "Forever" }] } }
            Item { Layout.fillWidth: true }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 14
            Pill { kind: "danger"; symbol: "trash"; text: page.confirmDelete ? "Press again to delete it all" : "Delete everything Jarvis keeps about me"
                   onClicked: {
                       if (!page.confirmDelete) { page.confirmDelete = true; disarm.restart(); return }
                       page.confirmDelete = false
                       Api.post("/api/data/delete", {}, () => Backend.toast("Deleted. Keys, accounts and settings are kept.", false),
                                e => Backend.toast(e.error, true))
                   } }
            Txt { kind: "small"; text: "Keys, account sign-ins and settings stay."; color: Theme.text3; Layout.fillWidth: true }
        }
        Timer { id: disarm; interval: 4000; onTriggered: page.confirmDelete = false }
    }

    Section {
        title: "Move to another computer"
        description: "One file with your settings, memory, reminders, scheduled tasks, routines, plugins, conversations and the "
                     + "clips Jarvis learned your voice from. Keys, account sign-ins, WhatsApp and your phone aren't in it: set "
                     + "those up again on the other computer."
        RowLayout {
            Layout.fillWidth: true
            spacing: 14
            Pill { text: "Save a backup"
                   onClicked: { saver.selectedFile = StandardPaths.writableLocation(StandardPaths.DocumentsLocation) + "/jarvis-backup-"
                                    + new Date().toISOString().slice(0, 10) + ".zip"; saver.open() } }
            Pill { kind: "ghost"; text: "Bring one in"; onClicked: opener.open() }
            Txt { kind: "small"; text: "Bringing one in replaces what's on this computer (conversations are added), then Jarvis restarts."
                  color: Theme.text3; Layout.fillWidth: true }
        }
        FileDialog {
            id: saver
            fileMode: FileDialog.SaveFile
            title: "Save a Jarvis backup"
            nameFilters: ["Jarvis backups (*.zip)"]
            defaultSuffix: "zip"
            onAccepted: Api.post("/api/data/export", { path: String(selectedFile) }, d => Backend.toast(`Saved to ${d.path}`, false),
                                 e => Backend.toast(e.error, true))
        }
        FileDialog {
            id: opener
            title: "Bring in a Jarvis backup"
            nameFilters: ["Jarvis backups (*.zip)"]
            onAccepted: Api.post("/api/data/import", { path: String(selectedFile) },
                                 d => Backend.toast("Brought in" + (d.skipped.length ? ` (left at their defaults here: ${d.skipped.join(", ")})` : "")
                                                    + ": Jarvis is restarting", false),
                                 e => Backend.toast(e.error, true))
        }
    }

    RowLayout {  // about: no card, it's a footer
        Layout.fillWidth: true
        Layout.leftMargin: Theme.pad; Layout.rightMargin: Theme.pad - 12
        spacing: 12
        Orb { Layout.preferredWidth: 24; Layout.preferredHeight: 24; rings: false }
        Txt { kind: "small"; text: "Jarvis " + Backend.version; wrapMode: Text.NoWrap }
        Txt { kind: "small"; Layout.fillWidth: true
              color: page.step && !page.updating ? Theme.red : page.update.available ? Theme.accent : Theme.text3
              text: page.step ? page.step
                    : page.update.available ? `${page.update.latest} is out` + (page.update.how ? ` (${page.update.how})` : "")
                    : page.update.latest ? "Up to date" : "" }
        Pill { text: page.updating ? "Updating…" : page.update.can_update ? "Update now" : "Check for updates"
               kind: page.update.can_update ? "primary" : "ghost"; enabled: !page.updating
               onClicked: page.update.can_update ? page.installUpdate() : page.checkUpdate() }
        Pill { kind: "ghost"; text: "Run the setup again"; onClicked: page.setupAgain() }
    }

    component Row2: RowLayout {
        Layout.fillWidth: true
        spacing: 24
        uniformCellSizes: true
    }
    component Setting: ColumnLayout {
        property string label
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignTop
        spacing: 8
        Txt { kind: "label"; text: label; Layout.fillWidth: true }
    }
    component Line: Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.stroke }
    component Switches: ColumnLayout {  // toggles as rows with hairlines between them, and one above
        Layout.fillWidth: true
        spacing: 0
        Line {}
    }
    component Status: RowLayout {  // a status light and what it means
        property alias status: dot.status
        property alias text: label.text
        property alias format: label.textFormat
        Layout.fillWidth: true
        spacing: 10
        StatusDot { id: dot }
        Txt { id: label; kind: "small"; color: Theme.text; textFormat: Text.PlainText; Layout.fillWidth: true }
    }
    component Code: Rectangle {  // a command to type, set in mono
        property string text
        implicitWidth: codeText.implicitWidth + 16
        implicitHeight: codeText.implicitHeight + 6
        radius: 6
        color: Theme.glass
        border.width: 1; border.color: Theme.stroke
        Txt { id: codeText; anchors.centerIn: parent; text: parent.text; wrapMode: Text.NoWrap
              font.family: Theme.mono; font.pixelSize: Theme.px(12.5) }
    }
    component Command: RowLayout {
        property alias code: cmd.text
        property alias text: what.text
        Layout.fillWidth: true
        spacing: 12
        Code { id: cmd; Layout.preferredWidth: 150 }
        Txt { id: what; kind: "small"; Layout.fillWidth: true }
    }
    component Step: RowLayout {  // a numbered step, with a command to run after it
        property int number
        property alias text: what.text
        property alias format: what.textFormat
        property string code
        Layout.fillWidth: true
        spacing: 10
        Rectangle {
            Layout.alignment: Qt.AlignTop
            Layout.preferredWidth: 22; Layout.preferredHeight: 22; radius: 11
            color: Theme.accentSoft
            Txt { anchors.centerIn: parent; kind: "label"; text: number; color: Theme.accent; font.features: { "tnum": 1 } }
        }
        Flow {
            Layout.fillWidth: true
            Layout.topMargin: 2
            spacing: 8
            Txt { id: what; kind: "small"; width: Math.min(implicitWidth, parent.width) }
            Code { text: code; visible: code !== "" }
        }
    }
    component Slide: ColumnLayout {
        id: sl
        property string label
        property string hint
        property string key
        property alias from: slider.from
        property alias to: slider.to
        property alias step: slider.stepSize
        property string unit
        property int decimals: 0
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignTop
        spacing: 6
        RowLayout {
            Layout.fillWidth: true
            Txt { kind: "label"; text: sl.label; Layout.fillWidth: true }
            Txt { text: slider.value.toFixed(sl.decimals) + sl.unit; weight: 600; color: Theme.accent
                  font.pixelSize: Theme.px(13); font.features: { "tnum": 1 }; wrapMode: Text.NoWrap }
        }
        Range {
            id: slider
            Layout.fillWidth: true
            leftPadding: 0; rightPadding: 0  // (the track lines up with the label and the value)
            snapMode: Slider.SnapAlways
            value: page.s[sl.key] !== undefined ? page.s[sl.key] : from
            onPressedChanged: if (!pressed) page.set(sl.key, Number(value.toFixed(sl.decimals)))
        }
        Txt { kind: "small"; text: sl.hint; visible: sl.hint !== ""; color: Theme.text3; Layout.fillWidth: true }
    }
    component Area: Rectangle {
        id: area
        property alias text: edit.text
        property bool mono: false
        property alias placeholder: edit.placeholderText
        signal done(string value)
        Layout.fillWidth: true
        implicitHeight: Math.max(104, edit.implicitHeight + 4)
        radius: Theme.radiusControl
        color: "transparent"  // (it sits alone in its card: a second glass fill would read as a stock text box)
        border.width: 1
        border.color: edit.activeFocus ? Theme.accent : Theme.stroke
        Behavior on border.color { ColorAnimation { duration: Theme.fast } }
        Focus { visible: edit.activeFocus }
        TextArea {
            id: edit
            anchors.fill: parent
            color: Theme.text
            placeholderText: "e.g. Keep answers short."
            placeholderTextColor: Theme.text3
            font.family: area.mono ? Theme.mono : Theme.font
            font.pixelSize: Theme.px(area.mono ? 12 : 14)
            wrapMode: TextEdit.Wrap
            selectionColor: Theme.alpha(Theme.accent, 0.4)
            selectedTextColor: Theme.text
            background: null
            padding: 16
            onActiveFocusChanged: if (!activeFocus) area.done(text)
        }
    }
}
