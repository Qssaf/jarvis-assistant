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
    function plain(t) {  // a leading emoji in a notice clashes with the line icons
        return t.replace(/^(?:[\u2300-\u27bf\u2b00-\u2bff]|[\ud83c-\ud83e][\udc00-\udfff])\ufe0f?\s*/, "")
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

    ColumnLayout {
        anchors { top: parent.top; bottom: parent.bottom; horizontalCenter: parent.horizontalCenter; margins: Theme.margin }
        width: Math.min(parent.width - 2 * Theme.margin, Theme.pageWidth)
        spacing: 24

        PageHeader {
            Layout.fillWidth: true
            title: qsTr("Activity")
            hint: qsTr("Every step Jarvis takes in this conversation, as it happens.")
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.gap

            Card {  // the steps, newest first, on a timeline through their icons; as tall as they are, up to the page
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.maximumHeight: steps.count ? list.contentHeight + 2 * padding : Number.POSITIVE_INFINITY
                Layout.alignment: Qt.AlignTop
                padding: 8
                ListView {
                    id: list
                    anchors.fill: parent
                    clip: true
                    model: steps
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: Scroller {}
                    delegate: Item {
                        id: step
                        required property string who
                        required property string text
                        required property real time
                        required property int index
                        readonly property color tint: who === "tool" ? Theme.warm : who === "thinking" ? Theme.accent : Theme.text2
                        width: ListView.view.width
                        height: Math.max(56, title.implicitHeight + 32)
                        Rectangle {
                            anchors.fill: parent
                            radius: Theme.radiusControl
                            color: hover.hovered ? Theme.glassHover : "transparent"
                            Behavior on color { ColorAnimation { duration: Theme.fast } }
                        }
                        HoverHandler { id: hover }
                        Tip { text: step.text; visible: step.who === "tool" && hover.hovered }
                        Rectangle {  // the timeline
                            anchors { left: parent.left; leftMargin: 27 }
                            y: step.index === 0 ? 28 : 0
                            width: 1; height: (step.index === steps.count - 1 ? 28 : step.height) - y
                            color: Theme.stroke
                        }
                        Rectangle {
                            anchors { left: parent.left; leftMargin: 12 }
                            y: 12
                            width: 32; height: 32; radius: 16
                            color: Qt.tint(Theme.bg, Theme.alpha(step.tint, 0.16))  // opaque, so the timeline stops at its edge
                            border.width: 1
                            border.color: Theme.alpha(step.tint, 0.2)
                            Icon { anchors.centerIn: parent; size: 16; color: step.tint
                                   name: step.who === "tool" ? "wrench" : step.who === "thinking" ? "sparkle" : "bell" }
                        }
                        Txt {
                            id: title
                            anchors { left: parent.left; leftMargin: 56; right: when.left; rightMargin: 12; verticalCenter: parent.verticalCenter }
                            text: step.who === "tool" ? Backend.toolLabel(step.text) : page.plain(step.text)
                            weight: step.who === "thinking" ? 400 : 500
                            color: step.who === "thinking" ? Theme.text2 : Theme.text
                            maximumLineCount: 4
                            elide: Text.ElideRight
                        }
                        Txt {
                            id: when
                            anchors { right: parent.right; rightMargin: 16; baseline: title.baseline }
                            kind: "small"; font.pixelSize: Theme.px(12); font.features: { "tnum": 1 }; color: Theme.text3; wrapMode: Text.NoWrap
                            text: Qt.formatTime(new Date(step.time * 1000), "HH:mm:ss")
                        }
                        Rectangle {
                            anchors { left: parent.left; right: parent.right; bottom: parent.bottom; leftMargin: 56; rightMargin: 12 }
                            height: 1
                            color: Theme.stroke
                            visible: step.index < steps.count - 1 && !hover.hovered
                        }
                    }
                    footer: Item {
                        width: ListView.view.width
                        visible: steps.count > 0
                        height: hint.implicitHeight + 24
                        Txt {
                            id: hint
                            y: 16
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            kind: "small"; color: Theme.text3
                            text: qsTr("New steps appear at the top as Jarvis works")
                        }
                    }
                    ColumnLayout {
                        anchors.centerIn: parent
                        width: parent.width - 32
                        visible: steps.count === 0
                        spacing: 12
                        Rectangle {
                            Layout.alignment: Qt.AlignHCenter
                            width: 40; height: 40; radius: 20
                            color: Theme.accentSoft
                            Icon { anchors.centerIn: parent; name: "activity"; size: 20; color: Theme.accent }
                        }
                        Txt { Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; kind: "small"; text: qsTr("Nothing yet: ask Jarvis something") }
                    }
                }
            }

            Card {  // shows up with the first timed reply
                Layout.preferredWidth: 260
                Layout.alignment: Qt.AlignTop
                visible: page.speeds.length > 0
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 6
                    Txt { kind: "label"; text: qsTr("Reply speed") }
                    Row {
                        spacing: 4
                        Txt {
                            id: average
                            text: page.speeds.length ? (page.speeds.reduce((a, b) => a + b, 0) / page.speeds.length).toFixed(2) : ""
                            kind: "display"; font.features: { "tnum": 1 }; wrapMode: Text.NoWrap
                        }
                        //: seconds, after the average reply time
                        Txt { text: qsTr("s"); kind: "heading"; weight: 500; color: Theme.text2; anchors.baseline: average.baseline }
                    }
                    Txt { kind: "small"; Layout.fillWidth: true; lineHeight: 1.15
                          text: qsTr("Averaged over the last %n replies: from the end of what you said to Jarvis's first word.", "", page.speeds.length) }
                    Item { Layout.fillHeight: true }
                    Item {
                        id: chart
                        Layout.fillWidth: true
                        implicitHeight: 64
                        visible: page.speeds.length > 1
                        Row {
                            anchors.bottom: parent.bottom
                            spacing: 4
                            Repeater {
                                model: page.speeds
                                Rectangle {
                                    required property real modelData
                                    width: Math.floor((chart.width - 19 * 4) / 20); height: Math.max(4, Math.min(64, modelData * 24)); radius: 3
                                    anchors.bottom: parent.bottom
                                    color: modelData < 1.2 ? Theme.listen : modelData < 2.5 ? Theme.warm : Theme.red
                                }
                            }
                        }
                    }
                }
            }
        }
        Item { Layout.fillHeight: true; visible: steps.count > 0 }  // the room a short list of steps leaves free
    }
}
