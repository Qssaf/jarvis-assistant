import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Shapes
import Jarvis

// The first run: what Jarvis does and what leaves the PC, a Gemini key, a microphone check, a voice, how careful to be,
// then a first wake word ("Hey Jarvis", or the one picked in Settings). Every step can be skipped; it doesn't come back once finished.
Rectangle {
    id: wiz
    signal finished(string goTo)
    property int step: 0
    readonly property int steps: 6
    readonly property bool last: step === steps - 1
    readonly property var names: ["Welcome", "Gemini key", "Microphone", "Voice", "Safety", "Ready"]
    property var s: ({})
    property var voices: []
    property string wake: "Hey Jarvis"
    property bool keyOk: false
    property string keyDetail: ""
    // (no key saved at all is the normal first visit, not an error: brain.api_key's message, or empty)
    readonly property bool keyMissing: !keyOk && (!keyDetail || /AI Studio key|^no key/i.test(keyDetail))
    property bool checking: false
    readonly property real mic: Math.min(1, Backend.micLevel * 4)
    readonly property bool hearing: Backend.micLevel > 0.02
    readonly property bool compact: height < 760
    readonly property int panel: 16  // (one radius for every panel inside the card; fields keep radiusControl)
    gradient: Gradient {  // (opaque: the page showing through only muddies it)
        GradientStop { position: 0; color: Theme.bgTop }
        GradientStop { position: 1; color: Theme.bgBottom }
    }
    radius: Window.window && Window.window.visibility === Window.Maximized ? 0 : Theme.radiusWindow

    function load() {
        Api.get("/api/settings", d => { s = d.settings; voices = d.voices; wake = d.wake_phrase })
        checkKey()
    }
    function checkKey() {
        checking = true
        Api.get("/api/setup/key", d => { keyOk = d.ok; keyDetail = d.detail; checking = false },
                e => { keyOk = false; keyDetail = e.error; checking = false })
    }
    function saveKey(text) {
        if (!text.trim()) return
        checking = true
        Api.post("/api/keys/aistudio", { key: text.trim() }, () => checkKey(), e => { checking = false; keyDetail = e.error })
    }
    function set(key, value) {
        const change = {}
        change[key] = value
        Api.post("/api/settings", change, d => s = d.settings, e => Backend.toast(e.error, true))
    }
    function finish(goTo) {
        set("setup_done", true)
        finished(goTo)
    }
    Component.onCompleted: load()
    onStepChanged: stepIn.restart()

    MouseArea { anchors.fill: parent }  // (nothing behind it takes clicks)

    // light behind the reactor, and a warm hint behind the card
    Glow { x: intro.x + intro.width / 2 - width / 2; y: intro.y + 40 + orb.height / 2 - height / 2; size: 760; tint: orb.tint; strength: 0.13 }
    Glow { x: card.x + card.width - width / 2; y: card.y + card.height - height / 2; size: 520; tint: Theme.warm; strength: 0.05 }

    readonly property int introWidth: Math.min(300, width * 0.3)
    readonly property int gutter: width > 1100 ? 72 : 40

    // the reactor and the steps
    Item {
        id: intro
        width: wiz.introWidth
        height: col.implicitHeight
        x: (wiz.width - width - wiz.gutter - card.width) / 2
        anchors.verticalCenter: parent.verticalCenter
        ColumnLayout {
            id: col
            width: parent.width
            spacing: 0
            Orb {
                id: orb
                Layout.preferredWidth: Math.min(196, wiz.height * 0.25)
                Layout.preferredHeight: Layout.preferredWidth
                Layout.bottomMargin: 20
                Layout.leftMargin: -width * 0.08  // (lines the outer ring up with the text)
                mode: wiz.step === 2 && wiz.hearing ? "listening" : "idle"
                level: wiz.step === 2 ? wiz.mic : 0
            }
            Txt { kind: "label"; text: "Setting up Jarvis"; color: Theme.text3; Layout.bottomMargin: 6 }
            Txt { kind: "heading"; text: "Let’s get you ready"; Layout.fillWidth: true; Layout.bottomMargin: 24 }
            Repeater {
                model: wiz.steps
                StepRow { required property int index; n: index }
            }
        }
    }

    // the step itself
    Glass {
        id: card
        floating: true
        radius: 28
        width: Math.min(560, wiz.width - 2 * Theme.margin - wiz.introWidth - wiz.gutter)
        height: body.implicitHeight + 2 * body.anchors.margins
        x: intro.x + intro.width + wiz.gutter
        anchors.verticalCenter: parent.verticalCenter
        Behavior on height { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }

        ColumnLayout {
            id: body
            anchors { fill: parent; margins: wiz.compact ? 28 : 36 }
            spacing: 0

            StackLayout {
                id: stack
                Layout.fillWidth: true
                Layout.preferredHeight: children[wiz.step].implicitHeight  // (the card fits the step: no empty glass under short ones)
                currentIndex: wiz.step
                opacity: 0
                transform: Translate { id: rise }
                ParallelAnimation {
                    id: stepIn
                    running: true
                    NumberAnimation { target: stack; property: "opacity"; from: 0; to: 1; duration: 220; easing.type: Easing.OutCubic }
                    NumberAnimation { target: rise; property: "y"; from: 8; to: 0; duration: 220; easing.type: Easing.OutCubic }
                }

                Step {
                    symbol: "sparkle"
                    title: "Hi, I’m Jarvis"
                    lead: `Say “${wiz.wake}” and ask for anything: questions, what’s on your screen, your apps, email, calendar, `
                          + "Classroom, reminders. A couple of minutes of setup and you’re ready."
                    Inset {
                        symbol: "shield"
                        title: "What leaves this PC"
                        detail: `What you say after “${wiz.wake}”, and screenshots when a task needs the screen, go to Google `
                                + "Gemini. Account actions go through Composio, only for the accounts you connect. Memory, "
                                + "reminders and conversations stay on this computer."
                    }
                }

                Step {
                    symbol: "key"
                    title: "Your Gemini key"
                    lead: "Jarvis thinks with Google Gemini. A free key takes a minute: sign in at "
                          + "<a href=\"https://aistudio.google.com/apikey\">aistudio.google.com/apikey</a>, press Create API key, "
                          + "and paste it here. It’s kept in your system keychain."
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        Field { id: keyField; Layout.fillWidth: true; echoMode: TextInput.Password
                                placeholderText: wiz.keyOk ? "Key saved · paste a new one to replace it" : "Paste your API key"
                                onAccepted: { wiz.saveKey(text); text = "" } }
                        Pill { text: "Save"; implicitHeight: 44; enabled: keyField.text.trim() !== "" && !wiz.checking
                               kind: enabled ? "primary" : ""  // (a dimmed solid cyan reads as broken)
                               onClicked: { wiz.saveKey(keyField.text); keyField.text = "" } }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        Icon { visible: !wiz.keyMissing; name: wiz.checking ? "refresh" : wiz.keyOk ? "check" : "alert"; size: 16
                               Layout.preferredWidth: 16; Layout.preferredHeight: 16; color: keyNote.color }
                        Txt { id: keyNote; kind: "small"; Layout.fillWidth: true
                              color: wiz.checking ? Theme.text2 : wiz.keyOk ? Theme.green : wiz.keyMissing ? Theme.text3 : Theme.red
                              text: wiz.checking ? "Checking the key…" : wiz.keyOk ? "The key works: " + wiz.keyDetail
                                    : wiz.keyMissing ? "No key yet" : "That key didn’t work: " + wiz.keyDetail }
                    }
                }

                Step {
                    symbol: "mic"
                    title: "Your microphone"
                    lead: "Say something: the bars should jump while you talk."
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: meter.implicitHeight + 32
                        radius: wiz.panel
                        color: Theme.glass
                        border.width: 1
                        border.color: Theme.stroke
                        ColumnLayout {
                            id: meter
                            anchors { fill: parent; margins: 16 }
                            spacing: 14
                            Row {
                                id: bars
                                Layout.fillWidth: true
                                readonly property int n: 36
                                spacing: 7
                                height: 36
                                Repeater {
                                    model: bars.n
                                    Rectangle {
                                        required property int index
                                        readonly property bool lit: wiz.mic * bars.n > index
                                        width: (bars.width - bars.spacing * (bars.n - 1)) / bars.n
                                        height: 8 + 28 * Math.pow(Math.sin(Math.PI * (index + 0.5) / bars.n), 0.6)
                                        anchors.verticalCenter: parent.verticalCenter
                                        radius: width / 2
                                        color: lit ? Theme.accent : Theme.alpha(Theme.text3, 0.35)
                                        Behavior on color { ColorAnimation { duration: 80 } }
                                    }
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                StatusDot { status: wiz.hearing ? "ok" : ""; Layout.alignment: Qt.AlignTop; Layout.topMargin: 6 }  // (on the first line)
                                Txt { kind: "small"; Layout.fillWidth: true; color: wiz.hearing ? Theme.text : Theme.text2
                                      text: wiz.hearing ? "I can hear you."
                                            : "Quiet so far. If the bars never move, pick the right input device in your system’s sound settings." }
                            }
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: 6
                        spacing: 6
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { text: "Wake word sensitivity"; weight: 500; Layout.fillWidth: true }
                            Txt { kind: "small"; text: Number(wakeSlider.value).toFixed(2); font.features: { "tnum": 1 } }
                        }
                        Range {
                            id: wakeSlider
                            Layout.fillWidth: true
                            leftPadding: 0; rightPadding: 0  // (the track lines up with the text)
                            from: 0.2; to: 0.9; stepSize: 0.05; snapMode: Slider.SnapAlways
                            value: wiz.s.wake_threshold !== undefined ? wiz.s.wake_threshold : 0.5
                            onPressedChanged: if (!pressed) wiz.set("wake_threshold", Number(value.toFixed(2)))
                        }
                        Txt { kind: "small"; color: Theme.text3; text: "Lower wakes more easily." }
                    }
                }

                Step {
                    symbol: "volume"
                    title: "My voice"
                    lead: "How I sound, and when I talk."
                    Select { Layout.fillWidth: true; model: wiz.voices.map(v => ({ value: v, label: v })); value: wiz.s.voice || ""
                             onPicked: v => wiz.set("voice", v) }
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: toggles.implicitHeight
                        radius: wiz.panel
                        color: Theme.glass
                        border.width: 1
                        border.color: Theme.stroke
                        ColumnLayout {
                            id: toggles
                            width: parent.width
                            spacing: 0
                            Toggle { Layout.fillWidth: true; Layout.preferredHeight: 54; Layout.leftMargin: 16; Layout.rightMargin: 16
                                     text: "Speak replies to typed messages"; checked: !!wiz.s.speak_typed_replies
                                     onToggled: wiz.set("speak_typed_replies", checked) }
                            Rectangle { Layout.fillWidth: true; Layout.leftMargin: 16; implicitHeight: 1; color: Theme.stroke }
                            Toggle { Layout.fillWidth: true; Layout.preferredHeight: 54; Layout.leftMargin: 16; Layout.rightMargin: 16
                                     text: "Start Jarvis when I log in"; checked: !!wiz.s.start_at_login
                                     onToggled: wiz.set("start_at_login", checked) }
                        }
                    }
                }

                Step {
                    symbol: "shield"
                    title: "How careful should I be?"
                    lead: "You can change this any time in Settings."
                    Choice { title: "Ask first"; tag: "Recommended"; picked: wiz.s.safety !== "full"; onChosen: wiz.set("safety", "ask")
                             detail: "Commands that delete, install or shut down, and changes to your accounts (sending email, "
                                     + "creating events), wait for your yes, unless you asked for exactly that." }
                    Choice { title: "Just do it"; picked: wiz.s.safety === "full"; onChosen: wiz.set("safety", "full")
                             detail: "Jarvis acts without checking first. Quicker, for when you trust it with your PC and accounts." }
                }

                Step {
                    symbol: "check"
                    title: "You’re set"
                    lead: "Connect Gmail, Calendar, Classroom, Drive and more on the Accounts page so Jarvis can use them. If "
                          + "something doesn’t work, the Health page says what and how to fix it."
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 76
                        radius: wiz.panel
                        color: Theme.glass
                        border.width: 1
                        border.color: Theme.stroke
                        RowLayout {
                            anchors { fill: parent; leftMargin: 16; rightMargin: 16 }
                            spacing: 14
                            Rectangle {  // (an icon well, not a button: saying it is the way in)
                                implicitWidth: 40; implicitHeight: 40; radius: 20
                                color: Theme.accentSoft
                                Icon { anchors.centerIn: parent; name: "mic"; size: 18; color: Theme.accent }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Txt { kind: "label"; text: "Try it now"; color: Theme.accent }
                                Txt { kind: "heading"; text: `“${wiz.wake}, what’s the weather?”`; Layout.fillWidth: true }
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: wiz.compact ? 24 : 32
                spacing: 10
                Pill { visible: !wiz.last; kind: "ghost"; text: "Skip setup"; Layout.leftMargin: -12  // (the label on the content edge)
                       onClicked: wiz.finish("") }
                Item { Layout.fillWidth: true }
                Pill { visible: wiz.step > 0 && !wiz.last; text: "Back"; onClicked: wiz.step-- }
                Pill { visible: wiz.last; kind: "ghost"; text: "Done"; onClicked: wiz.finish("") }
                Pill { readonly property bool skipKey: wiz.step === 1 && !wiz.keyOk
                       kind: skipKey ? "" : "primary"; Layout.minimumWidth: 96
                       text: wiz.last ? "Connect accounts" : skipKey ? "Skip for now" : "Next"
                       onClicked: wiz.last ? wiz.finish("accounts") : wiz.step++ }
            }
        }
    }

    component Glow: Shape {
        property int size
        property color tint
        property real strength
        width: size; height: size
        ShapePath {
            strokeWidth: -1
            fillGradient: RadialGradient {
                centerX: size / 2; centerY: size / 2; focalX: centerX; focalY: centerY; centerRadius: size / 2
                GradientStop { position: 0; color: Theme.alpha(tint, strength) }
                GradientStop { position: 0.45; color: Theme.alpha(tint, strength * 0.35) }
                GradientStop { position: 1; color: Theme.alpha(tint, 0) }
            }
            PathAngleArc { centerX: size / 2; centerY: size / 2; radiusX: size / 2; radiusY: size / 2; sweepAngle: 360 }
        }
    }
    component StepRow: Item {
        id: sr
        property int n
        readonly property bool done: n < wiz.step
        readonly property bool current: n === wiz.step
        Layout.fillWidth: true
        implicitHeight: 40
        Rectangle {  // the line down to the next step
            visible: sr.n < wiz.steps - 1
            x: 13; y: 32; width: 2; height: 16; radius: 1
            color: sr.done ? Theme.alpha(Theme.accent, 0.45) : Theme.stroke
            Behavior on color { ColorAnimation { duration: 220 } }
        }
        Rectangle {
            id: dot
            width: 28; height: 28; radius: 14
            anchors.verticalCenter: parent.verticalCenter
            color: sr.done ? Theme.accentSoft : "transparent"  // (soft: solid discs would outshine the reactor)
            border.width: sr.done ? 0 : 1.5
            border.color: sr.current ? Theme.accent : Theme.strokeStrong
            Behavior on color { ColorAnimation { duration: 220 } }
            Icon { visible: sr.done; anchors.centerIn: parent; name: "check"; size: 15; color: Theme.accent }
            Text {
                visible: !sr.done
                anchors.centerIn: parent
                text: sr.n + 1
                font.family: Theme.font; font.pixelSize: Theme.px(12); font.weight: 600; font.variableAxes: { "wght": 600 }
                font.features: { "tnum": 1 }
                color: sr.current ? Theme.accent : Theme.text3
            }
        }
        Txt {
            anchors { left: dot.right; leftMargin: 14; right: parent.right; verticalCenter: parent.verticalCenter }
            text: wiz.names[sr.n]
            weight: sr.current ? 600 : 400
            color: sr.current ? Theme.text : sr.done ? Theme.text2 : Theme.text3
            elide: Text.ElideRight
            wrapMode: Text.NoWrap
        }
    }
    component Step: ColumnLayout {
        id: st
        property string symbol
        property string title
        property string lead
        Layout.fillWidth: true
        spacing: wiz.compact ? 12 : 16
        Rectangle {
            visible: !wiz.compact
            implicitWidth: 44; implicitHeight: 44; radius: 22
            color: Theme.accentSoft
            border.width: 1
            border.color: Theme.alpha(Theme.accent, 0.25)
            Icon { anchors.centerIn: parent; name: st.symbol; size: 20; color: Theme.accent }
        }
        Txt { kind: "title"; text: st.title; Layout.fillWidth: true; Layout.topMargin: wiz.compact ? 0 : 4 }
        Txt { Layout.fillWidth: true; Layout.bottomMargin: 8; text: st.lead; color: Theme.text2; lineHeight: 1.45
              font.pixelSize: Theme.px(15); textFormat: Text.StyledText }
    }
    component Inset: Rectangle {
        id: ins
        property string symbol
        property string title
        property string detail
        Layout.fillWidth: true
        implicitHeight: insRow.implicitHeight + 32
        radius: wiz.panel
        color: Theme.glass
        border.width: 1
        border.color: Theme.stroke
        RowLayout {
            id: insRow
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
            spacing: 14
            Icon { Layout.alignment: Qt.AlignTop; Layout.preferredWidth: 20; Layout.preferredHeight: 20; name: ins.symbol; size: 20; color: Theme.text2 }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Txt { text: ins.title; weight: 600 }
                Txt { kind: "small"; text: ins.detail; Layout.fillWidth: true; lineHeight: 1.4 }
            }
        }
    }
    component Choice: AbstractButton {
        id: ch
        property string title
        property string tag
        property string detail
        property bool picked
        signal chosen()
        Layout.fillWidth: true
        implicitHeight: chCol.implicitHeight + 32
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        onClicked: chosen()
        background: Rectangle {
            radius: wiz.panel
            color: ch.picked ? Theme.accentSoft : ch.hovered ? Theme.glassHover : Theme.glass
            border.width: 1
            border.color: ch.picked ? Theme.alpha(Theme.accent, 0.5) : Theme.stroke
            Behavior on color { ColorAnimation { duration: Theme.fast } }
        }
        contentItem: Item {
            Rectangle {  // the radio
                id: radio
                x: 16; y: 16
                width: 20; height: 20; radius: 10
                color: "transparent"
                border.width: ch.picked ? 2 : 1.5
                border.color: ch.picked ? Theme.accent : Theme.strokeStrong
                Rectangle { anchors.centerIn: parent; width: 10; height: 10; radius: 5; color: Theme.accent; visible: ch.picked }
            }
            ColumnLayout {
                id: chCol
                anchors { left: radio.right; leftMargin: 14; right: parent.right; rightMargin: 16; top: parent.top; topMargin: 16 }
                spacing: 4
                RowLayout {
                    spacing: 8
                    Txt { text: ch.title; weight: 600 }
                    Rectangle {
                        visible: ch.tag !== ""
                        implicitWidth: tagText.implicitWidth + 20; implicitHeight: 22; radius: 11
                        color: Theme.accentSoft
                        Txt { id: tagText; anchors.centerIn: parent; kind: "label"; text: ch.tag; color: Theme.accent }
                    }
                }
                Txt { kind: "small"; text: ch.detail; Layout.fillWidth: true; lineHeight: 1.4 }
            }
        }
    }
}
