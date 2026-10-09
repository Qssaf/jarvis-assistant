import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Jarvis

// Today at a glance: the time and weather, what's playing, what's next, and how the PC is doing.
ScrollView {
    id: today
    property real latency: -1
    signal wake(string phrase)
    property var info: ({})
    property var media: ({})
    property var stats: ({})
    property var now: new Date()
    readonly property bool shown: visible && Window.window !== null && Window.window.visible
    contentWidth: availableWidth
    clip: true
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

    function load() { Api.get("/api/today", t => { info = t; wake(t.wake || "Hey Jarvis") }) }
    function live() {
        Api.get("/api/media", d => media = d)
        Api.get("/api/system", d => stats = d)
    }
    function gb(bytes) { return (bytes / 1073741824).toFixed(1) }
    Component.onCompleted: { load(); live() }
    Timer { interval: 60000; running: true; repeat: true; onTriggered: today.load() }
    Timer { interval: 3000; running: today.shown; repeat: true; triggeredOnStart: true; onTriggered: today.live() }
    Timer { interval: 1000; running: today.shown; repeat: true; triggeredOnStart: true; onTriggered: today.now = new Date() }
    Connections {
        target: Backend
        function onEvent(json) { if (JSON.parse(json).kind === "log" && json.indexOf("Reminder") >= 0) today.load() }
    }

    ColumnLayout {
        width: today.availableWidth
        spacing: 12
        Item { Layout.preferredHeight: 2 }

        // the time and the weather
        ColumnLayout {
            Layout.leftMargin: 20; Layout.rightMargin: 20
            spacing: 0
            Txt { text: Qt.formatTime(today.now, "HH:mm"); font.pixelSize: 44; font.weight: Font.Bold; font.letterSpacing: -1.5 }
            Txt { text: Qt.formatDate(today.now, "dddd, d MMMM"); kind: "small"; font.pixelSize: 13 }
        }
        Card {
            Layout.fillWidth: true; Layout.leftMargin: 14; Layout.rightMargin: 14
            visible: !!today.info.weather
            RowLayout {
                width: parent.width
                spacing: 12
                Text { text: (today.info.weather || {}).icon || ""; font.pixelSize: 30 }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 1
                    Txt { text: ((today.info.weather || {}).temp || "") + " · " + ((today.info.weather || {}).condition || ""); font.weight: Font.DemiBold
                            Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                    Txt { kind: "small"; text: "Feels " + ((today.info.weather || {}).feels || "") + " in " + ((today.info.weather || {}).place || "")
                            Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                }
            }
        }

        // what's playing
        Card {
            Layout.fillWidth: true; Layout.leftMargin: 14; Layout.rightMargin: 14
            visible: !!today.media.title
            ColumnLayout {
                width: parent.width
                spacing: 12
                RowLayout {
                    spacing: 12
                    Rectangle {
                        Layout.preferredWidth: 52; Layout.preferredHeight: 52
                        radius: 12
                        color: Theme.raised
                        clip: true
                        Icon { anchors.centerIn: parent; name: "music"; size: 22; color: Theme.dim; visible: art.status !== Image.Ready }
                        Image { id: art; anchors.fill: parent; source: today.media.art || ""; fillMode: Image.PreserveAspectCrop; asynchronous: true
                                sourceSize: Qt.size(104, 104) }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Txt { text: today.media.title || ""; font.weight: Font.DemiBold; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                        Txt { kind: "small"; text: today.media.artist || today.media.app || ""; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                    }
                }
                RowLayout {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 10
                    IconButton { symbol: "prev"; glyph: 16; onClicked: Api.post("/api/media/Previous", {}, today.live) }
                    IconButton { symbol: today.media.status === "Playing" ? "pause" : "play"; tint: Theme.text; size: 40
                                 onClicked: Api.post("/api/media/PlayPause", {}, today.live) }
                    IconButton { symbol: "next"; glyph: 16; onClicked: Api.post("/api/media/Next", {}, today.live) }
                }
            }
        }

        // what's next
        Card {
            Layout.fillWidth: true; Layout.leftMargin: 14; Layout.rightMargin: 14
            ColumnLayout {
                width: parent.width
                spacing: 8
                Txt { kind: "caps"; text: "Up next" }
                Txt { kind: "small"; text: "Nothing scheduled. Try “remind me in 20 minutes to stretch”."; visible: !(today.info.reminders || []).length
                        Layout.fillWidth: true }
                Repeater {
                    model: today.info.reminders || []
                    RowLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 10
                        Rectangle { Layout.preferredWidth: 4; Layout.preferredHeight: 30; radius: 2; color: Theme.accent }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0
                            Txt { text: modelData.text; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap; font.pixelSize: 14 }
                            Txt { kind: "small"; text: modelData.when }
                        }
                        IconButton { symbol: "close"; size: 28; glyph: 13; tip: "Cancel this reminder"
                                     onClicked: Api.post(`/api/reminders/${modelData.id}/cancel`, {}, today.load) }
                    }
                }
            }
        }

        // the PC
        Card {
            Layout.fillWidth: true; Layout.leftMargin: 14; Layout.rightMargin: 14
            visible: today.stats.mem_total !== undefined
            ColumnLayout {
                width: parent.width
                spacing: 10
                Txt { kind: "caps"; text: "This PC" }
                Meter { label: "Processor"; value: (today.stats.cpu || 0) / 100; detail: Math.round(today.stats.cpu || 0) + "%" }
                Meter { label: "Memory"; value: (today.stats.mem_used || 0) / Math.max(1, today.stats.mem_total || 1)
                        detail: today.gb(today.stats.mem_used || 0) + " of " + today.gb(today.stats.mem_total || 0) + " GB" }
                Meter { label: "Disk"; value: (today.stats.disk_used || 0) / Math.max(1, today.stats.disk_total || 1)
                        detail: Math.round((today.stats.disk_total - today.stats.disk_used) / 1073741824) + " GB free" }
            }
        }

        // how fast Jarvis answered
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20; Layout.rightMargin: 20
            spacing: 8
            visible: today.latency >= 0
            Icon { name: "bolt"; size: 15; color: Theme.listen }
            Txt { kind: "small"; Layout.fillWidth: true; text: "Last answer started " + today.latency.toFixed(1) + " s after you finished" }
        }
        Item { Layout.preferredHeight: 12 }
    }

    component Meter: ColumnLayout {
        property string label
        property string detail
        property real value
        Layout.fillWidth: true
        spacing: 5
        RowLayout {
            Layout.fillWidth: true
            Txt { text: label; font.pixelSize: 13; Layout.fillWidth: true }
            Txt { kind: "small"; text: detail }
        }
        Rectangle {
            Layout.fillWidth: true
            height: 5; radius: 3
            color: Theme.raised
            Rectangle {
                width: parent.width * Math.min(1, Math.max(0.02, value)); height: parent.height; radius: 3
                color: value > 0.85 ? Theme.red : value > 0.65 ? Theme.warm : Theme.accent
                Behavior on width { NumberAnimation { duration: 400; easing.type: Easing.OutCubic } }
            }
        }
    }
}
