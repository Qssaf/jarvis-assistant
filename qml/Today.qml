import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Layouts
import Jarvis

// Today at a glance: the time and weather, what's playing, what's next, and how the PC is doing.
// `compact` (a narrow window) folds it into one strip: the time, the weather and what's playing.
ScrollView {
    id: today
    property real latency: -1
    property bool compact: false
    signal wake(string phrase)
    property var info: ({})
    property var media: ({})
    property var stats: ({})
    property var jobs: []
    // (one line each, for the tips of the Stop buttons that end them all)
    readonly property string jobList: jobs.map(j => "• " + (j.label.length > 64 ? j.label.slice(0, 63) + "…" : j.label)).join("\n")
    property var finished: []  // /api/jobs/done: the longer tasks that ended lately, with what each answered
    property var todo: null  // /api/todo: {items, couldnt_check}
    readonly property var todoAll: todo ? todo.items : (info.reminders || []).map(r => ({ what: r.text, when: r.when, id: r.id, kind: "reminder" }))
    property bool todoOpen: false  // "+n more" pressed: every item, not the first five
    readonly property var todoRows: todoOpen ? todoAll : todoAll.slice(0, 5)
    property var opened: ({})  // finished tasks shown whole, by their number
    property var now: new Date()
    readonly property var weather: info.weather || {}
    readonly property bool shown: visible && Window.window !== null && Window.window.visible
    contentWidth: availableWidth
    contentHeight: compact ? strip.implicitHeight : cards.implicitHeight
    clip: true
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical: Scroller { parent: today; x: today.width - width; height: today.availableHeight }

    function load() { Api.get("/api/today", t => { info = t; wake(t.wake || "Hey Jarvis") }) }
    function loadTodo() { Api.get("/api/todo", d => todo = d) }
    function when(t) {  // a time today, else the day too
        const d = new Date(t * 1000)
        return Qt.formatDateTime(d, d.toDateString() === today.now.toDateString() ? "HH:mm" : "ddd d MMM, HH:mm")
    }
    function live() {
        Api.get("/api/media", d => media = d)
        Api.get("/api/system", d => stats = d)
        // (a list that hasn't changed isn't set again: its rows were made anew every 3 s, and a Stop Tab had reached lost it)
        Api.get("/api/jobs", d => { if (JSON.stringify(d) !== JSON.stringify(jobs)) jobs = d })
        Api.get("/api/jobs/done", d => { if (JSON.stringify(d) !== JSON.stringify(finished)) finished = d })
    }
    function clock(seconds) {  // 3:07, 1:02:45
        const s = Math.max(0, Math.floor(seconds)), h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60
        return (h ? h + ":" + String(m).padStart(2, "0") : m) + ":" + String(s % 60).padStart(2, "0")
    }
    function gb(bytes) { return (bytes / 1073741824).toFixed(1) }
    function sky(c) {  // a line icon for wttr.in's condition (its emoji clash with the icon set)
        c = String(c).toLowerCase()
        return /thunder/.test(c) ? "bolt" : /sun/.test(c) ? "sun" : /clear/.test(c) ? (today.now.getHours() < 6 || today.now.getHours() >= 19 ? "moon" : "sun") : "cloud"
    }
    Component.onCompleted: { load(); live() }
    Timer { interval: 60000; running: true; repeat: true; onTriggered: today.load() }
    Timer { interval: 600000; running: today.shown; repeat: true; triggeredOnStart: true; onTriggered: today.loadTodo() }
    Timer { interval: 3000; running: today.shown; repeat: true; triggeredOnStart: true; onTriggered: today.live() }
    Timer { interval: 1000; running: today.shown; repeat: true; triggeredOnStart: true; onTriggered: today.now = new Date() }
    Connections {
        target: Backend
        function onEvent(json) { if (JSON.parse(json).kind === "log" && json.indexOf("Reminder") >= 0) { today.load(); today.loadTodo() } }
    }

    Glass {
        id: strip
        visible: today.compact
        width: today.availableWidth
        implicitHeight: 56
        radius: 28
        RowLayout {
            anchors { fill: parent; leftMargin: 22; rightMargin: 10 }
            spacing: 12
            Txt { text: Qt.formatTime(today.now, "HH:mm"); kind: "heading"; font.features: { "tnum": 1 }; wrapMode: Text.NoWrap }
            Icon { visible: !!today.weather.temp; name: today.sky(today.weather.condition); size: 18; Layout.preferredWidth: 18; Layout.preferredHeight: 18; color: name === "sun" ? Theme.accent : Theme.text2 }
            Txt { visible: !!today.weather.temp; text: today.weather.temp || ""; kind: "small"; wrapMode: Text.NoWrap }
            // what the side column shows in a wide window, a click away: the tasks at work (each with its Stop) and the to-dos
            Chip {
                id: runningChip
                objectName: "runningChip"
                visible: today.jobs.length > 0
                Layout.leftMargin: 4
                dot: "working"
                text: qsTr("%n running", "", today.jobs.length)
                Accessible.description: today.jobList
                onClicked: runningDrop.open()
                onVisibleChanged: if (!visible) runningDrop.close()
                Drop {
                    id: runningDrop
                    objectName: "runningDrop"
                    chip: runningChip
                    Txt { kind: "label"; text: qsTr("Working on"); Layout.leftMargin: Theme.pad; Layout.topMargin: 16; Layout.bottomMargin: 4 }
                    Repeater { model: today.jobs; JobRow {} }
                    Item { Layout.preferredHeight: 6 }
                }
            }
            Chip {
                id: todoChip
                objectName: "todoChip"
                visible: today.todoAll.length > 0
                symbol: "check"
                text: qsTr("%n to do", "", today.todoAll.length)
                onClicked: todoDrop.open()
                onVisibleChanged: if (!visible) todoDrop.close()
                Drop {
                    id: todoDrop
                    chip: todoChip
                    Txt { kind: "label"; text: qsTr("To do"); Layout.leftMargin: Theme.pad; Layout.topMargin: 16; Layout.bottomMargin: 4 }
                    Repeater { model: today.todoAll; TodoRow {} }
                    Item { Layout.preferredHeight: 6 }
                }
            }
            Rectangle { visible: !!today.media.title; Layout.preferredWidth: 1; Layout.preferredHeight: 20; Layout.leftMargin: 4; Layout.rightMargin: 4; color: Theme.stroke }
            Icon { visible: !!today.media.title; name: "music"; size: 16; Layout.preferredWidth: 16; Layout.preferredHeight: 16; color: Theme.accent }
            Txt { text: today.media.title || ""; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
            IconButton { visible: !!today.media.title; symbol: today.media.status === "Playing" ? "pause" : "play"; tint: Theme.accentSoft; iconColor: Theme.accent
                         size: 36; glyph: 16; onClicked: Api.post("/api/media/PlayPause", {}, today.live) }
        }
    }

    ColumnLayout {
        id: cards
        visible: !today.compact
        width: today.availableWidth
        spacing: 12

        // the time and the weather, on one line (the condition and how it feels in a tip)
        Card {
            id: clockCard
            Layout.fillWidth: true
            padding: 16
            readonly property string feels: !today.weather.temp ? "" : (today.weather.condition ? today.weather.condition + " · " : "")
                + (today.weather.place ? qsTr("Feels %1 in %2").arg(today.weather.feels || "").arg(today.weather.place) : qsTr("Feels %1").arg(today.weather.feels || ""))
            Accessible.role: Accessible.StaticText
            Accessible.name: [Qt.formatTime(today.now, "HH:mm"), today.now.toLocaleDateString(Qt.locale(), "dddd, d MMMM"), today.weather.temp || "", feels]
                             .filter(t => t).join(", ")
            RowLayout {
                width: parent.width
                spacing: 10
                Txt { text: Qt.formatTime(today.now, "HH:mm"); kind: "heading"; font.pixelSize: Theme.px(22); weight: 600; font.features: { "tnum": 1 }
                      wrapMode: Text.NoWrap }
                Txt { text: today.now.toLocaleDateString(Qt.locale(), "dddd, d MMM"); kind: "small"; wrapMode: Text.NoWrap; elide: Text.ElideRight
                      Layout.fillWidth: true }
                Icon { visible: !!today.weather.temp; name: today.sky(today.weather.condition); size: 18; Layout.preferredWidth: 18; Layout.preferredHeight: 18
                       color: name === "sun" ? Theme.accent : Theme.text2 }
                Txt { visible: !!today.weather.temp; text: today.weather.temp || ""; weight: 600; wrapMode: Text.NoWrap }
            }
            HoverHandler { id: sky }
            Tip { text: clockCard.feels; visible: sky.hovered && clockCard.feels !== "" }
        }

        // what's playing
        Card {
            Layout.fillWidth: true
            visible: !!today.media.title
            RowLayout {  // (art, words and controls on one line, centred on the art)
                width: parent.width
                spacing: 12
                Item {
                    Layout.preferredWidth: 56; Layout.preferredHeight: 56
                    Rectangle {
                        anchors.fill: parent; radius: 12; visible: art.status !== Image.Ready
                        border.width: 1; border.color: Theme.stroke
                        gradient: Gradient {
                            GradientStop { position: 0; color: Theme.accentSoft }
                            GradientStop { position: 1; color: "#0e1822" }
                        }
                        Icon { anchors.centerIn: parent; name: "music"; size: 22; color: Theme.accent }
                    }
                    Image {
                        id: art
                        anchors.fill: parent
                        source: today.media.art || ""
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: true
                        sourceSize: Qt.size(112, 112)
                        layer.enabled: status === Image.Ready
                        layer.effect: MultiEffect { maskEnabled: true; maskSource: artMask; maskThresholdMin: 0.5; maskSpreadAtMin: 1 }
                    }
                    Rectangle { id: artMask; anchors.fill: parent; radius: 12; visible: false; layer.enabled: true }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Txt { kind: "label"; text: qsTr("Now playing"); wrapMode: Text.NoWrap }
                        Txt { kind: "label"; color: Theme.text3; text: "· " + (today.media.app || ""); visible: !!today.media.app
                              Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                    }
                    Txt { text: today.media.title || ""; weight: 600; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                    Txt { kind: "small"; text: today.media.artist || today.media.app || ""; Layout.fillWidth: true; elide: Text.ElideRight
                          wrapMode: Text.NoWrap }
                }
                Row {
                    Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                    LayoutMirroring.enabled: false  // (media buttons keep their order in any language)
                    IconButton { anchors.verticalCenter: parent.verticalCenter; size: 28; glyph: 14; symbol: "prev"; tip: qsTr("Previous")
                                 onClicked: Api.post("/api/media/Previous", {}, today.live) }
                    IconButton { symbol: today.media.status === "Playing" ? "pause" : "play"; tint: Theme.accentSoft; iconColor: Theme.accent; size: 36; glyph: 16
                                 onClicked: Api.post("/api/media/PlayPause", {}, today.live) }
                    IconButton { anchors.verticalCenter: parent.verticalCenter; size: 28; glyph: 14; symbol: "next"; tip: qsTr("Next")
                                 onClicked: Api.post("/api/media/Next", {}, today.live) }
                }
            }
        }

        // what Jarvis is working on: each task that's running, and Stop for that one only
        Card {
            Layout.fillWidth: true
            visible: today.jobs.length > 0 || today.finished.length > 0
            padding: 0
            ColumnLayout {
                width: parent.width
                spacing: 0
                Txt { kind: "label"; text: today.jobs.length ? qsTr("Working on") : qsTr("Finished lately")
                      Layout.leftMargin: Theme.pad; Layout.topMargin: 16; Layout.bottomMargin: 4 }
                Repeater { model: today.jobs; JobRow {} }
                Repeater {  // (what a longer task answered, so it isn't lost in the chat once it's off "Working on"; click: all of it)
                    model: today.finished
                    AbstractButton {
                        id: ended
                        required property var modelData
                        required property int index
                        readonly property bool open: !!today.opened[modelData.n]
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.max(56, endedText.height + 20)
                        hoverEnabled: true
                        focusPolicy: Qt.TabFocus
                        Keys.onReturnPressed: click()
                        Keys.onEnterPressed: click()
                        Accessible.role: Accessible.Button
                        Accessible.name: modelData.label
                        Accessible.description: modelData.answer || ""
                        Accessible.checkable: true
                        Accessible.checked: open
                        onClicked: { const o = Object.assign({}, today.opened); o[modelData.n] = !open; today.opened = o }
                        leftInset: 8; rightInset: 8; topInset: 2; bottomInset: 2
                        background: Rectangle {
                            radius: Theme.radiusControl
                            color: ended.hovered ? Theme.glassHover : "transparent"
                            Behavior on color { ColorAnimation { duration: Theme.fast } }
                            Focus { keyboard: true; visible: ended.visualFocus }
                        }
                        Rectangle { visible: ended.index > 0 || today.jobs.length > 0; x: Theme.pad; width: parent.width - 2 * Theme.pad; height: 1; color: Theme.stroke }
                        Rectangle {
                            id: endedWell
                            anchors { left: parent.left; leftMargin: Theme.pad; verticalCenter: parent.verticalCenter }
                            width: 36; height: 36; radius: 18
                            color: ended.modelData.ok ? Theme.accentSoft : Theme.warmSoft
                            Icon { anchors.centerIn: parent; name: ended.modelData.ok ? "check" : "alert"; size: 18
                                   color: ended.modelData.ok ? Theme.accent : Theme.warm }
                        }
                        Column {
                            id: endedText
                            anchors { left: endedWell.right; leftMargin: 12; right: parent.right; rightMargin: Theme.pad; verticalCenter: parent.verticalCenter }
                            spacing: 1
                            Txt { text: ended.modelData.label; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                            Txt { kind: "small"; width: parent.width; elide: Text.ElideRight; maximumLineCount: ended.open ? 40 : 2; wrapMode: Text.Wrap
                                  color: ended.modelData.ok ? Theme.text2 : Theme.warm
                                  text: qsTr("Finished at %1").arg(Qt.formatDateTime(new Date(ended.modelData.at * 1000), "HH:mm"))
                                        + (ended.modelData.answer ? " · " + ended.modelData.answer : "") }
                        }
                    }
                }
                Item { Layout.preferredHeight: 6 }
            }
        }

        // what's next: everything to do this week, from Google Tasks, reminders, promises and Classroom (only reminders
        // until that list arrives: it reads the accounts, so it's fetched when Home shows and every 10 minutes)
        Card {
            Layout.fillWidth: true
            padding: 0
            ColumnLayout {
                width: parent.width
                spacing: 0
                Txt { kind: "label"; text: qsTr("To do"); Layout.leftMargin: Theme.pad; Layout.topMargin: 16; Layout.bottomMargin: 4 }
                Txt { kind: "small"; color: Theme.text3; text: qsTr("Nothing to do this week. Try “remind me in 20 minutes to stretch”.")
                      visible: !today.todoRows.length; Layout.fillWidth: true; Layout.margins: Theme.pad; Layout.topMargin: 4 }
                Repeater { model: today.todoRows; TodoRow {} }
                Pill {  // the items left out: here, in place
                    visible: today.todoAll.length > 5
                    Layout.leftMargin: Theme.pad - 12; Layout.topMargin: 2
                    kind: "ghost"; implicitHeight: 32
                    symbol: today.todoOpen ? "" : "chevron"
                    text: today.todoOpen ? qsTr("Show fewer") : qsTr("+%n more", "", today.todoAll.length - 5)
                    onClicked: today.todoOpen = !today.todoOpen
                }
                Txt { kind: "small"; color: Theme.text3; visible: !!today.todo && today.todo.couldnt_check.length > 0
                      text: qsTr("Couldn't check %1 just now.").arg(today.todo ? today.todo.couldnt_check.join(", ") : "")
                      Layout.fillWidth: true; Layout.leftMargin: Theme.pad; Layout.rightMargin: Theme.pad; Layout.topMargin: 4 }
                Item { Layout.preferredHeight: 6 }
            }
        }

        // the PC
        Card {
            Layout.fillWidth: true
            visible: today.stats.mem_total !== undefined
            ColumnLayout {
                width: parent.width
                spacing: 14
                Txt { kind: "label"; text: qsTr("This PC") }
                Meter { label: qsTr("Processor"); value: (today.stats.cpu || 0) / 100; detail: Math.round(today.stats.cpu || 0) + "%" }
                Meter { label: qsTr("Memory"); value: (today.stats.mem_used || 0) / Math.max(1, today.stats.mem_total || 1)
                        detail: qsTr("%1 of %2 GB").arg(today.gb(today.stats.mem_used || 0)).arg(today.gb(today.stats.mem_total || 0)) }
                Meter { label: qsTr("Disk"); value: (today.stats.disk_used || 0) / Math.max(1, today.stats.disk_total || 1)
                        detail: qsTr("%1 GB free").arg(Math.round((today.stats.disk_total - today.stats.disk_used) / 1073741824)) }
            }
        }

        // how fast Jarvis answered
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 8; Layout.rightMargin: 8
            spacing: 8
            visible: today.latency >= 0
            Icon { name: "bolt"; size: 14; Layout.preferredWidth: 14; Layout.preferredHeight: 14; color: Theme.text3 }
            Txt { kind: "small"; color: Theme.text3; Layout.fillWidth: true; font.features: { "tnum": 1 }
                  text: qsTr("Last answer started %1 s after you finished").arg(today.latency.toFixed(1)) }
        }
        Item { Layout.preferredHeight: 12 }
    }

    // a task at work, with Stop for that one only (in the "Working on" card, or a narrow window's list under its chip)
    component JobRow: Item {
        id: job
        required property var modelData
        required property int index
        Layout.fillWidth: true
        Layout.preferredHeight: Math.max(56, jobText.height + 20)  // (a long request takes two lines)
        Rectangle { visible: job.index > 0; x: Theme.pad; width: parent.width - 2 * Theme.pad; height: 1; color: Theme.stroke }
        Rectangle {
            id: jobWell
            anchors { left: parent.left; leftMargin: Theme.pad; verticalCenter: parent.verticalCenter }
            width: 36; height: 36; radius: 18
            color: Theme.warmSoft
            Icon { anchors.centerIn: parent; name: job.modelData.coding ? "cpu" : "bolt"; size: 18; color: Theme.warm }
        }
        Column {
            id: jobText
            anchors { left: jobWell.right; leftMargin: 12; right: stopJob.left; rightMargin: 4; verticalCenter: parent.verticalCenter }
            spacing: 1
            Txt { text: job.modelData.label; width: parent.width; elide: Text.ElideRight; maximumLineCount: 2 }
            Txt { kind: "small"; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap; font.features: { "tnum": 1 }
                  text: today.clock(today.now.getTime() / 1000 - job.modelData.since)
                        + (job.modelData.now ? " · " + Backend.toolLabel(job.modelData.now) : "") }
        }
        IconButton {
            id: stopJob
            anchors { right: parent.right; rightMargin: 12; verticalCenter: parent.verticalCenter }
            size: 28; glyph: 14; symbol: "close"; tip: qsTr("Stop this task")
            onClicked: Api.post(`/api/jobs/${job.modelData.n}/stop`, {}, today.live)
        }
    }

    // something to do, with its action (in the "To do" card, or a narrow window's list under its chip)
    component TodoRow: Item {
        id: row
        required property var modelData
        required property int index
        readonly property bool late: !!modelData.due && modelData.due * 1000 < today.now.getTime()
        Layout.fillWidth: true
        Layout.preferredHeight: 56
        HoverHandler { id: over }
        Rectangle { visible: row.index > 0; x: Theme.pad; width: parent.width - 2 * Theme.pad; height: 1; color: Theme.stroke }
        Rectangle {
            id: well
            anchors { left: parent.left; leftMargin: Theme.pad; verticalCenter: parent.verticalCenter }
            width: 36; height: 36; radius: 18
            color: row.late ? Theme.warmSoft : Theme.accentSoft
            Icon { anchors.centerIn: parent; size: 18; color: row.late ? Theme.warm : Theme.accent
                   name: ({ task: "check", promise: "accounts", classroom: "calendar" })[row.modelData.kind] || "bell" }
        }
        Column {
            anchors { left: well.right; leftMargin: 12; right: rowAction.left; rightMargin: 4; verticalCenter: parent.verticalCenter }
            spacing: 1
            Txt { text: row.modelData.what; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap }
            Txt { kind: "small"; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap
                  color: row.late ? Theme.warm : Theme.text2
                  text: [row.modelData.when !== undefined ? String(row.modelData.when).replace(/^./, ch => ch.toUpperCase())
                         : !row.modelData.due ? (row.modelData.kind === "promise" ? "" : qsTr("No date"))
                         : row.late ? qsTr("Overdue since %1").arg(Qt.formatDateTime(new Date(row.modelData.due * 1000), "ddd d MMM"))
                         : today.when(row.modelData.due),
                         row.modelData.kind === "promise" ? qsTr("Promised to %1").arg(row.modelData.place || "")
                         : row.modelData.kind === "classroom" ? row.modelData.place || "" : ""].filter(x => x).join(" · ") }
        }
        Item {  // a promise: Done (it ends, with its reminder); Classroom work: open it; a reminder: cancel it, in two clicks
            id: rowAction
            readonly property bool promise: row.modelData.kind === "promise"
            readonly property bool cancels: !promise && !row.modelData.link && !!row.modelData.id
            anchors { right: parent.right; rightMargin: 12; verticalCenter: parent.verticalCenter }
            width: 28; height: 28
            visible: promise || !!row.modelData.link || cancels
            opacity: over.hovered || act.activeFocus || cancel.activeFocus || cancel.armed ? 1 : 0  // (Tab reaches it: it shows then too)
            Behavior on opacity { NumberAnimation { duration: Theme.fast } }
            IconButton {
                id: act
                visible: !rowAction.cancels
                size: 28; glyph: 14
                symbol: rowAction.promise ? "check" : "external"
                tip: rowAction.promise ? qsTr("Mark as done") : qsTr("Open in Classroom")
                onClicked: {
                    if (rowAction.promise)
                        Api.post("/api/promises/done", { to: row.modelData.place, what: row.modelData.what }, () => { today.load(); today.loadTodo() })
                    else
                        Qt.openUrlExternally(row.modelData.link)
                }
            }
            ConfirmButton {
                id: cancel
                visible: rowAction.cancels
                size: 28; glyph: 14; idleSymbol: "close"
                label: qsTr("Cancel this reminder"); again: qsTr("Click again to cancel it")
                onConfirmed: Api.post(`/api/reminders/${row.modelData.id}/cancel`, {}, () => { today.load(); today.loadTodo() })
            }
        }
    }

    // a narrow window's list under its chip, in the menus' glass: the rows go in a column, as in the side column's cards
    component Drop: Popup {
        id: drop
        default property alias rows: box.data
        required property Item chip
        x: chip.mirrored ? chip.width - width : 0  // (it opens toward the end of the strip, either way round)
        y: chip.height + 10
        width: 360
        height: Math.min(implicitHeight, 420)
        padding: 0
        margins: 12
        focus: true
        background: Glass { floating: true; color: Theme.popover; radius: Theme.radius; border.color: Theme.strokeStrong }
        contentItem: ScrollView {
            implicitHeight: box.implicitHeight
            contentWidth: availableWidth
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical: Scroller {}
            ColumnLayout {
                id: box
                width: drop.availableWidth
                spacing: 0
            }
        }
        enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.fast } }
    }

    component Meter: ColumnLayout {
        property string label
        property string detail
        property real value
        Layout.fillWidth: true
        spacing: 7
        RowLayout {
            Layout.fillWidth: true
            Txt { text: label; font.pixelSize: Theme.px(13); Layout.fillWidth: true }
            Txt { kind: "small"; text: detail; font.features: { "tnum": 1 } }
        }
        Rectangle {
            Layout.fillWidth: true
            height: 4; radius: 2
            color: Theme.track
            Rectangle {
                anchors.left: parent.left
                width: parent.width * Math.min(1, Math.max(0.02, value)); height: parent.height; radius: 2
                color: value > 0.8 ? Theme.warm : Theme.accent
                Behavior on width { NumberAnimation { duration: 400; easing.type: Easing.OutCubic } }
            }
        }
    }
}
