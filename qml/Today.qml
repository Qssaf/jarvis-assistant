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
    property var now: new Date()
    readonly property var weather: info.weather || {}
    readonly property bool shown: visible && Window.window !== null && Window.window.visible
    contentWidth: availableWidth
    contentHeight: compact ? strip.implicitHeight : cards.implicitHeight
    clip: true
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical: Scroller { parent: today; x: today.width - width; height: today.availableHeight }

    function load() { Api.get("/api/today", t => { info = t; wake(t.wake || "Hey Jarvis") }) }
    function live() {
        Api.get("/api/media", d => media = d)
        Api.get("/api/system", d => stats = d)
    }
    function gb(bytes) { return (bytes / 1073741824).toFixed(1) }
    function sky(c) {  // a line icon for wttr.in's condition (its emoji clash with the icon set)
        c = String(c).toLowerCase()
        return /thunder/.test(c) ? "bolt" : /sun/.test(c) ? "sun" : /clear/.test(c) ? (today.now.getHours() < 6 || today.now.getHours() >= 19 ? "moon" : "sun") : "cloud"
    }
    Component.onCompleted: { load(); live() }
    Timer { interval: 60000; running: true; repeat: true; onTriggered: today.load() }
    Timer { interval: 3000; running: today.shown; repeat: true; triggeredOnStart: true; onTriggered: today.live() }
    Timer { interval: 1000; running: today.shown; repeat: true; triggeredOnStart: true; onTriggered: today.now = new Date() }
    Connections {
        target: Backend
        function onEvent(json) { if (JSON.parse(json).kind === "log" && json.indexOf("Reminder") >= 0) today.load() }
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

        // the time and the weather
        Card {
            Layout.fillWidth: true
            ColumnLayout {
                width: parent.width
                spacing: 16
                ColumnLayout {
                    spacing: 2
                    Txt { text: Qt.formatTime(today.now, "HH:mm"); font.pixelSize: Theme.px(48); weight: 600; font.letterSpacing: -2
                          font.features: { "tnum": 1 }; lineHeight: 0.95 }
                    Txt { text: Qt.formatDate(today.now, "dddd, d MMMM"); kind: "small" }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.stroke; visible: !!today.weather.temp }
                RowLayout {
                    visible: !!today.weather.temp
                    spacing: 12
                    Icon { name: today.sky(today.weather.condition); size: 24; Layout.preferredWidth: 24; Layout.preferredHeight: 24; color: name === "sun" ? Theme.accent : Theme.text2 }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1
                        Txt { text: today.weather.condition || ""; weight: 600; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                        Txt { kind: "small"; text: "Feels " + (today.weather.feels || "") + " in " + (today.weather.place || "")
                              Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                    }
                    Txt { text: today.weather.temp || ""; kind: "heading"; font.pixelSize: Theme.px(22); weight: 500; wrapMode: Text.NoWrap }
                }
            }
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
                        Txt { kind: "label"; text: "Now playing"; wrapMode: Text.NoWrap }
                        Txt { kind: "label"; color: Theme.text3; text: "· " + (today.media.app || ""); visible: !!today.media.app
                              Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                    }
                    Txt { text: today.media.title || ""; weight: 600; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                    Txt { kind: "small"; text: today.media.artist || today.media.app || ""; Layout.fillWidth: true; elide: Text.ElideRight
                          wrapMode: Text.NoWrap }
                }
                Row {
                    Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                    IconButton { anchors.verticalCenter: parent.verticalCenter; size: 28; glyph: 14; symbol: "prev"; tip: "Previous"
                                 onClicked: Api.post("/api/media/Previous", {}, today.live) }
                    IconButton { symbol: today.media.status === "Playing" ? "pause" : "play"; tint: Theme.accentSoft; iconColor: Theme.accent; size: 36; glyph: 16
                                 onClicked: Api.post("/api/media/PlayPause", {}, today.live) }
                    IconButton { anchors.verticalCenter: parent.verticalCenter; size: 28; glyph: 14; symbol: "next"; tip: "Next"
                                 onClicked: Api.post("/api/media/Next", {}, today.live) }
                }
            }
        }

        // what's next
        Card {
            Layout.fillWidth: true
            padding: 0
            ColumnLayout {
                width: parent.width
                spacing: 0
                Txt { kind: "label"; text: "Up next"; Layout.leftMargin: Theme.pad; Layout.topMargin: 16; Layout.bottomMargin: 4 }
                Txt { kind: "small"; color: Theme.text3; text: "Nothing scheduled. Try “remind me in 20 minutes to stretch”."
                      visible: !(today.info.reminders || []).length; Layout.fillWidth: true; Layout.margins: Theme.pad; Layout.topMargin: 4 }
                Repeater {
                    model: today.info.reminders || []
                    Item {
                        id: row
                        required property var modelData
                        required property int index
                        Layout.fillWidth: true
                        Layout.preferredHeight: 56
                        HoverHandler { id: over }
                        Rectangle { visible: row.index > 0; x: Theme.pad; width: parent.width - 2 * Theme.pad; height: 1; color: Theme.stroke }
                        Rectangle {
                            id: well
                            x: Theme.pad; anchors.verticalCenter: parent.verticalCenter
                            width: 36; height: 36; radius: 18
                            color: Theme.accentSoft
                            Icon { anchors.centerIn: parent; name: "bell"; size: 18; color: Theme.accent }
                        }
                        Column {
                            anchors { left: well.right; leftMargin: 12; right: cancel.left; rightMargin: 4; verticalCenter: parent.verticalCenter }
                            spacing: 1
                            Txt { text: row.modelData.text; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                            Txt { kind: "small"; text: String(row.modelData.when).replace(/^./, ch => ch.toUpperCase()); width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                        }
                        IconButton {
                            id: cancel
                            anchors { right: parent.right; rightMargin: 12; verticalCenter: parent.verticalCenter }
                            opacity: over.hovered ? 1 : 0
                            Behavior on opacity { NumberAnimation { duration: Theme.fast } }
                            size: 28; glyph: 14; symbol: "close"; tip: "Cancel this reminder"
                            onClicked: Api.post(`/api/reminders/${row.modelData.id}/cancel`, {}, today.load)
                        }
                    }
                }
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
                Txt { kind: "label"; text: "This PC" }
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
            Layout.leftMargin: 8; Layout.rightMargin: 8
            spacing: 8
            visible: today.latency >= 0
            Icon { name: "bolt"; size: 14; Layout.preferredWidth: 14; Layout.preferredHeight: 14; color: Theme.text3 }
            Txt { kind: "small"; color: Theme.text3; Layout.fillWidth: true; font.features: { "tnum": 1 }
                  text: "Last answer started " + today.latency.toFixed(1) + " s after you finished" }
        }
        Item { Layout.preferredHeight: 12 }
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
                width: parent.width * Math.min(1, Math.max(0.02, value)); height: parent.height; radius: 2
                color: value > 0.8 ? Theme.warm : Theme.accent
                Behavior on width { NumberAnimation { duration: 400; easing.type: Easing.OutCubic } }
            }
        }
    }
}
