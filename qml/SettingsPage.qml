import QtCore
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import Jarvis

// Settings save themselves as you change them.
ScrollPage {
    id: page
    title: qsTr("Settings")
    hint: qsTr("Changes are saved at once. Models and API keys are on the Models page.")
    property var s: ({})
    property var voices: []
    property var languages: ({})
    property var windowLanguages: ({})  // code -> its own name
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
    readonly property var relaySetup: phone.setup || ({})
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
        step = qsTr("Checking…")
        Api.post("/api/update", {}, () => Backend.toast(qsTr("Updated: Jarvis is restarting"), false),
                 e => { updating = false; step = qsTr("Couldn't update: %1").arg(e.error); Backend.toast(e.error, true) })
    }
    Connections {
        target: Backend
        function onEvent(json) { const e = JSON.parse(json); if (e.kind === "update") page.step = e.step }
    }

    function load() {
        Api.get("/api/settings", d => { took(d); voices = d.voices; languages = d.languages; windowLanguages = d.window_languages })
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
        Api.post("/api/settings", change, d => {
            took(d)
            Theme.scale = d.settings.text_size || 1
            if (key === "window_languages") Backend.setLanguages(d.settings.window_languages)
        }, e => { Backend.toast(e.error, true); load() })
    }
    function moveLanguage(i, by) { const all = s.window_languages.slice(); all.splice(i + by, 0, all.splice(i, 1)[0]); set("window_languages", all) }
    function setPassphrase(text) {
        Api.post("/api/passphrase", { passphrase: text }, d => { passphraseSet = d.passphrase; passphrase.text = ""
                 Backend.toast(d.passphrase ? qsTr("Passphrase saved") : qsTr("Passphrase removed"), false) }, e => Backend.toast(e.error, true))
    }
    Component.onCompleted: load()


    Section {
        title: qsTr("Voice")
        description: qsTr("How Jarvis sounds and talks to you. Changes apply from the next conversation.")
        Row2 {
            Setting { label: qsTr("Jarvis's voice")
                Select { Layout.fillWidth: true; model: page.voices.map(v => ({ value: v, label: v })); value: page.s.voice || ""; onPicked: v => page.set("voice", v) } }
            Setting { label: qsTr("Voice model")
                Select { Layout.fillWidth: true; visible: page.avail.live.length > 0; model: page.options(page.avail.live, page.s.live_model)
                         value: page.s.live_model || ""; onPicked: v => page.set("live_model", v) }
                Field { Layout.fillWidth: true; visible: !page.avail.live.length; text: page.s.live_model || ""
                        onEditingFinished: if (text !== page.s.live_model) page.set("live_model", text) } }
        }
        Row2 {
            Setting { label: qsTr("Personality")
                Select { Layout.fillWidth: true; value: page.s.personality || "jarvis"; onPicked: v => page.set("personality", v)
                         model: [{ value: "jarvis", label: qsTr("Jarvis: refined, dry wit") }, { value: "friendly", label: qsTr("Friendly: warm and casual") },
                                 { value: "brief", label: qsTr("Brief: just the answer") }] } }
            Setting { label: qsTr("Language Jarvis speaks and listens for")
                Select { Layout.fillWidth: true; model: Object.keys(page.languages).map(k => ({ value: k, label: page.languages[k] }))
                         value: page.s.language || "en-US"; onPicked: v => page.set("language", v) } }
        }
        Setting { label: qsTr("Also speaks and understands, when you (or someone on WhatsApp) speak them. Anything else is taken as mishearing.")
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
            Toggle { Layout.fillWidth: true; text: qsTr("Fast voice"); hint: qsTr("Answer without thinking first: about 0.3 s quicker, a little less sharp")
                     checked: !!page.s.fast_voice; onToggled: page.set("fast_voice", checked) }
            Line {}
            Toggle { Layout.fillWidth: true; text: qsTr("Speak replies to typed messages"); checked: !!page.s.speak_typed_replies
                     onToggled: page.set("speak_typed_replies", checked) }
            Line {}
            Toggle { Layout.fillWidth: true; text: qsTr("Always use the backup voice")
                     hint: qsTr("Hear and speak with the models on the Models page instead of Gemini Live, for keys without it. Off, the backup voice only answers while Gemini Live can't be reached")
                     checked: !!page.s.always_backup_voice; onToggled: page.set("always_backup_voice", checked) }
        }
    }

    Section {
        title: qsTr("Listening")
        description: qsTr("When Jarvis wakes up, and how long it keeps listening.")
        Row2 {
            Setting { label: qsTr("Wake word")
                Select { Layout.fillWidth: true; value: page.customWake || page.ownWake ? "custom" : (page.s.wake_word || "hey_jarvis")
                         model: Object.keys(page.wakeWords).map(k => ({ value: k, label: page.wakeWords[k] }))
                                .concat([{ value: "custom", label: qsTr("Your own model…") }])
                         onPicked: v => { page.ownWake = v === "custom"; if (v !== "custom") page.set("wake_word", v); else ownModel.forceActiveFocus() } } }
            Setting { label: qsTr("Path of your own openWakeWord .onnx model")
                visible: page.customWake || page.ownWake
                Field { id: ownModel; Layout.fillWidth: true; text: page.customWake ? page.s.wake_word : ""
                        placeholderText: qsTr("Full path, e.g. /home/you/hey_computer.onnx")
                        onEditingFinished: if (text.trim() && text !== page.s.wake_word) page.set("wake_word", text.trim()) } }
            Item { Layout.fillWidth: true; visible: !page.customWake && !page.ownWake }
        }
        Row2 {
            Slide { label: qsTr("Pause before Jarvis answers"); key: "end_of_speech_ms"; from: 200; to: 2000; step: 50; unit: qsTr(" ms")
                    hint: qsTr("Lower is snappier; higher cuts you off less") }
            Slide { label: qsTr("Wake word sensitivity"); key: "wake_threshold"; from: 0.05; to: 0.95; step: 0.05; unit: ""; decimals: 2
                    hint: qsTr("Lower wakes more easily") }
        }
        Row2 {
            Slide { label: qsTr("Keep listening after a reply"); key: "follow_up_seconds"; from: 0; to: 60; step: 1; unit: qsTr(" s")
                    hint: qsTr("How long Jarvis waits for a follow-up") }
            Slide { label: qsTr("Stay connected after a conversation"); key: "keep_session_seconds"; from: 0; to: 600; step: 30; unit: qsTr(" s")
                    hint: qsTr("Makes the next wake-up instant") }
        }
        Switches {
            Toggle { Layout.fillWidth: true; text: qsTr("Learn my voice"); hint: qsTr("Wake-ups you dismiss teach Jarvis what isn't you")
                     checked: !!page.s.learn_my_voice; onToggled: page.set("learn_my_voice", checked) }
            Line {}
            Toggle { Layout.fillWidth: true; text: qsTr("Only wake for my voice")
                     hint: !page.learned ? qsTr("Nothing learned for this wake word yet (Learn my voice needs a few wake-ups first): until then anyone can wake Jarvis")
                           : !page.s.learn_my_voice ? qsTr("Needs Learn my voice on: until then anyone can wake Jarvis")
                           : qsTr("Someone else saying the wake word doesn't wake Jarvis. Talk and push to talk always work")
                     checked: !!page.s.only_my_voice; onToggled: page.set("only_my_voice", checked) }
            Line {}
            Toggle { Layout.fillWidth: true; text: qsTr("Echo cancelling"); hint: Qt.platform.os === "windows"
                           ? qsTr("Keeps the PC's own sound (Jarvis, games, videos, calls) out of the mic, so it isn't heard as you, and you can "
                                  + "talk over Jarvis (experimental on Windows: Health says if it's working; restart Jarvis to apply)")
                           : qsTr("Keeps the PC's own sound (Jarvis, games, videos, calls) out of the mic, so it isn't heard as you, and you can "
                                  + "talk over Jarvis (PipeWire; restart Jarvis to apply)")
                     checked: !!page.s.echo_cancel; onToggled: page.set("echo_cancel", checked) }
        }
        Setting { label: qsTr("Spoken passphrase: asked for with every yes said out loud (sends, calls, account changes, risky commands). Never shown or said back")
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Field { id: passphrase; Layout.fillWidth: true; echoMode: TextInput.Password
                        placeholderText: page.passphraseSet ? qsTr("Passphrase set · type a new one to replace it") : qsTr("A few words only you know")
                        onAccepted: if (text.trim()) page.setPassphrase(text) }
                Pill { implicitHeight: 44; text: qsTr("Save"); kind: passphrase.text.trim() !== "" ? "primary" : ""; enabled: passphrase.text.trim() !== ""
                       onClicked: page.setPassphrase(passphrase.text) }
                Pill { implicitHeight: 44; kind: "ghost"; text: qsTr("Remove"); visible: page.passphraseSet; onClicked: page.setPassphrase("") }
            }
        }
        ColumnLayout {  // push to talk
            Layout.fillWidth: true
            spacing: 12
            Line {}
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Txt { text: qsTr("Push to talk"); Layout.fillWidth: true }
                Txt { kind: "small"; Layout.fillWidth: true
                      text: qsTr("Bind these to keyboard shortcuts (KDE: System Settings → Keyboard → Shortcuts → Add New → Command).") }
            }
            Command { code: "jarvis --listen"; text: qsTr("Start listening") }
            Command { code: "jarvis --region"; text: qsTr("Drag over part of the screen and ask about it") }
        }
    }

    Section {
        title: qsTr("Your day")
        description: qsTr("The weather, briefings and heads-ups Jarvis gives you.")
        Setting { label: qsTr("Home city, for the weather (empty: guess from your network)")
            Field { Layout.fillWidth: true; text: page.s.home_city || ""; placeholderText: qsTr("e.g. London")
                    onEditingFinished: if (text !== page.s.home_city) page.set("home_city", text) } }
        Switches {
            Toggle { Layout.fillWidth: true; text: qsTr("Morning briefing"); hint: qsTr("The first time Jarvis starts in a morning, it tells you about your day")
                     checked: !!page.s.morning_briefing; onToggled: page.set("morning_briefing", checked) }
            Line {}
            Toggle { Layout.fillWidth: true; text: qsTr("Do not disturb"); hint: qsTr("Jarvis doesn't speak up on its own: reminders, results and messages only go to the chat, notifications and your phone. It still answers you (also in the tray menu)")
                     checked: !!page.s.do_not_disturb; onToggled: page.set("do_not_disturb", checked) }
            Line {}
            Toggle { Layout.fillWidth: true; text: qsTr("Classroom deadlines"); hint: qsTr("Reminders a day and two hours before work is due (skipped once you've turned it in)")
                     checked: !!page.s.deadline_reminders; onToggled: page.set("deadline_reminders", checked) }
            Line {}
            Toggle { Layout.fillWidth: true; text: qsTr("Calendar heads-up"); hint: qsTr("A reminder ten minutes before each Google Calendar event")
                     checked: !!page.s.calendar_reminders; onToggled: page.set("calendar_reminders", checked) }
        }
        Row2 {
            Setting { label: qsTr("Quiet hours from (empty: none)")
                Field { Layout.fillWidth: true; text: page.s.quiet_from || ""; placeholderText: qsTr("e.g. 22:00")
                        onEditingFinished: if (text !== page.s.quiet_from) page.set("quiet_from", text) } }
            Setting { label: qsTr("Until (the morning briefing waits for it)")
                Field { Layout.fillWidth: true; text: page.s.quiet_until || ""; placeholderText: qsTr("e.g. 07:00")
                        onEditingFinished: if (text !== page.s.quiet_until) page.set("quiet_until", text) } }
        }
    }

    Section {
        title: qsTr("Window & behavior")
        description: qsTr("How the window looks, and what Jarvis may do on its own.")
        Row2 {
            Slide { label: qsTr("Text size"); key: "text_size"; from: 0.9; to: 1.5; step: 0.05; unit: "×"; decimals: 2
                    hint: qsTr("Bigger text across the window") }
            Setting { label: qsTr("Window language")
                Repeater {  // in order: each text shows in the first one that has it
                    model: page.s.window_languages || []
                    Rectangle {
                        required property string modelData
                        required property int index
                        readonly property var all: page.s.window_languages
                        Layout.fillWidth: true
                        implicitHeight: 40
                        radius: Theme.radiusControl
                        color: Theme.glass
                        border.width: 1; border.color: Theme.stroke
                        RowLayout {
                            anchors { fill: parent; leftMargin: 14; rightMargin: 4 }
                            spacing: 0
                            Txt { text: page.windowLanguages[modelData] || modelData; horizontalAlignment: Text.AlignLeft; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                            IconButton { symbol: "chevron"; rotation: 180; size: 32; glyph: 14; color: Theme.text3; tip: qsTr("Use sooner")
                                         visible: all.length > 1; enabled: index > 0; opacity: enabled ? 1 : 0.3; onClicked: page.moveLanguage(index, -1) }
                            IconButton { symbol: "chevron"; size: 32; glyph: 14; color: Theme.text3; tip: qsTr("Use later")
                                         visible: all.length > 1; enabled: index < all.length - 1; opacity: enabled ? 1 : 0.3; onClicked: page.moveLanguage(index, 1) }
                            IconButton { symbol: "close"; size: 32; glyph: 14; color: Theme.text3; tip: qsTr("Remove"); visible: all.length > 1
                                         onClicked: page.set("window_languages", all.filter(c => c !== modelData)) }
                        }
                    }
                }
                Select { Layout.fillWidth: true; value: ""
                         visible: Object.keys(page.windowLanguages).length > (page.s.window_languages || []).length
                         model: [{ value: "", label: qsTr("Add a language…") }].concat(Object.keys(page.windowLanguages)
                                .filter(c => (page.s.window_languages || []).indexOf(c) < 0).map(c => ({ value: c, label: page.windowLanguages[c] })))
                         onPicked: v => { value = ""; if (v) page.set("window_languages", page.s.window_languages.concat([v])) } }
                Txt { kind: "small"; color: Theme.text3; Layout.fillWidth: true
                      text: qsTr("Each text shows in the first language that has it. English is the window's own, so languages under it aren't used.") }
            }
        }
        Switches {
            Toggle { Layout.fillWidth: true; text: qsTr("Show Jarvis's thinking in the chat"); checked: !!page.s.show_thinking
                     onToggled: page.set("show_thinking", checked) }
            Line {}
            Toggle { Layout.fillWidth: true; text: qsTr("Start Jarvis when I log in"); checked: !!page.s.start_at_login
                     onToggled: page.set("start_at_login", checked) }
            Line {}
            Toggle { Layout.fillWidth: true; text: qsTr("Ask before risky actions")
                     hint: qsTr("Commands that delete, install or shut down, and account changes (sending email, new events), wait for your yes unless you asked for exactly that")
                     checked: page.s.safety !== "full"; onToggled: page.set("safety", checked ? "ask" : "full") }
        }
    }

    Section {
        title: qsTr("Your instructions")
        description: qsTr("How Jarvis should behave, and things it should know about you.")
        Area { text: page.s.extra_instructions || ""; onDone: v => page.set("extra_instructions", v) }
    }

    Section {
        title: qsTr("Jarvis on Telegram")
        description: qsTr("Send Jarvis tasks from anywhere through Telegram.")
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 8
            Step { number: 1; format: Text.StyledText
                   text: qsTr("In Telegram, message <a href=\"https://t.me/BotFather\">@BotFather</a>, send /newbot and copy the token it gives you.") }
            Step { number: 2; text: qsTr("Paste it here.") }
            Step { number: 3; text: qsTr("Send your new bot the code below. Only that chat is answered.") }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Field { id: tgToken; Layout.fillWidth: true; echoMode: TextInput.Password
                    placeholderText: page.remote.token ? qsTr("Bot token saved · paste a new one to replace it") : qsTr("Paste your bot's token")
                    onAccepted: page.setToken(text) }
            Pill { implicitHeight: 44; text: qsTr("Save"); kind: tgToken.text.trim() !== "" ? "primary" : ""; enabled: tgToken.text.trim() !== ""; onClicked: page.setToken(tgToken.text) }
        }
        Status {
            visible: !!page.remote.token
            status: page.remote.paired ? "ok" : "working"
            format: Text.StyledText
            text: page.remote.paired ? qsTr("Paired with %1.").arg(page.remote.paired)
                  : qsTr("Send your bot this code: %1").arg(`<font face="${Theme.mono}" color="${Theme.accent}">${page.remote.code}</font>`)
        }
        Txt { kind: "small"; visible: !!page.remote.error; text: page.remote.error || ""; color: Theme.red; Layout.fillWidth: true }
        RowLayout {
            visible: !!page.remote.token
            spacing: 10
            Pill { visible: !!page.remote.paired; text: qsTr("Unpair"); onClicked: Api.post("/api/remote/unpair", {}, d => page.remote = d) }
            Pill { kind: "danger"; text: qsTr("Remove the bot"); onClicked: page.setToken("") }
        }
    }

    Section {
        title: qsTr("The Jarvis app")
        description: qsTr("The Jarvis Android app reaches this PC from anywhere through your own private relay. It's end-to-end encrypted: "
                     + "the relay only passes on scrambled data, and nothing on this PC is open to the internet.")
        RowLayout {  // setting the relay up, until there is one: Jarvis runs wrangler itself...
            Layout.fillWidth: true
            visible: !page.phone.relay || page.changingRelay
            spacing: 14
            Pill { kind: "primary"; symbol: "link"; enabled: !page.relaySetup.running
                   text: page.relaySetup.running ? qsTr("Setting up…") : qsTr("Set up my relay")
                   onClicked: Api.post("/api/phone/relay/setup", {}, d => page.phone = d, e => Backend.toast(e.error, true)) }
            Txt { kind: "small"; Layout.fillWidth: true
                  text: qsTr("Signs in to your free Cloudflare account in your browser, puts the relay online and saves its address.") }
        }
        Txt { visible: (!page.phone.relay || page.changingRelay) && (page.relaySetup.log || []).length > 0
              text: (page.relaySetup.log || []).join("\n"); color: Theme.text3; Layout.fillWidth: true
              font.family: Theme.mono; font.pixelSize: Theme.px(12); wrapMode: Text.WrapAnywhere }
        Txt { kind: "small"; visible: (!page.phone.relay || page.changingRelay) && !!page.relaySetup.error; text: page.relaySetup.error || ""; color: Theme.red; Layout.fillWidth: true }
        ColumnLayout {  // ...or the user does, and pastes the address
            Layout.fillWidth: true
            spacing: 8
            visible: !page.phone.relay || page.changingRelay
            Txt { kind: "label"; text: qsTr("Or by hand"); Layout.fillWidth: true }
            Step { number: 1; text: qsTr("In the relay folder of Jarvis's files, sign in to a free Cloudflare account:"); code: "npx wrangler login" }
            Step { number: 2; text: qsTr("Put the relay online:"); code: "npx wrangler deploy" }
            Step { number: 3; text: qsTr("Paste the address it prints here.") }
        }
        RowLayout {
            Layout.fillWidth: true
            visible: !page.phone.relay || page.changingRelay
            spacing: 10
            Field { id: relayUrl; Layout.fillWidth: true
                    placeholderText: qsTr("Your relay's address, like https://jarvis-relay.you.workers.dev")
                    onAccepted: page.setRelay(text) }
            Pill { implicitHeight: 44; text: qsTr("Save"); kind: relayUrl.text.trim() !== "" ? "primary" : ""; enabled: relayUrl.text.trim() !== ""; onClicked: page.setRelay(relayUrl.text) }
            Pill { implicitHeight: 44; kind: "ghost"; text: qsTr("Cancel"); visible: page.changingRelay
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
                    text: page.phone.connected ? qsTr("Connected") : (page.phone.error || qsTr("Connecting…"))
                }
            }
            Pill { kind: "ghost"; text: qsTr("Change"); onClicked: { page.changingRelay = true; relayUrl.forceActiveFocus() } }
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
                        Pill { kind: "ghost"; text: qsTr("Unpair"); onClicked: Api.post("/api/phone/unpair", { device: modelData.id }, d => page.phone = d) }
                    }
                }
            }
            Line {}
        }
        Pill { visible: !!page.phone.relay && !page.phone.pairing; symbol: "phone"
               kind: (page.phone.devices || []).length ? "" : "primary"
               text: (page.phone.devices || []).length ? qsTr("Pair another phone") : qsTr("Pair a phone")
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
                Txt { kind: "heading"; text: qsTr("Scan to pair"); Layout.fillWidth: true }
                Txt { kind: "small"; Layout.fillWidth: true
                      text: qsTr("In the Jarvis app, tap Pair and scan this code. It works once, for ten minutes.") }
            }
        }
        Timer {  // while a code is up: notice when the phone has paired, and keep the relay's status fresh
            interval: 2000; repeat: true; running: !!page.phone.pairing || (!!page.phone.relay && !page.phone.connected)
            onTriggered: Api.get("/api/phone", d => page.phone = d)
        }
        Timer {  // while wrangler works: its progress, then the relay it put online
            interval: 500; repeat: true; running: !!page.relaySetup.running
            onTriggered: Api.get("/api/phone", d => {
                if (!d.setup.running && !d.setup.error)
                    page.changingRelay = false
                page.phone = d
            })
        }
    }

    Section {
        title: qsTr("WhatsApp")
        description: qsTr("Jarvis links to your own WhatsApp like WhatsApp Web. It answers your contacts' messages that don't need you, "
                     + "saying it's your assistant, and picks up calls you miss to take a message. It's not an official "
                     + "WhatsApp feature: WhatsApp may block numbers that act like bots, so Jarvis answers only saved contacts, never groups.")
        Pill { visible: !page.wa.linked && page.wa.state === "off"; kind: "primary"; symbol: "chats"; text: qsTr("Link WhatsApp")
               onClicked: Api.post("/api/whatsapp/link", {}, d => page.wa = d, e => Backend.toast(e.error, true)) }
        Status { visible: page.wa.state === "starting" || page.wa.state === "connecting"; status: "working"
                 text: page.wa.linked ? qsTr("Connecting to WhatsApp…") : qsTr("Getting a code from WhatsApp…") }
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
                Txt { kind: "heading"; text: qsTr("Scan with WhatsApp"); Layout.fillWidth: true }
                Txt { kind: "small"; Layout.fillWidth: true
                      text: qsTr("On your phone: WhatsApp → Settings → Linked devices → Link a device, then scan this code. It renews itself.") }
            }
        }
        RowLayout {
            visible: page.wa.state === "connected"
            spacing: 14
            Status { status: page.wa.on_call ? "working" : "ok"
                     text: page.wa.on_call ? qsTr("On a call with %1").arg(page.wa.on_call)
                           : page.wa.name ? qsTr("Linked as %1").arg(page.wa.name) : qsTr("Linked") }
            Pill { kind: "ghost"; text: qsTr("Unlink"); onClicked: Api.post("/api/whatsapp/unlink", {}, d => page.wa = d) }
        }
        Txt { kind: "small"; visible: !!page.wa.error; text: page.wa.error || ""; color: Theme.red; Layout.fillWidth: true }
        Row2 {
            Setting { label: qsTr("Messages")
                Select { Layout.fillWidth: true; value: page.s.whatsapp_replies || "contacts"; onPicked: v => page.set("whatsapp_replies", v)
                         model: [{ value: "contacts", label: qsTr("Answer my contacts") }, { value: "off", label: qsTr("Just show them to me") }] } }
            Setting { label: qsTr("Calls")
                Select { Layout.fillWidth: true; value: page.s.whatsapp_calls || "answer"; onPicked: v => page.set("whatsapp_calls", v)
                         model: [{ value: "answer", label: qsTr("Pick up if I don't (20 s)") }, { value: "decline", label: qsTr("Decline them") },
                                 { value: "off", label: qsTr("Let them ring") }] } }
        }
        Row2 {
            Setting { label: qsTr("Always let through (one name per line, as WhatsApp shows it): never answered by Jarvis, always told to you out loud, even in quiet hours")
                Area { text: (page.s.whatsapp_always || []).join("\n"); placeholder: qsTr("e.g. Alex"); onDone: v => page.set("whatsapp_always", v) } }
            Setting { label: qsTr("Never answer (one name per line): Jarvis never replies or picks up, and only shows their messages in the chat")
                Area { text: (page.s.whatsapp_never || []).join("\n"); placeholder: qsTr("e.g. Sam"); onDone: v => page.set("whatsapp_never", v) } }
        }
        Setting { label: qsTr("What Jarvis tells people")
            Area { text: page.s.whatsapp_note || ""; placeholder: qsTr("e.g. I'm in class until 5, I'll answer after")
                   onDone: v => page.set("whatsapp_note", v) } }
        Timer {  // while it's starting or showing a code: notice when the phone has linked
            interval: 2000; repeat: true; running: page.wa.state === "qr" || page.wa.state === "starting" || page.wa.state === "connecting" || !!page.wa.on_call
            onTriggered: Api.get("/api/whatsapp", d => page.wa = d)
        }
    }

    Section {
        title: qsTr("Your data")
        description: qsTr("On this PC Jarvis keeps what it remembers about you, your conversations, reminders and routines, short clips "
                     + "of your wake word (to learn your voice) and a log. What you say after the wake word, and screenshots when a "
                     + "task needs the screen, go to Google Gemini; account actions go through Composio.")
        Row2 {
            Setting { label: qsTr("Keep conversations and logs for")
                Select { Layout.fillWidth: true; value: String(page.s.keep_days || 0); onPicked: v => page.set("keep_days", v)
                         model: [{ value: "7", label: qsTr("A week") }, { value: "30", label: qsTr("A month") }, { value: "90", label: qsTr("3 months") },
                                 { value: "365", label: qsTr("A year") }, { value: "0", label: qsTr("Forever") }] } }
            Item { Layout.fillWidth: true }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 14
            Pill { kind: "danger"; symbol: "trash"; text: page.confirmDelete ? qsTr("Press again to delete it all") : qsTr("Delete everything Jarvis keeps about me")
                   onClicked: {
                       if (!page.confirmDelete) { page.confirmDelete = true; disarm.restart(); return }
                       page.confirmDelete = false
                       Api.post("/api/data/delete", {}, () => Backend.toast(qsTr("Deleted. Keys, accounts and settings are kept."), false),
                                e => Backend.toast(e.error, true))
                   } }
            Txt { kind: "small"; text: qsTr("Keys, account sign-ins and settings stay."); color: Theme.text3; Layout.fillWidth: true }
        }
        Timer { id: disarm; interval: 4000; onTriggered: page.confirmDelete = false }
    }

    Section {
        title: qsTr("Move to another computer")
        description: qsTr("One file with your settings, memory, reminders, scheduled tasks, routines, plugins, conversations and the "
                     + "clips Jarvis learned your voice from. Keys, account sign-ins, WhatsApp and your phone aren't in it: set "
                     + "those up again on the other computer.")
        RowLayout {
            Layout.fillWidth: true
            spacing: 14
            Pill { text: qsTr("Save a backup")
                   onClicked: { saver.selectedFile = StandardPaths.writableLocation(StandardPaths.DocumentsLocation) + "/jarvis-backup-"
                                    + new Date().toISOString().slice(0, 10) + ".zip"; saver.open() } }
            Pill { kind: "ghost"; text: qsTr("Bring one in"); onClicked: opener.open() }
            Txt { kind: "small"; text: qsTr("Bringing one in replaces what's on this computer (conversations are added), then Jarvis restarts.")
                  color: Theme.text3; Layout.fillWidth: true }
        }
        FileDialog {
            id: saver
            fileMode: FileDialog.SaveFile
            title: qsTr("Save a Jarvis backup")
            nameFilters: [qsTr("Jarvis backups (*.zip)")]
            defaultSuffix: "zip"
            onAccepted: Api.post("/api/data/export", { path: String(selectedFile) }, d => Backend.toast(qsTr("Saved to %1").arg(d.path), false),
                                 e => Backend.toast(e.error, true))
        }
        FileDialog {
            id: opener
            title: qsTr("Bring in a Jarvis backup")
            nameFilters: [qsTr("Jarvis backups (*.zip)")]
            onAccepted: Api.post("/api/data/import", { path: String(selectedFile) },
                                 d => Backend.toast(d.skipped.length ? qsTr("Brought in (left at their defaults here: %1): Jarvis is restarting").arg(d.skipped.join(", "))
                                                    : qsTr("Brought in: Jarvis is restarting"), false),
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
                    : page.update.available ? (page.update.how ? qsTr("%1 is out (%2)").arg(page.update.latest).arg(page.update.how)
                                                               : qsTr("%1 is out").arg(page.update.latest))
                    : page.update.latest ? qsTr("Up to date") : "" }
        Pill { text: page.updating ? qsTr("Updating…") : page.update.can_update ? qsTr("Update now") : qsTr("Check for updates")
               kind: page.update.can_update ? "primary" : "ghost"; enabled: !page.updating
               onClicked: page.update.can_update ? page.installUpdate() : page.checkUpdate() }
        Pill { kind: "ghost"; text: qsTr("Run the setup again"); onClicked: page.setupAgain() }
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
            placeholderText: qsTr("e.g. Keep answers short.")
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
