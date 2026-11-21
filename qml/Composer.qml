import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import Jarvis

// The message box: Enter sends, Shift+Enter starts a new line; talk, or stop Jarvis. Files are attached here whichever
// way they come: the attach button (the desktop's own file dialog), pasted (a picture, or files copied in a file
// manager) or dropped anywhere on `dropArea`. `submitted` hands over the words and the files together.
Glass {
    id: c
    objectName: "composer"
    property var files: []
    property bool stopShown: false  // (Stop is already on screen elsewhere)
    property int tasks: 0  // tasks at work, which Stop ends too (Esc doesn't)
    property string taskList: ""  // ...one line each
    property Item dropArea: c
    signal submitted(string text, var files)
    readonly property bool busy: Backend.state !== "idle"
    readonly property bool typed: input.text.trim() !== "" || files.length > 0
    floating: true
    implicitHeight: Math.max(56, col.implicitHeight + 16)
    radius: 28
    border.color: input.activeFocus ? Theme.alpha(Theme.accent, 0.3) : Theme.stroke
    Behavior on border.color { ColorAnimation { duration: Theme.fast } }

    function add(paths) {  // (a file already attached isn't added twice)
        const fresh = paths.filter((p, i) => !files.includes(p) && paths.indexOf(p) === i)
        if (fresh.length) {
            files = files.concat(fresh)
            Qt.callLater(strip.positionViewAtEnd)
        }
    }
    function remove(path) { files = files.filter(p => p !== path) }
    function paste() {  // a picture or files on the clipboard are attached; text goes in as text
        const got = Backend.paste()
        if (got.length) add(got)
        else input.paste()
    }
    function send() {
        submitted(input.text, files)
        input.text = ""
        files = []
    }

    FileDialog {
        id: picker
        fileMode: FileDialog.OpenFiles
        title: qsTr("Attach files for Jarvis")
        onAccepted: c.add(Backend.localFiles(selectedFiles))
    }
    DropArea {
        id: drop
        parent: c.dropArea
        anchors.fill: parent
        onEntered: drag => drag.accepted = drag.hasUrls
        onDropped: event => {
            const got = Backend.localFiles(event.urls)
            if (got.length) c.add(got)
            else input.insert(input.cursorPosition, event.urls.join(" "))  // (a link dragged from a browser: its address)
        }
    }
    Rectangle {  // dragging files over the page
        parent: c.dropArea
        anchors { fill: parent; margins: 16; topMargin: 46 }  // (clear of the window's top strip)
        z: 10
        visible: drop.containsDrag
        radius: Theme.radius
        color: Theme.alpha(Theme.accentSoft, 0.6)
        border.width: 1
        border.color: Theme.alpha(Theme.accent, 0.5)
        Column {
            anchors.centerIn: parent
            spacing: 10
            Icon { anchors.horizontalCenter: parent.horizontalCenter; name: "attach"; size: 28; color: Theme.accent }
            Txt { kind: "heading"; text: qsTr("Drop to attach") }
        }
    }

    ColumnLayout {
        id: col
        anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; leftMargin: 8; rightMargin: 8 }
        spacing: 6
        ListView {  // the files attached
            id: strip
            Layout.fillWidth: true
            Layout.preferredHeight: 62  // (room above for a picture's remove button)
            Layout.leftMargin: 6
            Layout.rightMargin: 6
            visible: c.files.length > 0
            orientation: ListView.Horizontal
            spacing: 8
            rightMargin: 6
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            model: c.files
            delegate: Item {
                required property string modelData
                width: tile.width
                height: 62
                Attachment {
                    id: tile
                    y: 6
                    path: parent.modelData
                    removable: true
                    onRemoved: { c.remove(parent.modelData); input.forceActiveFocus() }
                }
            }
            ScrollBar.horizontal: Scroller {}
        }
        RowLayout {
            spacing: 6
            IconButton {
                size: 40
                symbol: "attach"
                tip: qsTr("Attach files (or paste or drop them here)")
                tint: Theme.glass  // (a pair with the mic at the other end)
                iconColor: hovered ? Theme.text : Theme.text2
                onClicked: picker.open()
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(Math.max(40, input.implicitHeight), 5 * 22 + 18)
                TextArea {
                    id: input
                    objectName: "composerInput"
                    placeholderText: qsTr("Ask Jarvis")
                    placeholderTextColor: Theme.text3
                    color: Theme.text
                    font.family: Theme.font
                    font.pixelSize: Theme.px(15)
                    wrapMode: TextEdit.Wrap
                    selectionColor: Theme.alpha(Theme.accent, 0.4)
                    selectedTextColor: Theme.text
                    verticalAlignment: TextEdit.AlignVCenter
                    leftPadding: 4
                    background: null
                    focus: true
                    Keys.onTabPressed: nextItemInFocusChain().forceActiveFocus(Qt.TabFocusReason)
                    Keys.onBacktabPressed: nextItemInFocusChain(false).forceActiveFocus(Qt.BacktabFocusReason)
                    Keys.onPressed: event => {  // (before the box pastes by itself: it only knows text)
                        if (event.matches(StandardKey.Paste) || (event.key === Qt.Key_Insert && event.modifiers & Qt.ShiftModifier)) {
                            event.accepted = true
                            c.paste()
                        }
                    }
                    Keys.onReturnPressed: event => {
                        if (event.modifiers & Qt.ShiftModifier) { event.accepted = false; return }
                        c.send()
                    }
                    ContextMenu.menu: Menu {  // (Qt's own pastes text only)
                        padding: 5
                        background: Glass { implicitWidth: 180; floating: true; color: Theme.popover; radius: Theme.radiusControl; border.color: Theme.strokeStrong }
                        delegate: MenuItem {
                            id: item
                            implicitHeight: 34
                            contentItem: Txt { text: item.text; leftPadding: 8; verticalAlignment: Text.AlignVCenter; wrapMode: Text.NoWrap
                                               color: item.enabled ? Theme.text : Theme.text3 }
                            background: Rectangle { radius: Theme.radiusSmall; color: item.highlighted ? Theme.glassHover : "transparent" }
                        }
                        Action { text: qsTr("Undo"); enabled: input.canUndo; onTriggered: input.undo() }
                        Action { text: qsTr("Redo"); enabled: input.canRedo; onTriggered: input.redo() }
                        MenuSeparator { contentItem: Rectangle { implicitHeight: 1; color: Theme.stroke } }
                        Action { text: qsTr("Cut"); enabled: input.selectedText !== ""; onTriggered: input.cut() }
                        Action { text: qsTr("Copy"); enabled: input.selectedText !== ""; onTriggered: input.copy() }
                        Action { text: qsTr("Paste"); onTriggered: c.paste() }
                        Action { text: qsTr("Delete"); enabled: input.selectedText !== ""; onTriggered: input.remove(input.selectionStart, input.selectionEnd) }
                        MenuSeparator { contentItem: Rectangle { implicitHeight: 1; color: Theme.stroke } }
                        Action { text: qsTr("Select all"); enabled: input.text !== ""; onTriggered: input.selectAll() }
                    }
                }
            }
            IconButton {
                size: 40
                symbol: Backend.listening ? "pause" : "mic"
                tip: Backend.listening ? qsTr("Pause listening") : qsTr("Talk to Jarvis")
                tint: Backend.listening ? Theme.listen : Theme.glass
                iconColor: Backend.listening ? Theme.accentInk : hovered ? Theme.text : Theme.text2
                Rectangle {  // the voice level
                    z: -1
                    anchors.centerIn: parent
                    width: parent.width; height: width; radius: width / 2
                    visible: Backend.listening
                    color: "transparent"
                    border.width: 2
                    border.color: Theme.alpha(Theme.listen, 0.45)
                    scale: 1 + Math.min(1, Backend.level) * 0.3
                    Behavior on scale { NumberAnimation { duration: 90 } }
                }
                onClicked: Backend.listening ? Backend.pause() : Backend.talk()
            }
            IconButton {
                readonly property bool stopping: c.busy && !c.typed && !c.stopShown
                visible: c.typed || stopping
                size: 40
                symbol: stopping ? "stop" : "send"
                tint: stopping ? Theme.warmSoft : Theme.accent
                iconColor: stopping ? Theme.warm : Theme.accentInk
                tip: !stopping ? qsTr("Send (Enter)") : c.tasks > 1 ? qsTranslate("HomePage", "Stop all (%n)", "", c.tasks) + "\n" + c.taskList
                   : c.tasks ? qsTranslate("HomePage", "Stop") : qsTr("Stop (Esc)")
                Rectangle { anchors.fill: parent; radius: width / 2; visible: parent.stopping; color: "transparent"
                            border.width: 1; border.color: Theme.alpha(Theme.warm, 0.4) }
                onClicked: { if (stopping) Backend.stop(); else c.send() }
            }
        }
    }
}
