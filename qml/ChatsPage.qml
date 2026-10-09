import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Jarvis

// Past conversations: search them, read one, pick it up where it left off, or delete it.
Item {
    id: page
    signal opened()
    property var items: []
    property string current: ""
    property string selected: ""
    property var preview: null
    property bool confirming: false

    function load() {
        const q = search.text.trim()
        Api.get(q ? "/api/search?q=" + encodeURIComponent(q) : "/api/sessions", d => {
            items = q ? d : d.sessions
            if (!q) current = d.current
            if (items.length && !items.some(s => s.id === selected)) pick(items[0].id)
            if (!items.length) { selected = ""; preview = null }
        })
    }
    function pick(id) {
        selected = id
        confirming = false
        Api.get("/api/sessions/" + id, s => preview = s)
    }
    function ago(t) {
        const s = Date.now() / 1000 - t
        return s < 60 ? "just now" : s < 3600 ? Math.round(s / 60) + " min ago" : s < 86400 ? Math.round(s / 3600) + " h ago"
             : Qt.formatDate(new Date(t * 1000), "d MMM")
    }
    onVisibleChanged: if (visible) load()
    Component.onCompleted: load()
    Timer { id: debounce; interval: 250; onTriggered: page.load() }

    PageHeader {
        id: header
        anchors { left: parent.left; right: parent.right; top: parent.top; topMargin: 46; leftMargin: 34; rightMargin: 34 }
        title: "Chats"
        hint: "Every conversation is saved here. Open one to carry on where you left off."
        Pill { text: "New chat"; symbol: "plus"; kind: "primary"; onClicked: Api.post("/api/new", {}, () => page.opened()) }
    }

    RowLayout {
        anchors { left: parent.left; right: parent.right; top: header.bottom; bottom: parent.bottom; margins: 34; topMargin: 18 }
        spacing: 16

        ColumnLayout {
            Layout.preferredWidth: 320
            Layout.fillWidth: false
            Layout.fillHeight: true
            spacing: 10
            Field {
                id: search
                Layout.fillWidth: true
                placeholderText: "Search conversations"
                leftPadding: 38
                onTextChanged: debounce.restart()
                Icon { name: "search"; size: 16; color: Theme.faint; x: 13; anchors.verticalCenter: parent.verticalCenter }
            }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 4
                model: page.items
                ScrollBar.vertical: ScrollBar {}
                delegate: AbstractButton {
                    id: row
                    required property var modelData
                    width: ListView.view.width
                    height: 64
                    hoverEnabled: true
                    onClicked: page.pick(modelData.id)
                    background: Rectangle {
                        radius: 12
                        color: page.selected === modelData.id ? Theme.alpha(Theme.accent, 0.15) : row.hovered ? Theme.card : "transparent"
                        border.width: page.selected === modelData.id ? 1 : 0
                        border.color: Theme.alpha(Theme.accent, 0.3)
                    }
                    contentItem: ColumnLayout {
                        spacing: 3
                        RowLayout {
                            Layout.leftMargin: 12; Layout.rightMargin: 12
                            Txt { text: modelData.title; font.weight: Font.DemiBold; elide: Text.ElideRight; wrapMode: Text.NoWrap; Layout.fillWidth: true }
                            Rectangle { visible: modelData.id === page.current; width: 7; height: 7; radius: 4; color: Theme.listen }
                        }
                        Txt {
                            Layout.leftMargin: 12; Layout.rightMargin: 12; Layout.fillWidth: true
                            kind: "small"; elide: Text.ElideRight; wrapMode: Text.NoWrap
                            text: modelData.match ? modelData.match : page.ago(modelData.updated) + " · " + modelData.count + " messages"
                        }
                    }
                }
                Txt { anchors.centerIn: parent; kind: "small"; visible: !page.items.length
                      text: search.text ? "Nothing matches that" : "No conversations yet" }
            }
        }

        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            padding: 0
            ColumnLayout {
                anchors.fill: parent
                spacing: 0
                visible: page.preview !== null
                RowLayout {
                    Layout.fillWidth: true
                    Layout.margins: 18
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Txt { kind: "heading"; text: page.preview ? page.preview.title : ""; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                        Txt { kind: "small"; text: page.preview ? Qt.formatDateTime(new Date(page.preview.updated * 1000), "dddd d MMMM, HH:mm") : "" }
                    }
                    Pill {
                        text: page.confirming ? "Click again to delete" : "Delete"
                        kind: "danger"
                        symbol: "trash"
                        onClicked: {
                            if (!page.confirming) { page.confirming = true; undo.restart(); return }
                            Api.post(`/api/sessions/${page.selected}/delete`, {}, () => { Backend.toast("Conversation deleted", false); page.load() })
                        }
                        Timer { id: undo; interval: 4000; onTriggered: page.confirming = false }
                    }
                    Pill { text: "Open"; kind: "primary"; symbol: "chats"; visible: page.selected !== page.current
                           onClicked: Api.post(`/api/sessions/${page.selected}/open`, {}, () => page.opened()) }
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 6
                    topMargin: 10
                    bottomMargin: 16
                    ScrollBar.vertical: ScrollBar {}
                    model: page.preview ? page.preview.messages.filter(m => ["you", "jarvis", "tool", "system", "image"].includes(m.who)) : []
                    delegate: Message {
                        required property var modelData
                        width: ListView.view.width
                        who: modelData.who; text: String(modelData.text || ""); caption: String(modelData.caption || ""); time: modelData.time || 0
                    }
                }
            }
            Txt { anchors.centerIn: parent; kind: "small"; visible: page.preview === null; text: "Pick a conversation to read it" }
        }
    }
}
