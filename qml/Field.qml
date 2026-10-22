import QtQuick
import QtQuick.Controls

// A one-line text field.
TextField {
    id: f
    font.family: Theme.font
    font.pixelSize: Theme.px(14)
    color: Theme.text
    placeholderTextColor: Theme.text3
    selectionColor: Theme.alpha(Theme.accent, 0.4)
    selectedTextColor: Theme.text
    leftPadding: 14; rightPadding: 14
    implicitHeight: 44
    hoverEnabled: true
    background: Rectangle {
        radius: Theme.radiusControl
        color: f.hovered && !f.activeFocus ? Theme.glassHover : Theme.glass
        border.width: 1
        border.color: f.activeFocus ? Theme.accent : Theme.stroke
        Behavior on border.color { ColorAnimation { duration: Theme.fast } }
        Focus { visible: f.activeFocus }
    }
}
