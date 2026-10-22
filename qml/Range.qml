import QtQuick
import QtQuick.Controls
import QtQuick.Effects

// A slider: a thin track edge to edge (the knob overhangs its ends by half), the filled part in cyan, a white knob.
Slider {
    id: s
    implicitHeight: 24
    leftPadding: 0; rightPadding: 0
    background: Rectangle {
        x: s.leftPadding; y: s.topPadding + s.availableHeight / 2 - 2
        width: s.availableWidth; height: 4; radius: 2; color: Theme.track
        Rectangle { width: s.visualPosition * parent.width; height: 4; radius: 2; color: Theme.accent }
    }
    handle: Rectangle {
        x: s.leftPadding + s.visualPosition * s.availableWidth - width / 2
        y: s.topPadding + s.availableHeight / 2 - height / 2
        width: 20; height: 20; radius: 10
        color: "white"
        border.width: 1
        border.color: Theme.stroke
        RectangularShadow { z: -1; anchors.fill: parent; radius: 10; blur: 6; offset.y: 1; color: Theme.shadow }
        Rectangle {  // the glow ring under the mouse
            z: -2
            anchors.centerIn: parent
            width: s.pressed || s.hovered ? 32 : 20; height: width; radius: width / 2
            color: Theme.accentSoft
            Behavior on width { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
        }
    }
}
