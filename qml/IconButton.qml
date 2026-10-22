import QtQuick
import QtQuick.Controls

// A round icon button with a soft hover; `tint` fills it (for Stop, Send...).
AbstractButton {
    id: b
    property string symbol: "plus"
    property color color: Theme.text2
    property color tint: "transparent"
    property int size: 36
    property int glyph: 18
    property string tip: ""
    property color iconColor: tint.a > 0 ? Theme.accentInk : hovered ? Theme.text : color
    implicitWidth: size
    implicitHeight: size
    hoverEnabled: true
    focusPolicy: Qt.NoFocus
    Tip { text: b.tip; visible: b.tip !== "" && b.hovered }
    background: Rectangle {
        radius: width / 2
        color: b.tint.a > 0 ? (b.hovered ? Qt.lighter(b.tint, 1.1) : b.tint) : (b.down ? Theme.glassHover : b.hovered ? Theme.glass : "transparent")
        border.width: b.tint.a === 0 && b.hovered ? 1 : 0
        border.color: Theme.stroke
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }
    contentItem: Item {
        Icon { anchors.centerIn: parent; name: b.symbol; size: b.glyph; color: b.iconColor }
    }
    scale: down ? 0.94 : 1
    Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
}
