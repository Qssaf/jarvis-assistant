import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Jarvis

// What Jarvis remembers about you (edit it freely), and your reminders.
ScrollPage {
    id: page
    title: "Memory"
    hint: "Jarvis reads this before every conversation. Tell it “remember…” or edit it here."
    property var reminders: []
    property var routines: []
    property string saved: ""

    function load() {
        Api.get("/api/memory", d => { notes.text = d.memory; saved = d.memory })
        Api.get("/api/reminders", d => reminders = d)
        Api.get("/api/routines", d => routines = d)
    }
    Component.onCompleted: load()
    onVisibleChanged: if (visible) load()

    actions: [
        RowLayout {  // a quiet status while nothing is unsaved; the button only when there's something to save
            visible: notes.text === page.saved
            height: 40
            spacing: 6
            Icon { name: "check"; size: 14; color: Theme.text3; Layout.preferredWidth: 14; Layout.preferredHeight: 14 }
            Txt { kind: "small"; text: "Saved"; color: Theme.text3; wrapMode: Text.NoWrap }
        },
        Pill {
            visible: notes.text !== page.saved
            text: "Save"; kind: "primary"; symbol: "check"
            onClicked: Api.post("/api/memory", { memory: notes.text }, () => { page.saved = notes.text; Backend.toast("Memory saved", false) })
        }
    ]

    Section {
        title: "What Jarvis knows about you"
        description: "Plain notes, one per line. Jarvis adds to them as you talk."
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(Math.max(notes.implicitHeight + 2, 140), 420)  // (grows with the notes, then scrolls)
            radius: Theme.radiusControl
            color: "transparent"  // (a second glass fill inside the card reads as a stock text box)
            border.width: 1
            border.color: notes.activeFocus ? Theme.accent : Theme.stroke
            Behavior on border.color { ColorAnimation { duration: Theme.fast } }
            Focus { visible: notes.activeFocus }
            ScrollView {
                anchors.fill: parent
                anchors.margins: 1
                clip: true
                TextArea {
                    id: notes
                    placeholderText: "- Prefers to be called …\n- Studies …"
                    placeholderTextColor: Theme.text3
                    color: Theme.text
                    font.family: Theme.font
                    font.pixelSize: Theme.px(14)
                    wrapMode: TextEdit.Wrap
                    selectionColor: Theme.alpha(Theme.accent, 0.4)
                    selectedTextColor: Theme.text
                    background: null
                    padding: 20
                }
            }
        }
    }

    Section {
        title: "Reminders"
        description: page.reminders.length ? `${page.reminders.length} coming up` : "None. Say “remind me at 5 to call home”."
        ColumnLayout {
            Layout.fillWidth: true
            Layout.topMargin: -6; Layout.bottomMargin: -8
            spacing: 0
            visible: page.reminders.length > 0
            Repeater {
                model: page.reminders
                Entry {
                    required property var modelData
                    required property int index
                    first: index === 0
                    symbol: "bell"
                    title: modelData.text
                    Txt { kind: "small"; text: modelData.when; wrapMode: Text.NoWrap; font.features: { "tnum": 1 } }
                    Remove { tip: "Cancel"
                             onClicked: Api.post(`/api/reminders/${modelData.id}/cancel`, {}, page.load) }
                }
            }
        }
    }

    Section {
        title: "Routines"
        description: page.routines.length ? "Say a routine's name and Jarvis runs its steps."
                     : "None yet. Say “when I say study mode, close Discord, open my notes and set a 50-minute timer”."
        ColumnLayout {
            Layout.fillWidth: true
            Layout.topMargin: -6; Layout.bottomMargin: -8
            spacing: 0
            visible: page.routines.length > 0
            Repeater {
                model: page.routines
                Entry {
                    required property var modelData
                    required property int index
                    first: index === 0
                    symbol: "bolt"
                    title: modelData.name.charAt(0).toUpperCase() + modelData.name.slice(1)
                    detail: modelData.steps
                    Remove { tip: "Delete"
                             onClicked: Api.post("/api/routines/delete", { name: modelData.name }, page.load) }
                }
            }
        }
    }

    // A row in a list card: an icon in a soft well, a title and a line under it, then its buttons; a hairline above
    // all but the first.
    component Entry: ColumnLayout {
        property bool first
        property string symbol
        property string title
        property string detail
        default property alias trailing: tail.data
        Layout.fillWidth: true
        spacing: 0
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.stroke; visible: !first }
        RowLayout {
            Layout.fillWidth: true
            Layout.minimumHeight: 40  // (56 with the margins)
            Layout.topMargin: 8; Layout.bottomMargin: 8
            spacing: 14
            Rectangle {
                Layout.preferredWidth: 36; Layout.preferredHeight: 36; radius: 18
                color: Theme.accentSoft
                Icon { anchors.centerIn: parent; name: symbol; size: 18; color: Theme.accent }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Txt { text: title; weight: 500; Layout.fillWidth: true }
                Txt { kind: "small"; text: detail; visible: text !== ""; Layout.fillWidth: true }
            }
            RowLayout { id: tail; spacing: 10 }
        }
    }
    component Remove: IconButton { symbol: "trash"; size: 32; glyph: 18; color: Theme.text3; iconColor: hovered ? Theme.red : color }
}
