import QtQuick

// A short message at the bottom of the window. An error (often the only word that a request failed) stays 8 s, up to
// three lines; it waits while the mouse is on it, and × closes it.
Glass {
    id: t
    property bool bad: false
    function show(text, isBad) { label.text = text; bad = isBad; opacity = 1; if (over.hovered) hide.stop(); else hide.restart() }
    function close() { hide.stop(); opacity = 0 }
    floating: true
    color: Theme.popover
    border.color: bad ? Theme.alpha(Theme.red, 0.4) : Theme.strokeStrong
    width: Math.min(parent ? Math.max(200, parent.width - 96) : 600, label.implicitWidth + 80)
    height: Math.max(44, label.height + 24)
    radius: Math.min(22, height / 2)
    opacity: 0
    visible: opacity > 0
    transform: Translate { y: (1 - t.opacity) * 8 }
    Behavior on opacity { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
    Accessible.role: Accessible.AlertMessage
    Accessible.name: label.text
    HoverHandler { id: over; onHoveredChanged: if (hovered) hide.stop(); else if (t.opacity > 0) hide.restart() }
    Timer { id: hide; interval: t.bad ? 8000 : 3200; onTriggered: t.opacity = 0 }
    StatusDot { id: dot; anchors { left: parent.left; leftMargin: 18; verticalCenter: parent.verticalCenter } status: t.bad ? "error" : "ok" }
    Txt {
        id: label
        anchors { left: dot.right; leftMargin: 10; right: shut.left; rightMargin: 4; verticalCenter: parent.verticalCenter }
        maximumLineCount: 3
        elide: Text.ElideRight
    }
    IconButton {
        id: shut
        anchors { right: parent.right; rightMargin: 8; verticalCenter: parent.verticalCenter }
        size: 28; glyph: 14; symbol: "close"; color: Theme.text3; tip: qsTr("Close")
        onClicked: t.close()
    }
}
