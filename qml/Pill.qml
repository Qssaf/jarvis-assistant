import QtQuick
import QtQuick.Controls

// A round text button. kind: "primary" (solid cyan), "" (glass), "ghost" (text only), "danger" (red text on glass).
AbstractButton {
    id: b
    property string kind: ""
    property string symbol: ""
    readonly property bool primary: kind === "primary"
    readonly property color ink: primary ? Theme.accentInk : kind === "danger" ? Theme.red
                                : kind === "ghost" && !hovered ? Theme.text2 : Theme.text
    hoverEnabled: true
    focusPolicy: Qt.NoFocus
    implicitHeight: 40
    implicitWidth: row.implicitWidth + (kind === "ghost" ? 24 : 36)
    opacity: enabled ? 1 : 0.45
    background: Rectangle {
        radius: height / 2
        color: b.primary ? (b.hovered ? Qt.lighter(Theme.accent, 1.08) : Theme.accent)
             : b.kind === "ghost" ? (b.hovered ? Theme.glass : "transparent")
             : b.kind === "danger" && b.hovered ? Theme.alpha(Theme.red, 0.12)
             : b.hovered ? Theme.glassHover : Theme.glass
        border.width: b.primary || b.kind === "ghost" ? 0 : 1
        border.color: b.kind === "danger" && b.hovered ? Theme.alpha(Theme.red, 0.35) : Theme.stroke
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }
    contentItem: Item {
        Row {
            id: row
            anchors.centerIn: parent
            spacing: 8
            Icon { visible: b.symbol !== ""; name: b.symbol; size: 16; color: b.ink; anchors.verticalCenter: parent.verticalCenter }
            Text {
                text: b.text
                font.family: Theme.font; font.pixelSize: Theme.px(14); font.weight: 600; font.variableAxes: { "wght": 600 }
                color: b.ink
                anchors.verticalCenter: parent.verticalCenter
                Behavior on color { ColorAnimation { duration: Theme.fast } }
            }
        }
    }
    scale: down ? 0.97 : 1
    Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
}
