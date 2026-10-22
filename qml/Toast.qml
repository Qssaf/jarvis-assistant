import QtQuick

// A short message at the bottom of the window.
Glass {
    id: t
    property bool bad: false
    function show(text, isBad) { label.text = text; bad = isBad; opacity = 1; hide.restart() }
    floating: true
    color: Theme.popover
    border.color: bad ? Theme.alpha(Theme.red, 0.4) : Theme.strokeStrong
    width: label.implicitWidth + 50
    height: 44
    radius: 22
    opacity: 0
    visible: opacity > 0
    transform: Translate { y: (1 - t.opacity) * 8 }
    Behavior on opacity { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
    Timer { id: hide; interval: 3200; onTriggered: t.opacity = 0 }
    StatusDot { id: dot; x: 18; anchors.verticalCenter: parent.verticalCenter; status: t.bad ? "error" : "ok" }
    Txt { id: label; anchors.left: dot.right; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter; wrapMode: Text.NoWrap }
}
