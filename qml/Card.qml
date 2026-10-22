import QtQuick

// A glass card; put content inside (it fills the padding box). `hover` lights it up under the mouse.
Glass {
    id: card
    default property alias content: box.data
    property int padding: Theme.pad
    property bool hover: false
    color: hover && mouse.containsMouse ? Theme.glassHover : Theme.glass
    implicitHeight: (box.children.length ? box.children[0].implicitHeight : 0) + 2 * padding
    Behavior on color { ColorAnimation { duration: Theme.fast } }
    MouseArea { id: mouse; anchors.fill: parent; hoverEnabled: card.hover; acceptedButtons: Qt.NoButton }
    Item { id: box; anchors.fill: parent; anchors.margins: card.padding }
}
