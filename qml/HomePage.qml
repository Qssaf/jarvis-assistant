import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Jarvis

// The conversation (or, before it starts, Jarvis's orb and some ideas), the message box, and today at a glance.
Item {
    id: home
    property var attachments: []
    property string wake: "Hey Jarvis"
    property real latency: -1

    function reload() {
        Api.get("/api/conversation", c => {
            messages.clear()
            for (const m of c.messages) add(m)
            list.positionViewAtEnd()
        })
    }
    function add(m) {
        if (!["you", "jarvis", "tool", "system", "thinking", "image"].includes(m.who)) return
        messages.append({ who: m.who, text: String(m.text || ""), caption: String(m.caption || ""), time: m.time || Date.now() / 1000 })
    }
    function send(text) {
        text = text.trim()
        if (!text && !attachments.length) return
        const note = attachments.map(p => `(attached: ${p})`).join(" ")
        Backend.send((text + " " + note).trim())
        attachments = []
    }
    Component.onCompleted: reload()

    ListModel { id: messages }
    Connections {
        target: Backend
        function onEvent(json) {
            const e = JSON.parse(json)
            if (e.kind === "log") {
                const atEnd = list.atYEnd || list.contentHeight < list.height
                home.add(e)
                if (atEnd) Qt.callLater(list.positionViewAtEnd)
            } else if (e.kind === "latency") home.latency = e.seconds
        }
    }

    DropArea {
        anchors.fill: parent
        onDropped: drop => { home.attachments = home.attachments.concat(drop.urls.map(u => decodeURIComponent(String(u).replace("file://", "")))) }
    }
    FileDialog {
        id: picker
        fileMode: FileDialog.OpenFiles
        title: "Attach files for Jarvis"
        onAccepted: home.attachments = home.attachments.concat(selectedFiles.map(u => decodeURIComponent(String(u).replace("file://", ""))))
    }

    RowLayout {
        anchors.fill: parent
        anchors.topMargin: 46
        spacing: 0

        // ---- the conversation
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Item {  // before anything is said: the orb, a greeting and some ideas
                id: hero
                anchors { left: parent.left; right: parent.right; top: parent.top; bottom: composer.top }
                visible: messages.count === 0
                opacity: visible ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: 250 } }

                Column {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 64, 720)
                    spacing: 6
                    Orb {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 210; height: 210
                        mode: Backend.state
                        level: Backend.level
                        TapHandler { onTapped: Backend.talk() }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                    }
                    Item { width: 1; height: 14 }
                    Txt {
                        anchors.horizontalCenter: parent.horizontalCenter
                        kind: "title"
                        font.pixelSize: 30
                        text: Backend.state === "idle" ? greeting() : Theme.stateName(Backend.state) + "…"
                        function greeting() {
                            const h = new Date().getHours()
                            return h < 5 ? "Up late?" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening"
                        }
                    }
                    Txt {
                        anchors.horizontalCenter: parent.horizontalCenter
                        kind: "small"
                        font.pixelSize: 14
                        text: Backend.state === "idle" ? `Say “${home.wake}”, tap the orb, or type below`
                            : Backend.state === "listening" ? (Backend.listening ? "Go ahead, I'm listening" : "Paused")
                            : Backend.state === "speaking" ? `Say “${home.wake}” to cut in` : "On it"
                    }
                    Item { width: 1; height: 26 }
                    GridLayout {
                        width: parent.width
                        columns: width > 620 ? 3 : 2
                        rowSpacing: 10
                        columnSpacing: 10
                        Repeater {
                            model: [["sun", "Good morning", "Your day at a glance"], ["calendar", "What's due this week?", "From Google Classroom"],
                                    ["mail", "Any new emails?", "Your Gmail inbox"], ["screen", "What's on my screen?", "Jarvis takes a look"],
                                    ["timer", "Set a 10 minute timer", "With a notification"], ["image", "Paint a rainy city", "Make a picture"]]
                            Suggestion { required property var modelData; Layout.fillWidth: true; symbol: modelData[0]; title: modelData[1]; hint: modelData[2] }
                        }
                    }
                }
            }

            ListView {
                id: list
                anchors { left: parent.left; right: parent.right; top: parent.top; bottom: composer.top; bottomMargin: 8 }
                visible: messages.count > 0
                clip: true
                model: messages
                spacing: 6
                topMargin: 48
                bottomMargin: 12
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                delegate: Message { width: ListView.view.width }
            }

            Row {
                anchors { top: parent.top; right: parent.right; topMargin: 6; rightMargin: 22 }
                visible: messages.count > 0
                z: 10
                spacing: 8

                Pill {
                    text: "New chat"
                    symbol: "plus"
                    onClicked: Api.post("/api/new", {}, () => home.reload())
                }
            }

            Composer {
                id: composer
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 22; topMargin: 0 }
                attachments: home.attachments
                onSubmitted: text => home.send(text)
                onAttach: picker.open()
                onRemoved: path => home.attachments = home.attachments.filter(p => p !== path)
            }
        }

        Rectangle { Layout.fillHeight: true; Layout.preferredWidth: 1; color: Theme.line; visible: today.visible }

        Today {
            id: today
            Layout.preferredWidth: 300
            Layout.minimumWidth: 300
            Layout.maximumWidth: 300
            Layout.fillHeight: true
            visible: home.width > 1000
            latency: home.latency
            onWake: phrase => home.wake = phrase
        }
    }

    component Suggestion: AbstractButton {
        id: s
        property string symbol
        property string title
        property string hint
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        implicitHeight: 84
        onClicked: Backend.send(title)
        background: Rectangle {
            radius: Theme.radius
            color: s.hovered ? Theme.cardHover : Theme.card
            border.width: 1
            border.color: s.hovered ? Theme.alpha(Theme.accent, 0.45) : Theme.line
            Behavior on color { ColorAnimation { duration: 140 } }
            Behavior on border.color { ColorAnimation { duration: 140 } }
        }
        contentItem: Item {
            Rectangle {
                id: badge
                x: 14; anchors.verticalCenter: parent.verticalCenter
                width: 36; height: 36; radius: 11
                color: Theme.alpha(Theme.accent, s.hovered ? 0.22 : 0.13)
                Icon { anchors.centerIn: parent; name: s.symbol; size: 18; color: Theme.accent }
            }
            Column {
                anchors { left: badge.right; leftMargin: 12; right: parent.right; rightMargin: 12; verticalCenter: parent.verticalCenter }
                spacing: 3
                Txt { text: s.title; width: parent.width; font.weight: Font.DemiBold; font.pixelSize: 14; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                Txt { text: s.hint; kind: "small"; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap }
            }
        }
        scale: down ? 0.98 : 1
        Behavior on scale { NumberAnimation { duration: 90 } }
    }
}
