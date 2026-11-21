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
    focusPolicy: Qt.TabFocus  // (Tab reaches it; a click leaves the typing where it was)
    Keys.onReturnPressed: click()
    Keys.onEnterPressed: click()
    Accessible.name: tip  // (a button with only a picture: screen readers say what it does)
    Tip { text: b.tip; visible: b.tip !== "" && (b.hovered || b.visualFocus) }  // (the keyboard gets the name too)
    background: Rectangle {
        radius: width / 2
        // (a see-through tint, like glass, gets stronger under the mouse: lighter white is still white)
        color: b.tint.a > 0 ? (!b.hovered ? b.tint : b.tint.a < 1 ? Theme.alpha(b.tint, Math.min(1.6, 1 / b.tint.a)) : Qt.lighter(b.tint, 1.1))
                            : (b.down ? Theme.glassHover : b.hovered ? Theme.glass : "transparent")
        border.width: b.tint.a === 0 && b.hovered ? 1 : 0
        border.color: Theme.stroke
        Behavior on color { ColorAnimation { duration: Theme.fast } }
        Focus { keyboard: true; visible: b.visualFocus }
    }
    contentItem: Item {
        Icon { anchors.centerIn: parent; name: b.symbol; size: b.glyph; color: b.iconColor }
    }
    scale: down ? 0.94 : 1
    Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
}
