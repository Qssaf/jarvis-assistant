import QtCore
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import Jarvis

// Settings save themselves as you change them. Tabs show one part at a time; a search shows what matches from all of them.
Item {
    id: page
    objectName: "settingsPage"
    property var s: ({})
    property var voices: []
    property var languages: ({})
    property var windowLanguages: ({})  // code -> its own name
    property var wakeWords: ({})
    property bool learned: false  // a verifier is learned for the chosen wake word
    property bool passphraseSet: false
    property bool peopleLock: false  // the People page has a password
    property bool peopleSecret: false  // ...and there's a secret one, for the people hidden on it
    property bool ownWake: false  // "Your own model" picked, before its path is in
    readonly property bool customWake: !!page.s.wake_word && !(page.s.wake_word in page.wakeWords)
    property bool confirmDelete: false
    property var remote: ({})
    property var phone: ({})
    property var wa: ({})
    property var dc: ({})
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
    signal goTo(string key)  // another page of the window
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
        Api.get("/api/discord", d => dc = d)
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
    function took(d) { s = d.settings; wakeWords = d.wake_words; learned = d.voice_learned; passphraseSet = d.passphrase; peopleLock = !!d.people_lock; peopleSecret = !!d.people_secret }
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
    function setPeopleLock(old, fresh) {  // (never kept in the page: both boxes are emptied)
        Api.post("/api/people/password", { old: old, "new": fresh }, d => {
            lockOld.text = ""; lockNew.text = ""; peopleLock = !!d.lock
            Backend.toast(d.lock ? qsTr("The People page asks for its password now") : qsTr("Password removed: the People page is open"), false)
        }, e => Backend.toast(e.error, true))
    }
    function setPeopleSecret(old, fresh) {
        Api.post("/api/people/secret", { old: old, "new": fresh }, d => {
            secretOld.text = ""; secretNew.text = ""; peopleSecret = !!d.secret
            Backend.toast(d.secret ? qsTr("People you hide are encrypted with this password now") : qsTr("Secret password removed: nobody is hidden any more"), false)
        }, e => Backend.toast(e.error, true))
    }
    function setPassphrase(text) {
        Api.post("/api/passphrase", { passphrase: text }, d => { passphraseSet = d.passphrase; passphrase.text = ""
                 Backend.toast(d.passphrase ? qsTr("Passphrase saved") : qsTr("Passphrase removed"), false) }, e => Backend.toast(e.error, true))
    }
    Component.onCompleted: load()

    // ---- tabs and search
    readonly property var tabs: [{ key: "voice", label: qsTr("Voice"), symbol: "mic" }, { key: "day", label: qsTr("Your day"), symbol: "sun" },
                                 { key: "window", label: qsTr("Window"), symbol: "screen" }, { key: "messages", label: qsTr("Messages"), symbol: "chats" },
                                 { key: "phone", label: qsTr("Phone"), symbol: "phone" }, { key: "data", label: qsTr("Your data"), symbol: "shield" },
                                 { key: "advanced", label: qsTr("Advanced"), symbol: "wrench" }]
    property string tab: "voice"  // (kept while the window is open)
    readonly property string query: search.text.trim()
    readonly property var terms: fold(query).split(/\s+/).filter(w => w !== "")
    readonly property bool searching: terms.length > 0
    property var groups: []  // every section, each saying which tab it's on
    onTabChanged: body.toTop()
    onQueryChanged: body.toTop()
    function pick(key) { tab = key; search.clear() }
    function nextTab(by) {
        const i = (tabs.findIndex(t => t.key === tab) + by + tabs.length) % tabs.length
        pick(tabs[i].key)
        tabRepeater.itemAt(i).forceActiveFocus(Qt.TabFocusReason)  // (with its ring)
    }
    function fold(text) { return String(text).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "") }  // (é finds e)
    function found(text) { const t = fold(text); return terms.every(w => t.indexOf(w) >= 0) }
    // A row shows when every word is in its own text or its section's title, or when its section (or block) matched whole.
    // Rows and sections decide from their children's `showing`, never `visible`: a hidden parent makes every `visible` false.
    function within(item) {  // the section (or block) a row sits in
        for (let up = item.parent; up; up = up.parent)
            if (up.whole !== undefined) return up
        return null
    }
    function shows(home, words) { return !searching || (!!home && home.whole) || found(words + " " + (home && home.title || "")) }
    function choices(item) {  // what a setting's drop-downs offer: "drafts" finds WhatsApp's Messages
        let out = []
        for (const c of item.children)
            if (c.textRole === "label" && c.model && typeof c.model.map === "function") out = out.concat(c.model.map(o => o.label))
        return out.join(" ")
    }
    function anyShowing(items) {
        for (const c of items)
            if (c.showing) return true
        return false
    }
    function count(items) {  // the matching rows among these
        let n = 0
        for (const c of items)
            if (c.showing) n += c.words !== undefined ? 1 : count(c.children)
        return n
    }
    function hitsIn(key) { return groups.reduce((n, g) => n + (g.tab === key ? g.hits : 0), 0) }
    readonly property bool anyHit: groups.some(g => g.hit)
    readonly property int columnWidth: Math.min(width - 2 * Theme.margin, Theme.pageWidth)  // (as the scrolling column below)
    // (icons on the tabs only while they all fit on one line with them)
    readonly property bool tabIcons: {
        let wide = 0
        for (const t of tabBar.children)
            if (t.full) wide += t.full + tabBar.spacing
        return wide <= tabBar.width + tabBar.spacing
    }
    Shortcut { id: find; sequence: "Ctrl+F"; enabled: page.visible; onActivated: { search.forceActiveFocus(Qt.ShortcutFocusReason); search.selectAll() } }

    ColumnLayout {  // the header, the search and the tabs stay in place while the settings scroll under them
        id: head
        anchors { top: parent.top; topMargin: Theme.margin; horizontalCenter: parent.horizontalCenter }
        width: page.columnWidth
        spacing: 0
        PageHeader {
            Layout.fillWidth: true
            Layout.bottomMargin: 20
            Layout.rightMargin: Math.max(0, 112 - (page.width - page.columnWidth) / 2)  // (clear of the window buttons)
            title: qsTr("Settings")
            hint: qsTr("Changes are saved at once. Models and API keys are on the Models page.")
            Field {
                id: search
                objectName: "settingsSearch"
                width: Math.round(Math.min(300, Math.max(220, head.width * 0.36)))
                placeholderText: qsTr("Search settings")
                Accessible.name: qsTr("Search settings")
                readonly property int endRoom: text !== "" ? 42 : keyHint.visible ? keyHint.implicitWidth + 26 : 14
                leftPadding: LayoutMirroring.enabled ? endRoom : 40  // (paddings don't mirror by themselves; the icons' anchors do)
                rightPadding: LayoutMirroring.enabled ? 40 : endRoom
                Keys.onShortcutOverride: e => e.accepted = e.key === Qt.Key_Escape && text !== ""  // (Esc clears it rather than stopping Jarvis)
                Keys.onEscapePressed: clear()
                TextMetrics { id: placeholder; font: search.font; text: search.placeholderText }
                Icon { name: "search"; size: 16; color: search.activeFocus ? Theme.accent : Theme.text3
                       anchors { left: parent.left; leftMargin: 14; verticalCenter: parent.verticalCenter } }
                Txt { id: keyHint; kind: "small"; color: Theme.text3; text: find.nativeText; wrapMode: Text.NoWrap
                      visible: search.text === "" && !search.activeFocus && text !== ""
                               && placeholder.width + implicitWidth + 40 + 26 <= search.width  // (never over the placeholder: big text, a long language)
                      anchors { right: parent.right; rightMargin: 14; verticalCenter: parent.verticalCenter } }
                IconButton { symbol: "close"; size: 30; glyph: 14; tip: qsTr("Clear the search"); visible: search.text !== ""
                             anchors { right: parent.right; rightMargin: 7; verticalCenter: parent.verticalCenter }
                             onClicked: { search.clear(); search.forceActiveFocus() } }
            }
        }
        FocusScope {  // one Tab stop, on the tab that's open; the arrow keys move along
            Layout.fillWidth: true
            Layout.preferredHeight: tabBar.implicitHeight
            activeFocusOnTab: true
            Accessible.role: Accessible.PageTabList
            Flow {
                id: tabBar
                width: parent.width
                spacing: 4
                Repeater { id: tabRepeater; model: page.tabs; PageTab {} }
            }
        }
        Rectangle {  // brighter once settings have scrolled under it
            Layout.fillWidth: true; Layout.topMargin: 12; Layout.preferredHeight: 1
            color: body.scrolled ? Theme.strokeStrong : Theme.stroke
            Behavior on color { ColorAnimation { duration: Theme.fast } }
        }
    }

    ScrollPage {
        id: body
        anchors { top: head.bottom; left: parent.left; right: parent.right; bottom: parent.bottom }
        headroom: 20

        ColumnLayout {  // a search that finds nothing
            Layout.fillWidth: true
            Layout.topMargin: 48
            spacing: 10
            visible: page.searching && !page.anyHit
            Icon { Layout.alignment: Qt.AlignHCenter; name: "search"; size: 22; color: Theme.text3 }
            Txt { Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; textFormat: Text.PlainText
                  text: qsTr("No setting matches “%1”").arg(page.query) }
            Txt { Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; kind: "small"
                  text: qsTr("Try another word, or pick a tab above.") }
            Pill { Layout.alignment: Qt.AlignHCenter; Layout.topMargin: 6; kind: "ghost"; text: qsTr("Clear the search"); onClicked: search.clear() }
        }

        // ================================================================ Voice
        Group {
            tab: "voice"
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
            Rows {
                SwitchRow { text: qsTr("Fast voice"); hint: qsTr("Answer without thinking first: about 0.3 s quicker, a little less sharp")
                            checked: !!page.s.fast_voice; onToggled: page.set("fast_voice", checked) }
                SwitchRow { text: qsTr("Speak replies to typed messages"); checked: !!page.s.speak_typed_replies
                            onToggled: page.set("speak_typed_replies", checked) }
                SwitchRow { text: qsTr("Always use the backup voice")
                            hint: qsTr("Hear and speak with the models on the Models page instead of Gemini Live, for keys without it. Off, the backup voice only answers while Gemini Live can't be reached")
                            checked: !!page.s.always_backup_voice; onToggled: page.set("always_backup_voice", checked) }
            }
        }

        Group {
            tab: "voice"
            title: qsTr("Listening")
            description: qsTr("When Jarvis wakes up, and how long it keeps listening.")
            Row2 {
                Setting { label: qsTr("Wake word")
                    Select { Layout.fillWidth: true; value: page.customWake || page.ownWake ? "custom" : (page.s.wake_word || "hey_jarvis")
                             model: Object.keys(page.wakeWords).map(k => ({ value: k, label: page.wakeWords[k] }))
                                    .concat([{ value: "custom", label: qsTr("Your own model…") }])
                             onPicked: v => { page.ownWake = v === "custom"; if (v !== "custom") page.set("wake_word", v); else ownModel.forceActiveFocus() } } }
                Setting { label: qsTr("Path of your own openWakeWord .onnx model")
                    applies: page.customWake || page.ownWake
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
            Rows {
                SwitchRow { text: qsTr("Learn my voice"); hint: qsTr("Wake-ups you dismiss teach Jarvis what isn't you")
                            checked: !!page.s.learn_my_voice; onToggled: page.set("learn_my_voice", checked) }
                SwitchRow { text: qsTr("Only wake for my voice")
                            hint: !page.learned ? qsTr("Nothing learned for this wake word yet (Learn my voice needs a few wake-ups first): until then anyone can wake Jarvis")
                                  : !page.s.learn_my_voice ? qsTr("Needs Learn my voice on: until then anyone can wake Jarvis")
                                  : qsTr("Someone else saying the wake word doesn't wake Jarvis. Talk and push to talk always work")
                            checked: !!page.s.only_my_voice; onToggled: page.set("only_my_voice", checked) }
                SwitchRow { text: qsTr("Echo cancelling"); hint: Qt.platform.os === "windows"
                                  ? qsTr("Keeps the PC's own sound (Jarvis, games, videos, calls) out of the mic, so it isn't heard as you, and you can "
                                         + "talk over Jarvis (experimental on Windows: Health says if it's working; restart Jarvis to apply)")
                                  : qsTr("Keeps the PC's own sound (Jarvis, games, videos, calls) out of the mic, so it isn't heard as you, and you can "
                                         + "talk over Jarvis (PipeWire; restart Jarvis to apply)")
                            checked: !!page.s.echo_cancel; onToggled: page.set("echo_cancel", checked) }
                SwitchRow { text: qsTr("Listen through a Bluetooth headset")
                            hint: qsTr("When a Bluetooth headset's microphone is the default one, Jarvis listens through it, and the headset stays in call "
                                       + "quality (mono and muffled) while Jarvis runs. Off, Jarvis uses the PC's own microphone and the headset keeps its sound")
                            applies: Qt.platform.os !== "windows"  // (Windows records from the default microphone, whatever it is)
                            checked: !!page.s.bluetooth_mic; onToggled: page.set("bluetooth_mic", checked) }
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
            Block {  // push to talk
                words: [qsTr("Push to talk"), qsTr("Bind these to keyboard shortcuts (KDE: System Settings → Keyboard → Shortcuts → Add New → Command)."),
                        qsTr("Start listening"), qsTr("Drag over part of the screen and ask about it")]
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

        // ================================================================ Your day
        Group {
            tab: "day"
            title: qsTr("Your day")
            description: qsTr("The weather, briefings and heads-ups Jarvis gives you.")
            Setting { label: qsTr("Home city, for the weather (empty: guess from your network)")
                Field { Layout.fillWidth: true; text: page.s.home_city || ""; placeholderText: qsTr("e.g. London")
                        onEditingFinished: if (text !== page.s.home_city) page.set("home_city", text) } }
            Rows {
                SwitchRow { text: qsTr("Morning briefing"); hint: qsTr("The first time Jarvis starts in a morning, it tells you about your day")
                            checked: !!page.s.morning_briefing; onToggled: page.set("morning_briefing", checked) }
                SwitchRow { text: qsTr("Do not disturb"); hint: qsTr("Jarvis doesn't speak up on its own: reminders, results and messages only go to the chat, notifications and your phone. It still answers you (also in the tray menu)")
                            checked: !!page.s.do_not_disturb; onToggled: page.set("do_not_disturb", checked) }
                SwitchRow { text: qsTr("Quiet over full-screen apps"); hint: qsTr("While a game or a film is full screen, Jarvis keeps what it would say on its own to the chat and notifications. Reminders still speak")
                            checked: !!page.s.quiet_fullscreen; onToggled: page.set("quiet_fullscreen", checked) }
                SwitchRow { text: qsTr("Classroom deadlines"); hint: qsTr("Reminders a day and two hours before work is due (skipped once you've turned it in)")
                            checked: !!page.s.deadline_reminders; onToggled: page.set("deadline_reminders", checked) }
                SwitchRow { text: qsTr("Calendar heads-up"); hint: qsTr("A reminder ten minutes before each Google Calendar event")
                            checked: !!page.s.calendar_reminders; onToggled: page.set("calendar_reminders", checked) }
                SwitchRow { text: qsTr("Keep track of my promises"); hint: qsTr("When you write \"I'll send it tomorrow\" on WhatsApp, Discord or email, Jarvis sets a reminder, or puts it on the evening list")
                            checked: !!page.s.track_promises; onToggled: page.set("track_promises", checked) }
            }
            Row2 {
                Setting { label: qsTr("Evening list at (who's waiting on you, what's due tomorrow; empty: none)")
                    Field { Layout.fillWidth: true; text: page.s.evening_digest || ""; placeholderText: qsTr("e.g. 20:00")
                            onEditingFinished: if (text !== page.s.evening_digest) page.set("evening_digest", text) } }
                Item { Layout.fillWidth: true }
            }
            Row2 {
                Setting { label: qsTr("Quiet hours from (empty: none)")
                    Field { Layout.fillWidth: true; text: page.s.quiet_from || ""; placeholderText: qsTr("e.g. 22:00")
                            onEditingFinished: if (text !== page.s.quiet_from) page.set("quiet_from", text) } }
                Setting { label: qsTr("Until (the morning briefing waits for it)"); also: qsTr("Quiet hours from (empty: none)")
                    Field { Layout.fillWidth: true; text: page.s.quiet_until || ""; placeholderText: qsTr("e.g. 07:00")
                            onEditingFinished: if (text !== page.s.quiet_until) page.set("quiet_until", text) } }
            }
        }

        // ================================================================ Window
        Group {
            tab: "window"
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
            Rows {
                SwitchRow { text: qsTr("Show Jarvis's thinking in the chat"); checked: !!page.s.show_thinking
                            onToggled: page.set("show_thinking", checked) }
                SwitchRow { text: qsTr("Start Jarvis when I log in"); checked: !!page.s.start_at_login
                            onToggled: page.set("start_at_login", checked) }
                SwitchRow { text: qsTr("Ask before risky actions")
                            hint: qsTr("Commands that delete, install or shut down, and account changes (sending email, new events), wait for your yes unless you asked for exactly that")
                            checked: page.s.safety !== "full"; onToggled: page.set("safety", checked ? "ask" : "full") }
            }
        }

        Group {
            tab: "window"
            title: qsTr("Your instructions")
            description: qsTr("How Jarvis should behave, and things it should know about you.")
            Area { text: page.s.extra_instructions || ""; onDone: v => page.set("extra_instructions", v) }
        }

        // ================================================================ Messages
        Group {
            tab: "messages"
            title: qsTr("WhatsApp")
            description: qsTr("Jarvis links to your own WhatsApp like WhatsApp Web. It answers your contacts' messages that don't need you, "
                         + "saying it's your assistant, and picks up calls you miss to take a message. It's not an official "
                         + "WhatsApp feature: WhatsApp may block numbers that act like bots, so Jarvis answers only saved contacts, never groups.")
            Block {  // linking, and whether it's linked
                words: [qsTr("Link WhatsApp"), qsTr("Scan with WhatsApp"), qsTr("Unlink")]
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
            }
            Row2 {
                Setting { label: qsTr("Messages")
                    Select { Layout.fillWidth: true; value: page.s.whatsapp_replies || "contacts"; onPicked: v => page.set("whatsapp_replies", v)
                             model: [{ value: "contacts", label: qsTr("Answer my contacts") }, { value: "drafts", label: qsTr("Draft replies for me to send") },
                                     { value: "off", label: qsTr("Just show them to me") }] }
                    Txt { kind: "small"; Layout.fillWidth: true; visible: page.s.whatsapp_replies === "drafts"
                          text: qsTr("Jarvis writes a reply to your contacts' messages that don't need you and tells you. Nothing is sent until you say \"send it\".") } }
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
            Rows {
                SwitchRow { text: qsTr("Tell people when I'm busy")
                            hint: qsTr("From your Google Calendar: only the times, never what you're doing")
                            checked: !!page.s.whatsapp_share_free; onToggled: page.set("whatsapp_share_free", checked) }
            }
            Timer {  // while it's starting or showing a code: notice when the phone has linked
                interval: 2000; repeat: true; running: page.wa.state === "qr" || page.wa.state === "starting" || page.wa.state === "connecting" || !!page.wa.on_call
                onTriggered: Api.get("/api/whatsapp", d => page.wa = d)
            }
        }

        Group {
            tab: "messages"
            title: qsTr("Discord")
            description: qsTr("Jarvis reads and sends Discord messages for you through Vesktop, inside your own Discord: ask it what's new, "
                         + "or to message, reply or react in a DM or server channel. New DMs and pings show up in Jarvis's chat.")
            Block {  // whether Vesktop is there for it
                words: [qsTr("Connected to Vesktop"), qsTr("Restart Vesktop")]
                Status { visible: page.dc.state === "connected"; status: "ok"; text: qsTr("Connected to Vesktop") }
                Status { visible: page.dc.state === "starting"; status: "working"; text: qsTr("Waiting for Vesktop…") }
                Txt { kind: "small"; visible: page.dc.state === "off"; Layout.fillWidth: true
                      text: qsTr("Vesktop isn't running. Jarvis uses Discord through Vesktop (Discord with Vencord built in): install it, then sign in.") }
                RowLayout {
                    visible: page.dc.state === "restart"
                    spacing: 14
                    Txt { kind: "small"; Layout.fillWidth: true
                          text: qsTr("Vesktop needs a restart with Jarvis's connection turned on (a call in Vesktop would drop).") }
                    Pill { kind: "primary"; symbol: "chats"; text: qsTr("Restart Vesktop")
                           onClicked: Api.post("/api/discord/connect", {}, d => page.dc = d, e => Backend.toast(e.error, true)) }
                }
            }
            Setting { label: qsTr("Messages")
                Select { Layout.fillWidth: true; value: page.s.discord_replies || "off"; onPicked: v => page.set("discord_replies", v)
                         model: [{ value: "off", label: qsTr("Just show them to me") },
                                 { value: "friends", label: qsTr("Answer my friends' DMs (Discord may ban accounts that act like bots)") }] } }
            Row2 {
                Setting { label: qsTr("Always let through (one name per line, as Discord shows it): never answered by Jarvis, always told to you out loud, even in quiet hours")
                    Area { text: (page.s.discord_always || []).join("\n"); placeholder: qsTr("e.g. Alex"); onDone: v => page.set("discord_always", v) } }
                Setting { label: qsTr("Never answer (one name per line): Jarvis never replies, and only shows their messages in the chat")
                    Area { text: (page.s.discord_never || []).join("\n"); placeholder: qsTr("e.g. Sam"); onDone: v => page.set("discord_never", v) } }
            }
            Note { text: qsTr("Replies use what Jarvis tells people from the WhatsApp section. You can also just say \"don't answer Sam\" or \"tell me when Alex messages me\".") }
            Timer {
                interval: 2000; repeat: true; running: page.dc.state === "starting"
                onTriggered: Api.get("/api/discord", d => page.dc = d)
            }
        }

        Group {
            tab: "messages"
            title: qsTr("People")
            description: qsTr("Jarvis gets to know the people you chat with one to one, so it knows who someone is when you mention them. The People page shows what it understood, with your notes and promises.")
            Rows {
                SwitchRow { text: qsTr("Understand the people I chat with")
                            hint: qsTr("Now and then, the latest messages of your one-to-one WhatsApp and Discord chats go to your model to write a short profile of each person: who they are to you, how they write, what's open between you. Kept on this PC; groups are never read")
                            checked: !!page.s.people_profiles; onToggled: page.set("people_profiles", checked) }
            }
            Setting { label: qsTr("Write a profile again after"); applies: !!page.s.people_profiles
                also: qsTr("refresh profiles days")
                Select { Layout.fillWidth: true; value: String(page.s.people_refresh_days || 7); onPicked: v => page.set("people_refresh_days", Number(v))
                         model: [{ value: "3", label: qsTr("3 days") }, { value: "7", label: qsTr("A week") }, { value: "14", label: qsTr("Two weeks") },
                                 { value: "30", label: qsTr("A month") }].concat([3, 7, 14, 30].indexOf(page.s.people_refresh_days || 7) < 0
                                 ? [{ value: String(page.s.people_refresh_days), label: qsTr("%n day(s)", "", page.s.people_refresh_days) }] : []) } }
            Setting {
                id: lockRow
                readonly property string about: qsTr("Asked for before the People page shows anyone. The page locks again after 5 minutes unused, when "
                                                     + "the window is put away and at every start. It keeps the page from someone at your screen. "
                                                     + "Forgot it: “jarvis --reset-people-lock” in a terminal takes both passwords here off.")
                label: qsTr("Password for the People page")
                also: about + " " + qsTr("lock private security hide")
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Txt { kind: "small"; text: lockRow.about; Layout.fillWidth: true }
                    PasswordField { id: lockOld; Layout.fillWidth: true; visible: page.peopleLock
                            placeholderText: qsTr("Current password"); Accessible.name: qsTr("Current password for the People page") }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        PasswordField { id: lockNew; Layout.fillWidth: true
                                placeholderText: page.peopleLock ? qsTr("Password set · type a new one to change it") : qsTr("A password only you know, 4 characters or more")
                                Accessible.name: qsTr("New password for the People page")
                                onAccepted: if (savePeopleLock.enabled) page.setPeopleLock(lockOld.text, text) }
                        Pill { id: savePeopleLock; implicitHeight: 44; text: page.peopleLock ? qsTr("Change") : qsTr("Set password")
                               enabled: lockNew.text !== "" && (!page.peopleLock || lockOld.text !== ""); kind: enabled ? "primary" : ""
                               onClicked: page.setPeopleLock(lockOld.text, lockNew.text) }
                        Pill { implicitHeight: 44; kind: "ghost"; text: qsTr("Remove"); visible: page.peopleLock; enabled: lockOld.text !== ""
                               onClicked: page.setPeopleLock(lockOld.text, "") }
                    }
                }
            }
            Setting {
                id: secretRow
                readonly property string about: qsTr("A second password, for the people you hide on the People page: they're encrypted with it, and "
                                                     + "listed only when you type it in that page's search box and press Enter (the same again puts "
                                                     + "them away). Until you type it after a start, Jarvis doesn't know them either. Forget it and "
                                                     + "they stay encrypted until it's typed again.")
                label: qsTr("Secret password, for people you hide")
                also: about + " " + qsTr("hidden secret encrypt private")
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Txt { kind: "small"; text: secretRow.about; Layout.fillWidth: true }
                    PasswordField { id: secretOld; Layout.fillWidth: true; visible: page.peopleSecret
                                    placeholderText: qsTr("Current secret password"); Accessible.name: qsTr("Current secret password") }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        PasswordField { id: secretNew; Layout.fillWidth: true
                                        placeholderText: page.peopleSecret ? qsTr("Secret password set · type a new one to change it") : qsTr("A second password only you know, 4 characters or more")
                                        Accessible.name: qsTr("New secret password")
                                        onAccepted: if (saveSecret.enabled) page.setPeopleSecret(secretOld.text, text) }
                        Pill { id: saveSecret; implicitHeight: 44; text: page.peopleSecret ? qsTr("Change") : qsTr("Set secret password")
                               enabled: secretNew.text !== "" && (!page.peopleSecret || secretOld.text !== ""); kind: enabled ? "primary" : ""
                               onClicked: page.setPeopleSecret(secretOld.text, secretNew.text) }
                        Pill { implicitHeight: 44; kind: "ghost"; text: qsTr("Remove"); visible: page.peopleSecret; enabled: secretOld.text !== ""
                               onClicked: page.setPeopleSecret(secretOld.text, "") }
                    }
                }
            }
        }

        // ================================================================ Phone
        Group {
            tab: "phone"
            title: qsTr("The Jarvis app")
            description: qsTr("The Jarvis Android app reaches this PC from anywhere through your own private relay. It's end-to-end encrypted: "
                         + "the relay only passes on scrambled data, and nothing on this PC is open to the internet.")
            Rows {
                SwitchRow { text: qsTr("Connect directly on your own network")
                            hint: qsTr("On the same Wi-Fi, or a VPN like Tailscale, paired phones reach this PC without the relay, and pairing needs no relay either. Your firewall may need to allow Jarvis")
                            checked: !!page.s.phone_direct; onToggled: page.set("phone_direct", checked) }
                Line {}
            }
            Block {  // setting the relay up, until there is one: Jarvis runs wrangler itself, or the user does and pastes the address
                applies: !page.phone.relay || page.changingRelay
                words: [qsTr("Set up my relay"), qsTr("Signs in to your free Cloudflare account in your browser, puts the relay online and saves its address."),
                        qsTr("Or by hand"), qsTr("Your relay's address, like https://jarvis-relay.you.workers.dev")]
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 14
                    Pill { kind: "primary"; symbol: "link"; enabled: !page.relaySetup.running
                           text: page.relaySetup.running ? qsTr("Setting up…") : qsTr("Set up my relay")
                           onClicked: Api.post("/api/phone/relay/setup", {}, d => page.phone = d, e => Backend.toast(e.error, true)) }
                    Txt { kind: "small"; Layout.fillWidth: true
                          text: qsTr("Signs in to your free Cloudflare account in your browser, puts the relay online and saves its address.") }
                }
                Txt { visible: (page.relaySetup.log || []).length > 0
                      text: (page.relaySetup.log || []).join("\n"); color: Theme.text3; Layout.fillWidth: true
                      font.family: Theme.mono; font.pixelSize: Theme.px(12); wrapMode: Text.WrapAnywhere }
                Txt { kind: "small"; visible: !!page.relaySetup.error; text: page.relaySetup.error || ""; color: Theme.red; Layout.fillWidth: true }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Txt { kind: "label"; text: qsTr("Or by hand"); Layout.fillWidth: true }
                    Step { number: 1; text: qsTr("In the relay folder of Jarvis's files, sign in to a free Cloudflare account:"); code: "npx wrangler login" }
                    Step { number: 2; text: qsTr("Put the relay online:"); code: "npx wrangler deploy" }
                    Step { number: 3; text: qsTr("Paste the address it prints here.") }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Field { id: relayUrl; Layout.fillWidth: true
                            placeholderText: qsTr("Your relay's address, like https://jarvis-relay.you.workers.dev")
                            onAccepted: page.setRelay(text) }
                    Pill { implicitHeight: 44; text: qsTr("Save"); kind: relayUrl.text.trim() !== "" ? "primary" : ""; enabled: relayUrl.text.trim() !== ""; onClicked: page.setRelay(relayUrl.text) }
                    Pill { implicitHeight: 44; kind: "ghost"; text: qsTr("Cancel"); visible: page.changingRelay
                           onClicked: { page.changingRelay = false; relayUrl.text = "" } }
                }
            }
            Block {  // the relay in use and whether it's reachable
                applies: !!page.phone.relay && !page.changingRelay
                words: [page.phone.relay || "", qsTr("Connected"), qsTr("Change")]
                RowLayout {
                    Layout.fillWidth: true
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
            }
            Block {  // the phones paired
                applies: (page.phone.devices || []).length > 0
                words: (page.phone.devices || []).map(d => d.name).concat([qsTr("Unpair")])
                spacing: 0
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
            Block {  // pairing one
                applies: !!page.phone.relay || !!page.s.phone_direct || !!page.phone.pairing
                words: [qsTr("Pair a phone"), qsTr("Pair another phone"), qsTr("Scan to pair")]
                Pill { visible: !page.phone.pairing; symbol: "phone"
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

        Group {
            tab: "phone"
            title: qsTr("Jarvis on Telegram")
            description: qsTr("Send Jarvis tasks from anywhere through Telegram.")
            Block {
                words: [qsTr("Paste your bot's token"), qsTr("Send your new bot the code below. Only that chat is answered."), qsTr("Unpair"), qsTr("Remove the bot")]
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
        }

        // ================================================================ Your data
        Group {
            tab: "data"
            title: qsTr("Your data")
            description: qsTr("On this PC Jarvis keeps what it remembers about you, your conversations, reminders and routines, short clips "
                         + "of your wake word (to learn your voice) and a log. What you say after the wake word, and screenshots when a "
                         + "task needs the screen, go to Google Gemini; account actions go through Composio.")
            Rows {
                SwitchRow { text: qsTr("Screen history"); hint: qsTr("Jarvis notes which window you have in front (its title only, never what's in it, on this PC) so you can ask \"what was that site I had open yesterday?\". Private browsing and password managers are skipped; kept two weeks at most")
                            checked: !!page.s.screen_history; onToggled: page.set("screen_history", checked) }
                SwitchRow { text: qsTr("Learn from conversations"); hint: qsTr("When a conversation is over, Jarvis adds lasting things you said about yourself to its memory, and shows each one in the chat")
                            checked: !!page.s.learn_from_talk; onToggled: page.set("learn_from_talk", checked) }
            }
            Row2 {
                Setting { label: qsTr("Keep conversations and logs for")
                    Select { Layout.fillWidth: true; value: String(page.s.keep_days || 0); onPicked: v => page.set("keep_days", v)
                             model: [{ value: "7", label: qsTr("A week") }, { value: "30", label: qsTr("A month") }, { value: "90", label: qsTr("3 months") },
                                     { value: "365", label: qsTr("A year") }, { value: "0", label: qsTr("Forever") }] } }
                Item { Layout.fillWidth: true }
            }
            Block {
                words: [qsTr("Delete everything Jarvis keeps about me"), qsTr("Keys, account sign-ins and settings stay.")]
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
            }
            Timer { id: disarm; interval: 4000; onTriggered: page.confirmDelete = false }
        }

        Group {
            tab: "data"
            title: qsTr("Move to another computer")
            description: qsTr("One file with your settings, memory, reminders, scheduled tasks, routines, plugins, conversations and the "
                         + "clips Jarvis learned your voice from. Keys, account sign-ins, WhatsApp and your phone aren't in it: set "
                         + "those up again on the other computer.")
            Block {
                words: [qsTr("Save a backup"), qsTr("Bring one in"), qsTr("Bringing one in replaces what's on this computer (conversations are added), then Jarvis restarts.")]
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
                                     d => Backend.toast(d.skipped.length ? qsTr("Brought in (held back or left at their defaults here: %1): Jarvis is restarting").arg(d.skipped.join(", "))
                                                        : qsTr("Brought in: Jarvis is restarting"), false),
                                     e => Backend.toast(e.error, true))
            }
        }

        // ================================================================ Advanced
        Group {
            tab: "advanced"
            title: qsTr("On other pages")
            description: qsTr("These are set on the page they belong to.")
            Rows {
                Jump { text: qsTr("Models and API keys"); symbol: "cpu"; button: qsTranslate("Main", "Models"); onGo: page.goTo("models")
                       hint: qsTr("Which model does each job (tasks, reading the screen, web search, pictures, the backup voice), the order they're tried in, and your keys") }
                Jump { text: qsTr("Background checks"); symbol: "memory"; button: qsTranslate("Main", "Memory"); onGo: page.goTo("memory")
                       hint: qsTr("What Jarvis keeps an eye on for you (\"tell me if a payment fails\"), how often it looks, and which checks are paused") }
                Jump { text: qsTr("What Jarvis may do in each account"); symbol: "accounts"; button: qsTranslate("Main", "Accounts"); onGo: page.goTo("accounts")
                       hint: qsTr("Ask first, go ahead, read only or paused, for each account you connected") }
                Jump { text: qsTr("Tools from other apps"); symbol: "plugins"; button: qsTranslate("Main", "Plugins"); onGo: page.goTo("plugins")
                       hint: qsTr("The plugins (MCP servers) Jarvis can use: add one, or switch one on or off") }
            }
        }

        Group {
            tab: "advanced"
            title: qsTr("About Jarvis")
            Block {  // the version, and updates
                words: [qsTr("Check for updates"), qsTr("Update now"), qsTr("Up to date")]
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    Orb { Layout.preferredWidth: 24; Layout.preferredHeight: 24; rings: false }
                    Txt { text: "Jarvis " + Backend.version; weight: 500; wrapMode: Text.NoWrap }
                    Txt { kind: "small"; Layout.fillWidth: true
                          color: page.step && !page.updating ? Theme.red : page.update.available ? Theme.accent : Theme.text3
                          text: page.step ? page.step
                                : page.update.available ? (page.update.how ? qsTr("%1 is out (%2)").arg(page.update.latest).arg(page.update.how)
                                                                           : qsTr("%1 is out").arg(page.update.latest))
                                : page.update.latest ? qsTr("Up to date") : "" }
                    Pill { text: page.updating ? qsTr("Updating…") : page.update.can_update ? qsTr("Update now") : qsTr("Check for updates")
                           kind: page.update.can_update ? "primary" : ""; enabled: !page.updating
                           onClicked: page.update.can_update ? page.installUpdate() : page.checkUpdate() }
                }
            }
            Rows {
                Jump { text: qsTr("First-run setup"); button: qsTr("Run the setup again"); onGo: page.setupAgain()
                       hint: qsTr("Your Gemini key, microphone, Jarvis's voice and how careful it should be, one step at a time") }
            }
        }
    }

    // ---- the pieces
    component PageTab: AbstractButton {  // one tab; while searching, how many of its settings match
        id: pt
        required property var modelData
        required property int index
        readonly property bool current: page.tab === modelData.key
        objectName: "tab-" + modelData.key
        readonly property bool lit: current && !page.searching
        readonly property int hits: page.searching ? page.hitsIn(modelData.key) : 0
        readonly property real full: label.implicitWidth + 28 + 16 + row.spacing  // (its width with its icon)
        text: modelData.label
        implicitHeight: 36
        implicitWidth: row.implicitWidth + 28
        hoverEnabled: true
        focusPolicy: Qt.NoFocus  // (the bar takes Tab for it)
        focus: current
        Accessible.role: Accessible.PageTab
        Accessible.name: text
        Accessible.checkable: true
        Accessible.checked: lit
        Keys.onReturnPressed: click()
        Keys.onEnterPressed: click()
        Keys.onLeftPressed: page.nextTab(mirrored ? 1 : -1)
        Keys.onRightPressed: page.nextTab(mirrored ? -1 : 1)
        onClicked: page.pick(modelData.key)
        opacity: page.searching && !hits ? 0.5 : 1
        Behavior on opacity { NumberAnimation { duration: Theme.fast } }
        background: Rectangle {
            radius: 10
            color: pt.lit ? Theme.accentSoft : pt.hovered ? Theme.glassHover : "transparent"
            Behavior on color { ColorAnimation { duration: Theme.fast } }
            Focus { keyboard: true; visible: pt.visualFocus }
        }
        contentItem: Item {
            Row {
                id: row
                anchors.centerIn: parent
                spacing: 8
                Icon { visible: page.tabIcons && !page.searching; name: pt.modelData.symbol; size: 16; anchors.verticalCenter: parent.verticalCenter
                       color: pt.lit ? Theme.accent : pt.hovered ? Theme.text : Theme.text3 }
                Rectangle {  // the matches, in the icon's place
                    visible: pt.hits > 0
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.max(18, n.implicitWidth + 10); height: 18; radius: 9
                    color: Theme.accentSoft
                    Text { id: n; anchors.centerIn: parent; text: pt.hits; color: Theme.accent; font.family: Theme.font; font.pixelSize: Theme.px(11)
                           font.weight: 600; font.variableAxes: { "wght": 600 }; font.features: { "tnum": 1 } }
                }
                Text { id: label; text: pt.text; anchors.verticalCenter: parent.verticalCenter
                       font.family: Theme.font; font.pixelSize: Theme.px(14); font.weight: 500; font.variableAxes: { "wght": 500 }
                       color: pt.lit || pt.hovered ? Theme.text : Theme.text2
                       Behavior on color { ColorAnimation { duration: Theme.fast } } }
            }
        }
    }
    component Group: Section {  // a section on one tab; while searching, shown if anything in it matches
        id: g
        property string tab
        readonly property bool whole: page.searching && page.found(title)  // (not its description: "wake" brought up all of Your data)
        readonly property bool hit: page.searching && (whole || page.anyShowing(rows))
        readonly property int hits: hit ? Math.max(1, page.count(rows)) : 0
        visible: page.searching ? hit : page.tab === tab
        Component.onCompleted: page.groups = page.groups.concat([g])
    }
    component Row2: RowLayout {
        id: r2
        readonly property bool showing: page.anyShowing(r2.children)
        visible: showing
        Layout.fillWidth: true
        spacing: 24
        uniformCellSizes: true
    }
    component Rows: ColumnLayout {  // rows with a hairline above each
        id: rs
        readonly property bool showing: page.anyShowing(rs.children)
        visible: showing
        Layout.fillWidth: true
        spacing: 0
    }
    component Setting: ColumnLayout {
        id: st
        property string label
        property string also  // more words it's found by
        property bool applies: true
        readonly property string words: [label, also, page.choices(st)].join(" ")
        readonly property bool showing: page.shows(page.within(st), words) && applies
        visible: showing
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignTop
        spacing: 8
        Txt { kind: "label"; text: st.label; Layout.fillWidth: true }
    }
    component SwitchRow: Toggle {
        id: sw
        property bool applies: true
        readonly property string words: text + " " + hint
        readonly property bool showing: page.shows(page.within(sw), words) && applies
        visible: showing
        Layout.fillWidth: true
        Rectangle { anchors { left: parent.left; right: parent.right; top: parent.top } height: 1; color: Theme.stroke }
    }
    component Jump: ColumnLayout {  // a row that takes you where those settings are
        id: j
        property string text
        property string hint
        property string button
        property string symbol
        signal go()
        readonly property string words: text + " " + hint + " " + button
        readonly property bool showing: page.shows(page.within(j), words)
        visible: showing
        Layout.fillWidth: true
        spacing: 0
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.stroke }
        RowLayout {
            Layout.fillWidth: true
            Layout.minimumHeight: 56
            Layout.topMargin: 8; Layout.bottomMargin: 8
            spacing: 16
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Txt { text: j.text; Layout.fillWidth: true }
                Txt { kind: "small"; text: j.hint; visible: text !== ""; Layout.fillWidth: true }
            }
            Pill { text: j.button; symbol: j.symbol; onClicked: j.go() }
        }
    }
    component Block: ColumnLayout {  // anything else, found by the texts in `words`: shown whole or not at all
        id: b
        property var words: []
        property bool applies: true
        readonly property bool whole: page.shows(page.within(b), words.join(" "))
        readonly property bool showing: whole && applies
        visible: showing
        Layout.fillWidth: true
        spacing: 16
    }
    component Note: Txt {
        id: nt
        readonly property string words: text
        readonly property bool showing: page.shows(page.within(nt), words)
        visible: showing
        kind: "small"
        Layout.fillWidth: true
    }
    component Line: Rectangle {  // a hairline, kept with what it separates
        id: line
        Layout.fillWidth: true
        Layout.preferredHeight: 1
        color: Theme.stroke
        visible: { const home = page.within(line); return !page.searching || !home || home.whole }
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
        readonly property string words: label + " " + hint
        readonly property bool showing: page.shows(page.within(sl), words)
        visible: showing
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
