import QtQuick

// A line icon from Jarvis's set (ui.py ICONS), drawn crisp in any colour.
Image {
    property string name: "home"
    property color color: Theme.text
    property int size: 20
    width: size
    height: size
    sourceSize: Qt.size(size * 2, size * 2)
    source: name ? "image://icon/" + name + "/" + String(color).replace("#", "") : ""
    smooth: true
}
