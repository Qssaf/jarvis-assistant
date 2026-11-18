import QtQuick

// The soft cyan ring around a focused field: put it inside the field's background. `keyboard`: the sharper ring
// around a button, switch or chip that Tab has reached (visualFocus), which has no border of its own to light up.
Rectangle {
    property bool keyboard: false
    anchors.fill: parent
    anchors.margins: -3
    radius: parent.radius + 3
    color: "transparent"
    border.width: keyboard ? 2 : 3
    border.color: keyboard ? Theme.accent : Theme.accentSoft
}
