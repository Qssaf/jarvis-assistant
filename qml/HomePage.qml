import QtQuick
import QtQuick.Controls
import Jarvis

// The conversation (or, before it starts, Jarvis's reactor and some ideas), the message box, and today at a glance.
Item {
    id: home
    property string wake: "Hey Jarvis"
    property real latency: -1
    readonly property bool wide: width > 1000  // (narrower, today folds into a strip above the conversation)
    // (from the page's width, not talk's: talk ends where today begins, and today's margins are worked out from the column)
    readonly property real column: Math.min(760, (wide ? width - 300 - 12 - 8 : width) - 2 * Theme.margin)
    signal goTo(string key)  // another page: Accounts, from the idea to connect them
    // the ideas before anything is said: the accounts' own only once they're connected (null: not known yet, so neither
    // those nor the one to connect them)
    readonly property var connected: today.info.connected || null
    readonly property var ideas: {
        const has = slug => !!connected && connected.includes(slug)
        return [["sun", qsTr("Brief me"), qsTr("Weather and your schedule")]]
            .concat(connected && !["gmail", "googlecalendar", "google_classroom"].some(has)
                    ? [["accounts", qsTr("Connect your accounts"), qsTr("Gmail, Calendar, Classroom"), "accounts"]] : [])
            .concat(has("google_classroom") ? [["calendar", qsTr("What's due this week?"), qsTr("From Google Classroom")]] : [])
            .concat(has("gmail") ? [["mail", qsTr("Any new emails?"), qsTr("Your Gmail inbox")]] : [])
            .concat([["screen", qsTr("What's on my screen?"), qsTr("Jarvis takes a look")],
                     ["timer", qsTr("Set a 10 minute timer"), qsTr("With a notification")], ["image", qsTr("Paint a rainy city"), qsTr("Make a picture")]])
    }

    function reload() {
        Api.get("/api/conversation", c => {
            list.model = null  // (refilled detached, so a reload doesn't animate every message in)
            messages.clear()
            for (const m of c.messages) add(m)
            list.model = messages
            list.positionViewAtEnd()
        })
    }
    function add(m) {
        if (!["you", "jarvis", "tool", "system", "thinking", "image"].includes(m.who)) return
        messages.append({ who: m.who, text: String(m.text || ""), caption: String(m.caption || ""), time: m.time || Date.now() / 1000 })
    }
    function send(text, files) {  // (files go as "(attached: path)" notes: the agent reads them so)
        if (text.trim() || files.length)
            Backend.send(Backend.withAttached(text, files))
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

    // ---- the conversation
    Item {
        id: talk
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom; right: home.wide ? today.left : parent.right
                  rightMargin: home.wide ? 8 : 0 }

        Item {  // before anything is said: the reactor, a greeting and some ideas
            id: hero
            anchors { left: parent.left; right: parent.right; top: parent.top; topMargin: home.wide ? 46 : 116; bottom: composer.top; bottomMargin: 12 }
            visible: messages.count === 0
            opacity: visible ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: 250 } }

            Column {
                anchors.centerIn: parent
                width: home.column
                Orb {
                    anchors.horizontalCenter: parent.horizontalCenter
                    // (the outer ring is 84% of the item: 262 gives a ~220 px reactor, smaller only when the height is short)
                    width: Math.max(130, Math.min(262, hero.height - ideas.height - 150)); height: width
                    mode: Backend.state
                    level: Backend.level
                    TapHandler { onTapped: Backend.talk() }
                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                }
                Item { width: 1; height: 20 }
                Txt {
                    anchors.horizontalCenter: parent.horizontalCenter
                    kind: "display"
                    text: Backend.state === "idle" ? greeting() : Theme.stateName(Backend.state) + "…"
                    function greeting() {
                        const h = new Date().getHours()
                        return h < 5 ? qsTr("Up late?") : h < 12 ? qsTr("Good morning") : h < 18 ? qsTr("Good afternoon") : qsTr("Good evening")
                    }
                }
                Item { width: 1; height: 8 }
                Txt {
                    anchors.horizontalCenter: parent.horizontalCenter
                    color: Theme.text2
                    font.pixelSize: Theme.px(15)
                    text: Backend.state === "idle" ? qsTr("Say “%1”, tap the reactor, or type below").arg(home.wake)
                        : Backend.state === "listening" ? (Backend.listening ? qsTr("Go ahead, I'm listening") : qsTr("Paused"))
                        : Backend.state === "speaking" ? qsTr("Say “%1” to cut in").arg(home.wake) : qsTr("On it")
                }
                Item { width: 1; height: 32 }
                Grid {
                    id: ideas
                    width: parent.width
                    columns: width > 640 ? 3 : 2
                    spacing: 12
                    Repeater {
                        model: home.ideas
                        Suggestion { required property var modelData; width: (ideas.width - (ideas.columns - 1) * ideas.spacing) / ideas.columns
                                     symbol: modelData[0]; title: modelData[1]; hint: modelData[2]; page: modelData[3] || "" }
                    }
                }
            }
        }

        Pill {
            id: fresh
            anchors { top: parent.top; topMargin: home.wide ? 52 : 62; right: parent.right; rightMargin: (parent.width - home.column) / 2 }
            visible: messages.count > 0
            implicitHeight: 36
            text: qsTr("New chat")
            symbol: "plus"
            onClicked: Api.post("/api/new", {}, () => home.reload())
        }

        Chip {  // Gemini Live can't be used (or is switched off): the backup voice answers
            id: backup
            anchors { verticalCenter: fresh.verticalCenter; left: parent.left; leftMargin: (parent.width - home.column) / 2 }
            visible: Backend.backup
            focusPolicy: Qt.NoFocus
            dot: "working"
            text: qsTr("Backup voice")
            Tip { text: qsTr("The backup voice (Models page) answers instead of Gemini Live"); visible: backup.hovered }
        }

        ListView {
            id: list
            anchors { left: parent.left; right: parent.right; top: fresh.bottom; topMargin: home.wide ? 4 : 14; bottom: composer.top; bottomMargin: 4 }
            visible: messages.count > 0
            clip: true
            model: messages
            topMargin: 8
            bottomMargin: 16
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: Scroller {}
            // (the latest stays in view when the message box grows: attaching a file hid it behind the box's new height)
            property bool following: true
            onContentYChanged: following = atYEnd
            onHeightChanged: if (following) Qt.callLater(positionViewAtEnd)
            delegate: Message { width: ListView.view.width; column: home.column }
            add: Transition {
                NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 220; easing.type: Easing.OutCubic }
                NumberAnimation { property: "rise"; from: 8; to: 0; duration: 220; easing.type: Easing.OutCubic }
            }
            footer: Item {  // while Jarvis works: a warm reactor, a pulsing "Working on it…" chip and Stop
                id: busy
                readonly property bool on: Backend.state === "thinking"
                width: ListView.view.width
                height: on ? 48 : 0
                visible: on
                onOnChanged: if (on) Qt.callLater(list.positionViewAtEnd)
                Item {
                    x: (parent.width - home.column) / 2
                    width: home.column; height: 32
                    anchors.verticalCenter: parent.verticalCenter
                    Orb { width: 24; height: 24; anchors { left: parent.left; verticalCenter: parent.verticalCenter } rings: false; mode: "thinking" }
                    Rectangle {
                        anchors { left: parent.left; leftMargin: 36 }  // (the text column, like the tool chips)
                        width: working.implicitWidth + 26; height: 32; radius: 16
                        color: Theme.glass
                        border.width: 1
                        border.color: Theme.stroke
                        Row {
                            id: working
                            anchors.centerIn: parent
                            spacing: 9
                            StatusDot {
                                anchors.verticalCenter: parent.verticalCenter
                                status: "working"
                                SequentialAnimation on opacity {
                                    running: busy.on; loops: Animation.Infinite
                                    NumberAnimation { to: 0.35; duration: 700; easing.type: Easing.InOutSine }
                                    NumberAnimation { to: 1; duration: 700; easing.type: Easing.InOutSine }
                                }
                            }
                            Txt { anchors.verticalCenter: parent.verticalCenter; text: qsTr("Working on it…"); color: Theme.text2
                                  font.pixelSize: Theme.px(13); wrapMode: Text.NoWrap }
                        }
                    }
                    Chip {  // (it ends every task, coding jobs too: with more than one it says so, and its tip names them)
                        id: stopAll
                        readonly property int tasks: today.jobs.length
                        anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                        symbol: "stop"; text: tasks > 1 ? qsTr("Stop all (%n)", "", tasks) : qsTr("Stop"); ink: Theme.warm
                        onClicked: Backend.stop()
                        Accessible.description: tasks > 1 ? today.jobList : ""
                        Tip { text: today.jobList; visible: stopAll.tasks > 1 && (stopAll.hovered || stopAll.visualFocus) }
                    }
                }
            }
        }

        Composer {
            id: composer
            anchors { bottom: parent.bottom; bottomMargin: 24; horizontalCenter: parent.horizontalCenter }
            width: home.column
            stopShown: list.visible && Backend.state === "thinking"  // (the Stop chip under the conversation)
            tasks: today.jobs.length
            taskList: today.jobList
            dropArea: home  // (files dropped anywhere on the page)
            onSubmitted: (text, files) => home.send(text, files)
        }
    }

    Today {
        id: today
        // (anchors, so they mirror; both sides always: swapping one for the other set both for a moment, and Qt then
        // dropped the width binding for good)
        anchors { left: parent.left; right: parent.right
                  leftMargin: home.wide ? home.width - 300 - 12 : (home.width - home.column) / 2 + (backup.visible ? backup.width + 12 : 0)
                  rightMargin: home.wide ? 12 : (home.width - home.column) / 2 + (fresh.visible ? fresh.width + 12 : 0) }
        y: 52
        height: home.wide ? home.height - y - 24 : 56
        compact: !home.wide
        latency: home.latency
        onWake: phrase => home.wake = phrase
    }

    component Suggestion: AbstractButton {
        id: s
        objectName: "idea"
        property string symbol
        property string title
        property string hint
        property string page: ""  // a page it opens instead of asking Jarvis
        hoverEnabled: true
        focusPolicy: Qt.TabFocus  // (Tab reaches it; a click leaves the typing where it was)
        Keys.onReturnPressed: click()
        Keys.onEnterPressed: click()
        implicitHeight: 76
        onClicked: page ? home.goTo(page) : Backend.send(title)
        background: Glass {
            color: s.hovered ? Theme.glassHover : Theme.glass
            border.color: s.hovered ? Theme.alpha(Theme.accent, 0.3) : Theme.stroke
            Behavior on color { ColorAnimation { duration: Theme.fast } }
            Behavior on border.color { ColorAnimation { duration: Theme.fast } }
            Focus { keyboard: true; visible: s.visualFocus }
        }
        contentItem: Item {
            Rectangle {
                id: well
                anchors { left: parent.left; leftMargin: 16; verticalCenter: parent.verticalCenter }
                width: 36; height: 36; radius: 18
                color: s.hovered ? Theme.alpha(Theme.accent, 0.22) : Theme.accentSoft
                Icon { anchors.centerIn: parent; name: s.symbol; size: 18; color: Theme.accent }
            }
            Column {
                anchors { left: well.right; leftMargin: 12; right: parent.right; rightMargin: 14; verticalCenter: parent.verticalCenter }
                spacing: 3
                Txt { text: s.title; width: parent.width; weight: 600; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                Txt { text: s.hint; kind: "small"; font.pixelSize: Theme.px(12); width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap }
            }
        }
        scale: down ? 0.97 : 1
        Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
    }
}
