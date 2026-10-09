import QtQuick
import QtQuick.Controls

// A text button. kind: "primary" (violet), "danger", or "" (quiet).
AbstractButton {
    id: b
    property string kind: ""
    property string symbol: ""
    hoverEnabled: true
    focusPolicy: Qt.NoFocus
    implicitHeight: 36
    implicitWidth: row.implicitWidth + 30
    readonly property color fill: kind === "primary" ? Theme.accent : kind === "danger" ? Theme.alpha(Theme.red, 0.14) : Theme.card
    background: Rectangle {
        radius: height / 2
        color: b.hovered ? Qt.lighter(b.fill, b.kind === "primary" ? 1.1 : 1.35) : b.fill
        border.width: b.kind === "" ? 1 : 0
        border.color: Theme.line
        opacity: b.enabled ? 1 : 0.45
        Behavior on color { ColorAnimation { duration: 120 } }
    }
    contentItem: Item {
        Row {
            id: row
            anchors.centerIn: parent
            spacing: 7
            Icon { visible: b.symbol !== ""; name: b.symbol; size: 16; anchors.verticalCenter: parent.verticalCenter
                   color: b.kind === "primary" ? Theme.ink : b.kind === "danger" ? Theme.red : Theme.text }
            Text {
                text: b.text
                font.family: Theme.font; font.pixelSize: 14; font.weight: Font.DemiBold
                color: b.kind === "primary" ? Theme.ink : b.kind === "danger" ? Theme.red : Theme.text
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
    scale: down ? 0.97 : 1
    Behavior on scale { NumberAnimation { duration: 90 } }
}
