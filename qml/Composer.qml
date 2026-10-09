import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Jarvis

// The message box: Enter sends, Shift+Enter starts a new line; attach files, talk, or stop Jarvis.
Rectangle {
    id: c
    property var attachments: []
    signal submitted(string text)
    signal attach()
    signal removed(string path)
    readonly property bool busy: Backend.state !== "idle"
    implicitHeight: col.implicitHeight + 16
    radius: 22
    color: Theme.card
    border.width: 1
    border.color: input.activeFocus ? Theme.alpha(Theme.accent, 0.6) : Theme.lineStrong
    Behavior on border.color { ColorAnimation { duration: 140 } }

    ColumnLayout {
        id: col
        anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; leftMargin: 8; rightMargin: 8 }
        spacing: 6
        Flow {  // attached files
            Layout.fillWidth: true
            Layout.leftMargin: 6
            visible: c.attachments.length > 0
            spacing: 6
            Repeater {
                model: c.attachments
                Rectangle {
                    required property string modelData
                    height: 28; radius: 14
                    width: chip.implicitWidth + 40
                    color: Theme.raised
                    Txt { id: chip; x: 12; anchors.verticalCenter: parent.verticalCenter; kind: "small"; color: Theme.text
                            text: modelData.split("/").pop(); wrapMode: Text.NoWrap }
                    IconButton { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; size: 24; glyph: 12; symbol: "close"
                                 onClicked: c.removed(modelData) }
                }
            }
        }
        RowLayout {
            spacing: 4
            IconButton { symbol: "attach"; tip: "Attach files (or drop them here)"; onClicked: c.attach() }
            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(Math.max(40, input.implicitHeight), 160)
                TextArea {
                    id: input
                    placeholderText: "Message Jarvis…"
                    placeholderTextColor: Theme.faint
                    color: Theme.text
                    font.family: Theme.font
                    font.pixelSize: 15
                    wrapMode: TextEdit.Wrap
                    selectionColor: Theme.alpha(Theme.accent, 0.45)
                    verticalAlignment: TextEdit.AlignVCenter
                    background: null
                    focus: true
                    Keys.onReturnPressed: event => {
                        if (event.modifiers & Qt.ShiftModifier) { event.accepted = false; return }
                        c.submitted(text)
                        text = ""
                    }
                }
            }
            IconButton {
                symbol: Backend.listening ? "pause" : "mic"
                tip: Backend.listening ? "Pause listening" : "Talk to Jarvis"
                color: Backend.listening ? Theme.listen : Theme.dim
                onClicked: Backend.listening ? Backend.pause() : Backend.talk()
            }
            IconButton {
                readonly property bool stopping: c.busy && input.text.trim() === "" && c.attachments.length === 0
                symbol: stopping ? "stop" : "send"
                tint: stopping ? Theme.red : (input.text.trim() || c.attachments.length ? Theme.accent : Theme.raised)
                tip: stopping ? "Stop (Esc)" : "Send (Enter)"
                iconColor: tint === Theme.raised ? Theme.faint : Theme.ink
                onClicked: { if (stopping) Backend.stop(); else { c.submitted(input.text); input.text = "" } }
            }
        }
    }
}
