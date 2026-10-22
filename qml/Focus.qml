import QtQuick

// The soft cyan ring around a focused field: put it inside the field's background.
Rectangle {
    anchors.fill: parent
    anchors.margins: -3
    radius: parent.radius + 3
    color: "transparent"
    border.width: 3
    border.color: Theme.accentSoft
}
