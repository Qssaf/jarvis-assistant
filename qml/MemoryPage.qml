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

    actions: Pill {
        text: notes.text === page.saved ? "Saved" : "Save"
        kind: notes.text === page.saved ? "" : "primary"
        symbol: "check"
        enabled: notes.text !== page.saved
        onClicked: Api.post("/api/memory", { memory: notes.text }, () => { page.saved = notes.text; Backend.toast("Memory saved", false) })
    }

    Card {
        Layout.fillWidth: true
        Layout.preferredHeight: 320
        padding: 6
        ScrollView {
            anchors.fill: parent
            TextArea {
                id: notes
                placeholderText: "- Prefers to be called …\n- Studies …"
                placeholderTextColor: Theme.faint
                color: Theme.text
                font.family: Theme.font
                font.pixelSize: Theme.px(14)
                wrapMode: TextEdit.Wrap
                selectionColor: Theme.alpha(Theme.accent, 0.45)
                background: null
                padding: 12
            }
        }
    }

    Txt { kind: "heading"; text: "Reminders"; Layout.topMargin: 10 }
    Card {
        Layout.fillWidth: true
        ColumnLayout {
            width: parent.width
            spacing: 6
            Txt { kind: "small"; text: "None. Say “remind me at 5 to call home”."; visible: !page.reminders.length }
            Repeater {
                model: page.reminders
                RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 12
                    Icon { name: "bell"; size: 17; color: Theme.accent }
                    Txt { text: modelData.text; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                    Txt { kind: "small"; text: modelData.when }
                    IconButton { symbol: "close"; size: 30; glyph: 14; tip: "Cancel"
                                 onClicked: Api.post(`/api/reminders/${modelData.id}/cancel`, {}, page.load) }
                }
            }
        }
    }
    Txt { kind: "heading"; text: "Routines"; Layout.topMargin: 10 }
    Card {
        Layout.fillWidth: true
        ColumnLayout {
            width: parent.width
            spacing: 8
            Txt { kind: "small"; Layout.fillWidth: true; visible: !page.routines.length
                  text: "None yet. Say “when I say study mode, close Discord, open my notes and set a 50-minute timer”." }
            Repeater {
                model: page.routines
                RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 12
                    Icon { name: "bolt"; size: 17; color: Theme.accent }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Txt { text: modelData.name; font.weight: Font.DemiBold }
                        Txt { kind: "small"; text: modelData.steps; Layout.fillWidth: true }
                    }
                    IconButton { symbol: "trash"; size: 30; glyph: 14; tip: "Delete"
                                 onClicked: Api.post("/api/routines/delete", { name: modelData.name }, page.load) }
                }
            }
        }
    }
    Item { Layout.preferredHeight: 20 }
}
