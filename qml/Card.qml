import QtQuick

// A surface with a hairline border; put content inside (it fills the padding box).
Rectangle {
    id: card
    default property alias content: box.data
    property int padding: 18
    property bool hover: false
    color: hover && mouse.containsMouse ? Theme.cardHover : Theme.card
    radius: Theme.radius
    border.width: 1
    border.color: Theme.line
    implicitHeight: (box.children.length ? box.children[0].implicitHeight : 0) + 2 * padding
    Behavior on color { ColorAnimation { duration: 140 } }
    MouseArea { id: mouse; anchors.fill: parent; hoverEnabled: card.hover; acceptedButtons: Qt.NoButton }
    Item { id: box; anchors.fill: parent; anchors.margins: card.padding }
}
