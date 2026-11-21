import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Jarvis

// What Jarvis did in this conversation, step by step, newest first: each tool call with what it was asked and what came
// back (the work log: /api/work, then "work" events), notices and its own thinking. A call still running shows by name.
Item {
    id: page
    property var speeds: []
    property var rows: []  // every step, newest first; `steps` holds the ones the filter shows
    property string filter: "all"  // "all", "errors", "voice", "task"

    function load() {
        Api.get("/api/conversation", c => Api.get("/api/work", work => {
            const started = c.messages.filter(m => m.who === "tool")
            const paired = new Set()
            for (const w of work.slice().reverse()) {  // (oldest first) a finished call replaces the newest "started" line of its name before it
                for (let i = started.length - 1; i >= 0; i--)
                    if (!paired.has(i) && started[i].text === w.name && (started[i].time || 0) <= w.time + 1) { paired.add(i); break }
            }
            const all = c.messages.filter(m => ["system", "thinking"].includes(m.who))
                         .map(m => row(m.who, { text: String(m.text), time: m.time || 0 }))
                         .concat(started.filter((m, i) => !paired.has(i)).map(m => row("tool", { name: String(m.text), time: m.time || 0 })))
                         .concat(work.map(w => row("work", w)))
            rows = all.sort((a, b) => b.time - a.time)
            show()
        }))
    }
    function row(kind, d) {  // one shape for every step, so the list's roles are always the same
        return { kind: kind, who: d.who || "", name: d.name || "", text: d.text || "", label: d.label || "", args: d.args || "",
                 result: d.result || "", error: !!d.error, time: d.time || Date.now() / 1000 }
    }
    function shows(r) {
        return page.filter === "all" || r.kind === "work" && (page.filter === "errors" ? r.error : r.who === page.filter)
    }
    function show() {
        steps.clear()
        for (const r of rows)
            if (shows(r)) steps.append(r)
    }
    function add(r) {
        if (r.kind === "work") {  // the call it finishes: started, not done yet (not there when it ran before the page opened)
            const i = rows.findIndex(s => s.kind === "tool" && s.name === r.name)
            if (i >= 0) {
                rows = rows.slice(0, i).concat(rows.slice(i + 1))
                for (let j = 0; j < steps.count; j++)
                    if (steps.get(j).kind === "tool" && steps.get(j).name === r.name) { steps.remove(j); break }
            }
        }
        rows = [r].concat(rows)
        if (shows(r)) steps.insert(0, r)
    }
    function plain(t) {  // a leading emoji in a notice clashes with the line icons
        return t.replace(/^(?:[⌀-➿⬀-⯿]|[\ud83c-\ud83e][\udc00-\udfff])️?\s*/, "")
    }
    onFilterChanged: show()
    Component.onCompleted: load()
    onVisibleChanged: if (visible) load()
    ListModel { id: steps }
    Connections {
        target: Backend
        function onEvent(json) {
            const e = JSON.parse(json)
            if (e.kind === "work") page.add(page.row("work", e))
            else if (e.kind === "log" && e.who === "tool") page.add(page.row("tool", { name: String(e.text) }))
            else if (e.kind === "log" && ["system", "thinking"].includes(e.who)) page.add(page.row(e.who, { text: String(e.text) }))
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
            Repeater {
                model: [["all", qsTr("All")], ["errors", qsTr("Errors")], ["voice", qsTr("Voice")], ["task", qsTr("Tasks")]]
                Chip { required property var modelData; text: modelData[1]; checked: page.filter === modelData[0]; onClicked: page.filter = modelData[0]
                       Accessible.role: Accessible.RadioButton; Accessible.checkable: true; Accessible.checked: checked }
            }
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
                        required property string kind
                        required property string who
                        required property string name
                        required property string text
                        required property string label
                        required property string args
                        required property string result
                        required property bool error
                        required property real time
                        required property int index
                        readonly property bool work: kind === "work"
                        readonly property color tint: error ? Theme.red : work ? Theme.accent : kind === "tool" ? Theme.warm
                                                    : kind === "thinking" ? Theme.accent : Theme.text2
                        readonly property string title: work ? label : kind === "tool" ? Backend.toolLabel(name) : page.plain(text)
                        width: ListView.view.width
                        height: Math.max(56, words.implicitHeight + 28)
                        Accessible.role: Accessible.ListItem
                        Accessible.name: [error ? qsTr("Failed: %1").arg(title) : title, args, result].filter(t => t).join(". ")
                        Rectangle {
                            anchors.fill: parent
                            radius: Theme.radiusControl
                            color: hover.hovered ? Theme.glassHover : "transparent"
                            Behavior on color { ColorAnimation { duration: Theme.fast } }
                        }
                        HoverHandler { id: hover }
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
                            border.color: Theme.alpha(step.tint, step.error ? 0.4 : 0.2)
                            Icon { anchors.centerIn: parent; size: 16; color: step.tint
                                   name: step.error ? "alert" : step.work ? (step.who === "voice" ? "mic" : "bolt") : step.kind === "tool" ? "wrench"
                                         : step.kind === "thinking" ? "sparkle" : "bell" }
                        }
                        ColumnLayout {
                            id: words
                            anchors { left: parent.left; leftMargin: 56; right: when.left; rightMargin: 12; top: parent.top; topMargin: 14 }
                            spacing: 3
                            Txt { text: step.title; Layout.fillWidth: true; maximumLineCount: 4; elide: Text.ElideRight
                                  weight: step.kind === "thinking" ? 400 : 500; color: step.kind === "thinking" ? Theme.text2 : Theme.text }
                            Txt { kind: "small"; text: step.args; visible: text !== ""; Layout.fillWidth: true; maximumLineCount: 2; elide: Text.ElideRight
                                  color: Theme.text3 }
                            Txt { kind: "small"; text: step.result; visible: text !== ""; Layout.fillWidth: true; maximumLineCount: 3; elide: Text.ElideRight
                                  color: step.error ? Theme.red : Theme.text2 }
                        }
                        Column {
                            id: when
                            anchors { right: parent.right; rightMargin: 16; top: parent.top; topMargin: 16 }
                            spacing: 2
                            Txt { anchors.right: parent.right; kind: "small"; font.pixelSize: Theme.px(12); font.features: { "tnum": 1 }
                                  color: Theme.text3; wrapMode: Text.NoWrap; text: Qt.formatTime(new Date(step.time * 1000), "HH:mm:ss") }
                            Txt { anchors.right: parent.right; kind: "small"; font.pixelSize: Theme.px(12); color: Theme.text3; wrapMode: Text.NoWrap
                                  visible: step.work; text: step.who === "voice" ? qsTr("Voice") : qsTr("Task") }
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
                            color: page.filter === "errors" ? Theme.alpha(Theme.green, 0.14) : Theme.accentSoft
                            Icon { anchors.centerIn: parent; name: page.filter === "errors" ? "check" : "activity"; size: 20
                                   color: page.filter === "errors" ? Theme.green : Theme.accent }
                        }
                        Txt { Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; kind: "small"
                              text: page.filter === "all" ? qsTr("Nothing yet: ask Jarvis something")
                                    : page.filter === "errors" ? qsTr("Nothing has failed in this conversation")
                                    : page.filter === "voice" ? qsTr("The voice hasn't used a tool in this conversation yet")
                                    : qsTr("No background task has used a tool in this conversation yet") }
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
