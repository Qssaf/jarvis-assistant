import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Jarvis

// The first run: what Jarvis does and what leaves the PC, a Gemini key, a microphone check, a voice, how careful to be,
// then a first "Hey Jarvis". Every step can be skipped; it doesn't come back once finished.
Rectangle {
    id: wiz
    signal finished(string goTo)
    property int step: 0
    readonly property int steps: 6
    property var s: ({})
    property var voices: []
    property bool keyOk: false
    property string keyDetail: ""
    property bool checking: false
    color: Theme.alpha(Theme.bg, 0.94)

    function load() {
        Api.get("/api/settings", d => { s = d.settings; voices = d.voices })
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

    MouseArea { anchors.fill: parent }  // (nothing behind it takes clicks)

    Card {
        anchors.centerIn: parent
        width: Math.min(parent.width - 80, 640)
        padding: 32
        ColumnLayout {
            width: parent.width
            spacing: 18

            RowLayout {
                Layout.fillWidth: true
                Txt { kind: "caps"; text: `Setup · ${wiz.step + 1} of ${wiz.steps}`; Layout.fillWidth: true }
                Repeater {
                    model: wiz.steps
                    Rectangle { required property int index; width: 22; height: 4; radius: 2
                                color: index <= wiz.step ? Theme.accent : Theme.raised }
                }
            }

            StackLayout {
                Layout.fillWidth: true
                currentIndex: wiz.step

                Step {
                    Txt { kind: "title"; text: "Hi, I'm Jarvis" }
                    Txt { Layout.fillWidth: true
                          text: "Say \"Hey Jarvis\" and ask for anything: questions, what's on your screen, your apps, email, calendar, "
                                + "Classroom, reminders. A couple of minutes of setup and you're ready." }
                    Txt { kind: "small"; Layout.fillWidth: true
                          text: "What leaves this PC: what you say after \"Hey Jarvis\", and screenshots when a task needs the screen, go "
                                + "to Google Gemini. Account actions go through Composio, only for the accounts you connect. Memory, "
                                + "reminders and conversations stay on this computer." }
                }

                Step {
                    Txt { kind: "title"; text: "Your Gemini key" }
                    Txt { Layout.fillWidth: true; textFormat: Text.StyledText
                          text: "Jarvis thinks with Google Gemini. A free key takes a minute: sign in at "
                                + "<a href=\"https://aistudio.google.com/apikey\">aistudio.google.com/apikey</a>, press Create API key, "
                                + "and paste it here. It's kept in your system keychain." }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        Field { id: keyField; Layout.fillWidth: true; echoMode: TextInput.Password
                                placeholderText: wiz.keyOk ? "Key saved · paste a new one to replace it" : "Paste your API key"
                                onAccepted: { wiz.saveKey(text); text = "" } }
                        Pill { text: "Save"; kind: "primary"; enabled: keyField.text.trim() !== "" && !wiz.checking
                               onClicked: { wiz.saveKey(keyField.text); keyField.text = "" } }
                    }
                    Txt { kind: "small"; Layout.fillWidth: true
                          color: wiz.checking ? Theme.dim : wiz.keyOk ? Theme.green : Theme.warm
                          text: wiz.checking ? "Checking the key…" : wiz.keyOk ? "The key works: " + wiz.keyDetail
                                : wiz.keyDetail ? "Not working yet: " + wiz.keyDetail : "No key yet." }
                }

                Step {
                    Txt { kind: "title"; text: "Your microphone" }
                    Txt { Layout.fillWidth: true; text: "Say something: the bar should jump while you talk." }
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 12
                        radius: 6
                        color: Theme.raised
                        Rectangle {
                            height: parent.height; radius: 6
                            width: parent.width * Math.min(1, Backend.micLevel * 4)
                            color: Backend.micLevel > 0.02 ? Theme.accent : Theme.faint
                            Behavior on width { NumberAnimation { duration: 80 } }
                        }
                    }
                    Txt { kind: "small"; Layout.fillWidth: true
                          text: Backend.micLevel > 0.02 ? "I can hear you."
                                : "Quiet so far. If the bar never moves, pick the right input device in your system's sound settings." }
                    Txt { kind: "small"; Layout.fillWidth: true
                          text: "Wake word sensitivity (lower wakes more easily): " + Number(wakeSlider.value).toFixed(2) }
                    Slider {
                        id: wakeSlider
                        Layout.fillWidth: true
                        from: 0.2; to: 0.9; stepSize: 0.05; snapMode: Slider.SnapAlways
                        value: wiz.s.wake_threshold !== undefined ? wiz.s.wake_threshold : 0.5
                        onPressedChanged: if (!pressed) wiz.set("wake_threshold", Number(value.toFixed(2)))
                    }
                }

                Step {
                    Txt { kind: "title"; text: "My voice" }
                    Select { Layout.fillWidth: true; model: wiz.voices.map(v => ({ value: v, label: v })); value: wiz.s.voice || ""
                             onPicked: v => wiz.set("voice", v) }
                    Toggle { Layout.fillWidth: true; text: "Speak replies to typed messages"; checked: !!wiz.s.speak_typed_replies
                             onToggled: wiz.set("speak_typed_replies", checked) }
                    Toggle { Layout.fillWidth: true; text: "Start Jarvis when I log in"; checked: !!wiz.s.start_at_login
                             onToggled: wiz.set("start_at_login", checked) }
                }

                Step {
                    Txt { kind: "title"; text: "How careful should I be?" }
                    Choice { title: "Ask first (recommended)"; picked: wiz.s.safety !== "full"; onChosen: wiz.set("safety", "ask")
                             detail: "Commands that delete, install or shut down, and changes to your accounts (sending email, "
                                     + "creating events), wait for your yes, unless you asked for exactly that." }
                    Choice { title: "Just do it"; picked: wiz.s.safety === "full"; onChosen: wiz.set("safety", "full")
                             detail: "Jarvis acts without checking first. Quicker, for when you trust it with your PC and accounts." }
                    Txt { kind: "small"; Layout.fillWidth: true; text: "You can change this any time in Settings." }
                }

                Step {
                    Txt { kind: "title"; text: "You're set" }
                    Txt { Layout.fillWidth: true; text: "Try it now: say \"Hey Jarvis, what's the weather?\"" }
                    Txt { kind: "small"; Layout.fillWidth: true
                          text: "Connect Gmail, Calendar, Classroom, Drive and more on the Accounts page so Jarvis can use them. If "
                                + "something doesn't work, the Health page says what and how to fix it." }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Pill { visible: wiz.step < wiz.steps - 1; text: "Skip setup"; onClicked: wiz.finish("") }
                Item { Layout.fillWidth: true }
                Pill { visible: wiz.step > 0; text: "Back"; onClicked: wiz.step-- }
                Pill { visible: wiz.step === wiz.steps - 1; text: "Connect accounts"; onClicked: wiz.finish("accounts") }
                Pill { kind: "primary"; text: wiz.step === wiz.steps - 1 ? "Done" : wiz.step === 1 && !wiz.keyOk ? "Later" : "Next"
                       onClicked: wiz.step === wiz.steps - 1 ? wiz.finish("") : wiz.step++ }
            }
        }
    }

    component Step: ColumnLayout {
        Layout.fillWidth: true
        spacing: 14
    }
    component Choice: AbstractButton {
        id: ch
        property string title
        property string detail
        property bool picked
        signal chosen()
        Layout.fillWidth: true
        implicitHeight: col.implicitHeight + 28
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        onClicked: chosen()
        background: Rectangle {
            radius: Theme.radiusSmall
            color: ch.picked ? Theme.alpha(Theme.accent, 0.12) : ch.hovered ? Theme.cardHover : "transparent"
            border.width: 1
            border.color: ch.picked ? Theme.accent : Theme.lineStrong
        }
        contentItem: Item {
            ColumnLayout {
                id: col
                anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 16 }
                spacing: 4
                Txt { text: ch.title; font.weight: Font.DemiBold }
                Txt { kind: "small"; text: ch.detail; Layout.fillWidth: true }
            }
        }
    }
}
