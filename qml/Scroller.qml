import QtQuick
import QtQuick.Controls

// A thin scroll bar that shows while scrolling or under the mouse: `ScrollBar.vertical: Scroller {}`.
ScrollBar {
    id: s
    hoverEnabled: true
    padding: 3
    contentItem: Rectangle {
        implicitWidth: s.hovered || s.pressed ? 6 : 4
        implicitHeight: 4
        radius: 3
        color: s.pressed ? Theme.alpha(Theme.text, 0.35) : Theme.alpha(Theme.text, 0.2)
        opacity: s.policy === ScrollBar.AlwaysOn || (s.active && s.size < 1) ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 300 } }
        Behavior on implicitWidth { NumberAnimation { duration: Theme.fast } }
    }
}
