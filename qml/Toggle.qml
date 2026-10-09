import QtQuick
import QtQuick.Controls

// A switch with a label and an optional hint line under it.
AbstractButton {
    id: t
    property string hint: ""
    checkable: true
    hoverEnabled: true
    focusPolicy: Qt.NoFocus
    implicitHeight: Math.max(28, col.implicitHeight)
    implicitWidth: 300
    contentItem: Item {
        Column {
            id: col
            anchors { left: parent.left; right: track.left; rightMargin: 16; verticalCenter: parent.verticalCenter }
            spacing: 2
            Txt { text: t.text; width: parent.width }
            Txt { text: t.hint; kind: "small"; width: parent.width; visible: t.hint !== "" }
        }
        Rectangle {
            id: track
            anchors { right: parent.right; verticalCenter: parent.verticalCenter }
            width: 40; height: 22; radius: 11
            color: t.checked ? Theme.accent : Theme.raised
            border.width: 1; border.color: t.checked ? "transparent" : Theme.lineStrong
            Behavior on color { ColorAnimation { duration: 150 } }
            Rectangle {
                width: 16; height: 16; radius: 8
                y: 3; x: t.checked ? parent.width - width - 3 : 3
                color: t.checked ? Theme.ink : Theme.dim
                Behavior on x { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
            }
        }
    }
}
