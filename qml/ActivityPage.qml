import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Jarvis

// What Jarvis did in this conversation, step by step: tools, notices and its own thinking, newest first.
Item {
    id: page
    property var speeds: []

    function load() {
        Api.get("/api/conversation", c => {
            steps.clear()
            for (const m of c.messages) add(m)
        })
    }
    function add(m) {
        if (!["tool", "system", "thinking"].includes(m.who)) return
        steps.insert(0, { who: m.who, text: String(m.text), time: m.time || Date.now() / 1000 })
    }
    Component.onCompleted: load()
    onVisibleChanged: if (visible) load()
    ListModel { id: steps }
    Connections {
        target: Backend
        function onEvent(json) {
            const e = JSON.parse(json)
            if (e.kind === "log") page.add(e)
            else if (e.kind === "latency") page.speeds = page.speeds.concat([e.seconds]).slice(-20)
        }
    }

    PageHeader {
        id: header
        anchors { left: parent.left; right: parent.right; top: parent.top; topMargin: 46; leftMargin: 34; rightMargin: 34 }
        title: "Activity"
        hint: "Every step Jarvis takes in this conversation, as it happens."
    }

    RowLayout {
        anchors { left: parent.left; right: parent.right; top: header.bottom; bottom: parent.bottom; margins: 34; topMargin: 18 }
        spacing: 16
        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            padding: 6
            ListView {
                anchors.fill: parent
                clip: true
                model: steps
                ScrollBar.vertical: ScrollBar {}
                delegate: RowLayout {
                    required property string who
                    required property string text
                    required property real time
                    width: ListView.view.width
                    spacing: 12
                    height: Math.max(44, line.implicitHeight + 20)
                    Rectangle {
                        Layout.leftMargin: 12
                        Layout.preferredWidth: 30; Layout.preferredHeight: 30; radius: 9
                        color: Theme.alpha(who === "tool" ? Theme.warm : who === "thinking" ? Theme.accent : Theme.dim, 0.14)
                        Icon { anchors.centerIn: parent; size: 15; name: who === "tool" ? "wrench" : who === "thinking" ? "sparkle" : "bell"
                               color: who === "tool" ? Theme.warm : who === "thinking" ? Theme.accent : Theme.dim }
                    }
                    Txt {
                        id: line
                        Layout.fillWidth: true
                        text: who === "tool" ? Backend.toolLabel(parent.text) + "  ·  " + parent.text : parent.text
                        font.pixelSize: 13
                        color: who === "thinking" ? Theme.dim : Theme.text
                        maximumLineCount: 4
                        elide: Text.ElideRight
                    }
                    Txt { Layout.rightMargin: 14; kind: "small"; text: Qt.formatTime(new Date(time * 1000), "HH:mm:ss"); font.family: Theme.mono; font.pixelSize: 11 }
                }
                Txt { anchors.centerIn: parent; kind: "small"; visible: steps.count === 0; text: "Nothing yet: ask Jarvis something" }
            }
        }
        Card {
            Layout.preferredWidth: 260
            Layout.alignment: Qt.AlignTop
            ColumnLayout {
                width: parent.width
                spacing: 8
                Txt { kind: "caps"; text: "Reply speed" }
                Txt {
                    text: page.speeds.length ? (page.speeds.reduce((a, b) => a + b, 0) / page.speeds.length).toFixed(2) + " s" : "–"
                    font.pixelSize: 34; font.weight: Font.Bold
                }
                Txt { kind: "small"; Layout.fillWidth: true
                      text: page.speeds.length ? `on average, from the end of what you said to Jarvis's first word (last ${page.speeds.length})`
                                               : "How fast Jarvis starts answering after you stop talking shows up here." }
                Row {
                    spacing: 3
                    visible: page.speeds.length > 1
                    Repeater {
                        model: page.speeds
                        Rectangle {
                            required property real modelData
                            width: 8; height: Math.max(4, Math.min(48, modelData * 20)); radius: 3
                            anchors.bottom: parent.bottom
                            color: modelData < 1.2 ? Theme.listen : modelData < 2.5 ? Theme.warm : Theme.red
                        }
                    }
                }
            }
        }
    }
}
