import QtQuick

// An 8 px status light. status: "ok" (green), "working" (orange), "error" (red), anything else is off (grey).
Rectangle {
    property string status: "off"
    width: 8; height: 8; radius: 4
    color: status === "ok" ? Theme.green : status === "working" ? Theme.warm : status === "error" ? Theme.red : Theme.text3
    Rectangle {  // a faint glow when it's lit
        z: -1
        anchors.centerIn: parent
        width: 16; height: 16; radius: 8
        color: Theme.alpha(parent.color, 0.18)
        visible: parent.status === "ok" || parent.status === "working" || parent.status === "error"
    }
}
