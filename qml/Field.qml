import QtQuick
import QtQuick.Controls

// A one-line text field.
TextField {
    id: f
    font.family: Theme.font
    font.pixelSize: 14
    color: Theme.text
    placeholderTextColor: Theme.faint
    selectionColor: Theme.alpha(Theme.accent, 0.45)
    selectedTextColor: Theme.text
    leftPadding: 14; rightPadding: 14
    implicitHeight: 40
    background: Rectangle {
        radius: Theme.radiusSmall
        color: Theme.bg
        border.width: 1
        border.color: f.activeFocus ? Theme.accent : Theme.lineStrong
        Behavior on border.color { ColorAnimation { duration: 120 } }
    }
}
