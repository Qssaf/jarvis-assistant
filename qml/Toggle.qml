import QtQuick
import QtQuick.Controls

// A switch with a label and an optional hint line under it.
AbstractButton {
    id: t
    property string hint: ""
    checkable: true
    hoverEnabled: true
    focusPolicy: Qt.NoFocus
    implicitHeight: text === "" ? 26 : Math.max(56, col.implicitHeight + 16)  // (a labelled one is a 56 px list row)
    implicitWidth: 300
    contentItem: Item {
        Column {
            id: col
            anchors { left: parent.left; right: track.left; rightMargin: 16; verticalCenter: parent.verticalCenter }
            spacing: 2
            Txt { text: t.text; width: parent.width; visible: text !== "" }
            Txt { text: t.hint; kind: "small"; width: parent.width; visible: t.hint !== "" }
        }
        Rectangle {
            id: track
            anchors { right: parent.right; verticalCenter: parent.verticalCenter }
            width: 44; height: 26; radius: 13
            color: t.checked ? Theme.accent : t.hovered ? Theme.alpha(Theme.track, 1.5) : Theme.track
            Behavior on color { ColorAnimation { duration: 160 } }
            Rectangle {
                width: 20; height: 20; radius: 10
                y: 3; x: t.checked !== t.mirrored ? parent.width - width - 3 : 3
                color: "white"
                Behavior on x { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
            }
        }
    }
}
