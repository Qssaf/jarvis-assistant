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
    property string saved: ""

    function load() {
        Api.get("/api/memory", d => { notes.text = d.memory; saved = d.memory })
        Api.get("/api/reminders", d => reminders = d)
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
                font.pixelSize: 14
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
    Item { Layout.preferredHeight: 20 }
}
