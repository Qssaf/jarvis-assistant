import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Jarvis

// The user's accounts (through Composio): connect them, and decide what Jarvis may do with each.
ScrollPage {
    id: page
    title: "Accounts"
    hint: "Connect your accounts so Jarvis can read and act on them. You decide what it may do with each."
    property var items: []
    property bool loading: true
    property string problem: ""

    function load() {
        loading = true
        Api.get("/api/workspaces", d => { items = d; problem = ""; loading = false }, e => { problem = e.error; loading = false })
    }
    Component.onCompleted: load()

    actions: Pill { text: "Refresh"; symbol: "refresh"; onClicked: page.load() }

    Card {
        Layout.fillWidth: true
        visible: page.problem !== ""
        RowLayout {
            width: parent.width
            Icon { name: "bell"; color: Theme.warm; size: 18 }
            Txt { Layout.fillWidth: true; text: "Couldn't reach your accounts: " + page.problem }
        }
    }
    Txt { kind: "small"; text: "Checking your accounts…"; visible: page.loading && !page.items.length }

    GridLayout {
        Layout.fillWidth: true
        columns: Math.max(1, Math.floor(width / 300))
        rowSpacing: 12
        columnSpacing: 12
        Repeater {
            model: page.items
            Card {
                id: card
                required property var modelData
                property bool confirming: false
                Layout.fillWidth: true
                Layout.preferredHeight: 150
                hover: true
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10
                    RowLayout {
                        spacing: 12
                        Rectangle {
                            Layout.preferredWidth: 40; Layout.preferredHeight: 40; radius: 12
                            color: card.modelData.connected ? Theme.alpha(Theme.accent, 0.18) : Theme.raised
                            Txt {
                                anchors.centerIn: parent
                                text: card.modelData.name.split(/[ (]/).filter(w => w).slice(0, 2).map(w => w[0]).join("").toUpperCase()
                                font.weight: Font.Bold; font.pixelSize: 14
                                color: card.modelData.connected ? Theme.accent : Theme.dim
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 1
                            Txt { text: card.modelData.name; font.weight: Font.DemiBold; elide: Text.ElideRight; wrapMode: Text.NoWrap; Layout.fillWidth: true }
                            Txt { kind: "small"; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap
                                  text: card.modelData.connected ? (card.modelData.account || "Connected") : "Not connected"
                                  color: card.modelData.connected ? Theme.green : Theme.faint }
                        }
                    }
                    Item { Layout.fillHeight: true }
                    RowLayout {
                        Layout.fillWidth: true
                        visible: card.modelData.connected
                        spacing: 6
                        Select {
                            Layout.fillWidth: true
                            implicitHeight: 34
                            model: [{ value: "ask", label: "Ask before changes" }, { value: "full", label: "Full access" },
                                    { value: "read_only", label: "Read only" }, { value: "paused", label: "Paused" }]
                            value: card.modelData.mode
                            onPicked: v => Api.post(`/api/workspaces/${card.modelData.slug}/mode`, { mode: v }, () => Backend.toast(`${card.modelData.name}: ${displayText}`, false))
                        }
                        IconButton {
                            symbol: "refresh"; size: 34; glyph: 15; tip: "Sign in again"
                            onClicked: Api.post(`/api/workspaces/${card.modelData.slug}/connect`, {}, () => Backend.toast("Sign-in opened in your browser", false))
                        }
                        IconButton {
                            symbol: card.confirming ? "check" : "trash"; size: 34; glyph: 15
                            color: card.confirming ? Theme.red : Theme.dim
                            tip: card.confirming ? "Click again to disconnect" : "Disconnect"
                            onClicked: {
                                if (!card.confirming) { card.confirming = true; undo.restart(); return }
                                Api.post(`/api/workspaces/${card.modelData.slug}/disconnect`, {}, () => { Backend.toast(card.modelData.name + " disconnected", false); page.load() })
                            }
                            Timer { id: undo; interval: 4000; onTriggered: card.confirming = false }
                        }
                    }
                    Pill {
                        visible: !card.modelData.connected
                        text: "Connect"
                        symbol: "plus"
                        onClicked: Api.post(`/api/workspaces/${card.modelData.slug}/connect`, {}, () => Backend.toast("Finish signing in in your browser, then press Refresh", false))
                    }
                }
            }
        }
    }
    Item { Layout.preferredHeight: 20 }
}
