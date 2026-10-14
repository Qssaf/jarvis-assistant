import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Jarvis

// Settings save themselves as you change them.
ScrollPage {
    id: page
    title: "Settings"
    hint: "Changes are saved at once. Voice changes apply from the next conversation."
    property var s: ({})
    property var voices: []
    property var avail: ({ backends: [], live: [] })  // for the voice models (asked for separately: it's slower)
    property bool looking: false

    function load() {
        Api.get("/api/settings", d => { s = d.settings; voices = d.voices })
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
    Component.onCompleted: load()

    Section {
        title: "Voice"
        Row2 {
            Setting { label: "Jarvis's voice"
                Select { Layout.fillWidth: true; model: page.voices.map(v => ({ value: v, label: v })); value: page.s.voice || ""; onPicked: v => page.set("voice", v) } }
            Setting { label: "Voice model"
                Select { Layout.fillWidth: true; visible: page.avail.live.length > 0; model: page.options(page.avail.live, page.s.live_model)
                         value: page.s.live_model || ""; onPicked: v => page.set("live_model", v) }
                Field { Layout.fillWidth: true; visible: !page.avail.live.length; text: page.s.live_model || ""
                        onEditingFinished: if (text !== page.s.live_model) page.set("live_model", text) } }
        }
        Toggle { Layout.fillWidth: true; text: "Fast voice"; hint: "Answer without thinking first: about 0.3 s quicker, a little less sharp"
                 checked: !!page.s.fast_voice; onToggled: page.set("fast_voice", checked) }
        Toggle { Layout.fillWidth: true; text: "Speak replies to typed messages"; checked: !!page.s.speak_typed_replies
                 onToggled: page.set("speak_typed_replies", checked) }
    }

    Section {
        title: "Listening"
        Row2 {
            Slide { label: "Pause before Jarvis answers"; key: "end_of_speech_ms"; from: 200; to: 2000; step: 50; unit: " ms"
                    hint: "Lower is snappier; higher cuts you off less" }
            Slide { label: "Wake word sensitivity"; key: "wake_threshold"; from: 0.05; to: 0.95; step: 0.05; unit: ""; decimals: 2
                    hint: "Lower wakes more easily" }
        }
        Row2 {
            Slide { label: "Keep listening after a reply"; key: "follow_up_seconds"; from: 0; to: 60; step: 1; unit: " s" }
            Slide { label: "Stay connected after a conversation"; key: "keep_session_seconds"; from: 0; to: 600; step: 30; unit: " s"
                    hint: "Makes the next wake-up instant" }
        }
        Toggle { Layout.fillWidth: true; text: "Learn my voice"; hint: "Wake-ups you dismiss teach Jarvis what isn't you"
                 checked: !!page.s.learn_my_voice; onToggled: page.set("learn_my_voice", checked) }
        Toggle { Layout.fillWidth: true; text: "Echo cancelling"; hint: "Talk over Jarvis on speakers (PipeWire; restart Jarvis to apply)"
                 checked: !!page.s.echo_cancel; onToggled: page.set("echo_cancel", checked) }
    }

    Section {
        title: "Your day"
        Setting { label: "Home city, for the weather (empty: guess from your network)"
            Field { Layout.fillWidth: true; text: page.s.home_city || ""; placeholderText: "e.g. London"
                    onEditingFinished: if (text !== page.s.home_city) page.set("home_city", text) } }
        Toggle { Layout.fillWidth: true; text: "Morning briefing"; hint: "The first time Jarvis starts in a morning, it tells you about your day"
                 checked: !!page.s.morning_briefing; onToggled: page.set("morning_briefing", checked) }
        Toggle { Layout.fillWidth: true; text: "Classroom deadlines"; hint: "Reminders a day and two hours before work is due (skipped once you've turned it in)"
                 checked: !!page.s.deadline_reminders; onToggled: page.set("deadline_reminders", checked) }
    }

    Section {
        title: "Jarvis"
        Toggle { Layout.fillWidth: true; text: "Show Jarvis's thinking in the chat"; checked: !!page.s.show_thinking
                 onToggled: page.set("show_thinking", checked) }
        Toggle { Layout.fillWidth: true; text: "Start Jarvis when I log in"; checked: !!page.s.start_at_login
                 onToggled: page.set("start_at_login", checked) }
        Setting { label: "Your instructions for Jarvis (how to behave, things to know about you)"
            Area { text: page.s.extra_instructions || ""; onDone: v => page.set("extra_instructions", v) } }
        Txt { kind: "small"; Layout.fillWidth: true; text: "Models for everything else, and your API keys, are on the Models page." }
        Txt { kind: "small"; Layout.fillWidth: true
              text: "Push to talk: bind the command  jarvis --listen  to a keyboard shortcut (KDE: System Settings → Keyboard → Shortcuts → Add New → Command)." }
    }

    Txt { kind: "small"; text: "Jarvis " + Backend.version; Layout.topMargin: 6 }
    Item { Layout.preferredHeight: 24 }

    component Section: Card {
        property string title
        default property alias body: col.data
        Layout.fillWidth: true
        padding: 22
        ColumnLayout {
            id: col
            width: parent.width
            spacing: 16
            Txt { kind: "heading"; text: title }
        }
    }
    component Row2: RowLayout {
        Layout.fillWidth: true
        spacing: 18
        uniformCellSizes: true
    }
    component Setting: ColumnLayout {
        property string label
        Layout.fillWidth: true
        spacing: 6
        Txt { kind: "small"; text: label; Layout.fillWidth: true }
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
        spacing: 4
        RowLayout {
            Layout.fillWidth: true
            Txt { text: sl.label; Layout.fillWidth: true; font.pixelSize: 13 }
            Txt { text: slider.value.toFixed(sl.decimals) + sl.unit; font.family: Theme.mono; font.pixelSize: 12; color: Theme.accent }
        }
        Slider {
            id: slider
            Layout.fillWidth: true
            snapMode: Slider.SnapAlways
            value: page.s[sl.key] !== undefined ? page.s[sl.key] : from
            onPressedChanged: if (!pressed) page.set(sl.key, Number(value.toFixed(sl.decimals)))
            background: Rectangle {
                x: slider.leftPadding; y: slider.topPadding + slider.availableHeight / 2 - 2
                width: slider.availableWidth; height: 4; radius: 2; color: Theme.raised
                Rectangle { width: slider.visualPosition * parent.width; height: 4; radius: 2; color: Theme.accent }
            }
            handle: Rectangle {
                x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width)
                y: slider.topPadding + slider.availableHeight / 2 - 8
                width: 16; height: 16; radius: 8
                color: slider.pressed ? Theme.text : Theme.accent
                border.width: 3; border.color: Theme.card
            }
        }
        Txt { kind: "small"; text: sl.hint; visible: sl.hint !== ""; Layout.fillWidth: true }
    }
    component Area: Rectangle {
        id: area
        property alias text: edit.text
        property bool mono: false
        signal done(string value)
        Layout.fillWidth: true
        implicitHeight: Math.max(96, edit.implicitHeight + 4)
        radius: Theme.radiusSmall
        color: Theme.bg
        border.width: 1
        border.color: edit.activeFocus ? Theme.accent : Theme.lineStrong
        TextArea {
            id: edit
            anchors.fill: parent
            color: Theme.text
            font.family: area.mono ? Theme.mono : Theme.font
            font.pixelSize: area.mono ? 12 : 14
            wrapMode: TextEdit.Wrap
            selectionColor: Theme.alpha(Theme.accent, 0.45)
            background: null
            padding: 12
            onActiveFocusChanged: if (!activeFocus) area.done(text)
        }
    }
}
