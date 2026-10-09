import QtQuick
import QtQuick.Controls

// A round icon button with a soft hover; `tint` fills it (for Stop, Send...).
AbstractButton {
    id: b
    property string symbol: "plus"
    property color color: Theme.dim
    property color tint: "transparent"
    property int size: 36
    property int glyph: 18
    property string tip: ""
    property color iconColor: tint.a > 0 ? Theme.ink : hovered ? Theme.text : color
    implicitWidth: size
    implicitHeight: size
    hoverEnabled: true
    focusPolicy: Qt.NoFocus
    ToolTip.visible: tip !== "" && hovered
    ToolTip.text: tip
    ToolTip.delay: 500
    background: Rectangle {
        radius: width / 2
        color: b.tint.a > 0 ? (b.hovered ? Qt.lighter(b.tint, 1.12) : b.tint) : (b.down ? Theme.raised : b.hovered ? Theme.cardHover : "transparent")
        Behavior on color { ColorAnimation { duration: 120 } }
    }
    contentItem: Item {
        Icon { anchors.centerIn: parent; name: b.symbol; size: b.glyph; color: b.iconColor }
    }
    scale: down ? 0.94 : 1
    Behavior on scale { NumberAnimation { duration: 90 } }
}
