import QtQuick

// A short message at the bottom of the window.
Rectangle {
    id: t
    property bool bad: false
    function show(text, isBad) { label.text = text; bad = isBad; opacity = 1; hide.restart() }
    width: label.implicitWidth + 36
    height: 40
    radius: 20
    color: Theme.raised
    border.width: 1
    border.color: bad ? Theme.alpha(Theme.red, 0.5) : Theme.lineStrong
    opacity: 0
    visible: opacity > 0
    Behavior on opacity { NumberAnimation { duration: 180 } }
    Timer { id: hide; interval: 3200; onTriggered: t.opacity = 0 }
    Txt { id: label; anchors.centerIn: parent; color: t.bad ? Theme.red : Theme.text; wrapMode: Text.NoWrap }
}
