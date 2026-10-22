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
    readonly property var connected: items.filter(a => a.connected)
    readonly property var others: items.filter(a => !a.connected)

    function load() {
        loading = true
        Api.get("/api/workspaces", d => { items = d; problem = ""; loading = false }, e => { problem = e.error; loading = false })
    }
    function connect(a, note) { Api.post(`/api/workspaces/${a.slug}/connect`, {}, () => Backend.toast(note, false)) }
    function glyph(slug) {  // a line icon for a service (Composio's logos are remote images)
        const known = [[/mail|outlook/, "mail"], [/calendar/, "calendar"], [/drive|dropbox|onedrive/, "cloud"], [/classroom/, "screen"],
                       [/github|gitlab|linear|jira/, "wrench"], [/spotify|youtube|music/, "music"], [/slack|discord|telegram|whatsapp|teams/, "chats"],
                       [/notion|docs|sheets/, "edit"], [/todoist|tasks|trello/, "check"]]
        const hit = known.find(k => k[0].test(slug))
        return hit ? hit[1] : "link"
    }
    Component.onCompleted: load()

    actions: Pill { text: "Refresh"; symbol: "refresh"; enabled: !page.loading; onClicked: page.load() }

    Card {
        Layout.fillWidth: true
        visible: page.problem !== ""
        color: Theme.alpha(Theme.warmSoft, 0.6)
        border.color: Theme.alpha(Theme.warm, 0.25)
        RowLayout {
            width: parent.width
            spacing: 12
            Icon { name: "alert"; color: Theme.warm; size: 18; Layout.preferredWidth: 18; Layout.preferredHeight: 18 }
            Txt { Layout.fillWidth: true; text: "Couldn't reach your accounts: " + page.problem }
        }
    }
    Txt { kind: "small"; text: "Checking your accounts…"; visible: page.loading && !page.items.length }

    Section {
        title: "Connected"
        description: "Choose what Jarvis may do with each account."
        visible: page.connected.length > 0
        spacing: 8
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            Repeater {
                model: page.connected
                ColumnLayout {
                    id: row
                    required property var modelData
                    required property int index
                    property bool confirming: false
                    readonly property bool lit: hover.hovered || confirming
                    Layout.fillWidth: true
                    spacing: 0
                    HoverHandler { id: hover }
                    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.stroke; visible: row.index > 0 }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 64
                        spacing: 12
                        Service { slug: row.modelData.slug; lit: true }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Txt { text: row.modelData.name; weight: 600; elide: Text.ElideRight; wrapMode: Text.NoWrap; Layout.fillWidth: true }
                            Txt { kind: "small"; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap
                                  text: row.modelData.account || "Connected" }
                        }
                        RowLayout {  // shown on hover: they're rarely needed
                            spacing: 0
                            opacity: row.lit ? 1 : 0
                            Behavior on opacity { NumberAnimation { duration: Theme.fast } }
                            IconButton {
                                symbol: "refresh"; size: 32; glyph: 16; color: Theme.text3; tip: "Sign in again"
                                onClicked: page.connect(row.modelData, "Sign-in opened in your browser")
                            }
                            IconButton {
                                symbol: row.confirming ? "check" : "trash"; size: 32; glyph: 16
                                color: row.confirming ? Theme.red : Theme.text3
                                tip: row.confirming ? "Click again to disconnect" : "Disconnect"
                                onClicked: {
                                    if (!row.confirming) { row.confirming = true; undo.restart(); return }
                                    Api.post(`/api/workspaces/${row.modelData.slug}/disconnect`, {}, () => { Backend.toast(row.modelData.name + " disconnected", false); page.load() })
                                }
                                Timer { id: undo; interval: 4000; onTriggered: row.confirming = false }
                            }
                        }
                        Select {
                            Layout.preferredWidth: 200
                            model: [{ value: "ask", label: "Ask before changes" }, { value: "full", label: "Full access" },
                                    { value: "read_only", label: "Read only" }, { value: "paused", label: "Paused" }]
                            value: row.modelData.mode
                            onPicked: v => Api.post(`/api/workspaces/${row.modelData.slug}/mode`, { mode: v }, () => Backend.toast(`${row.modelData.name}: ${displayText}`, false))
                        }
                    }
                }
            }
        }
    }

    Section {
        title: page.connected.length ? "More accounts" : "Accounts you can connect"
        description: "Pick one to sign in from your browser, then press Refresh."
        visible: page.others.length > 0
        Flow {
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: page.others
                Chip {
                    id: tile
                    required property var modelData
                    implicitHeight: 36
                    symbol: page.glyph(modelData.slug)
                    text: modelData.name
                    onClicked: page.connect(modelData, "Finish signing in in your browser, then press Refresh")
                    Tip { text: "Connect " + tile.modelData.name; visible: tile.hovered }
                }
            }
        }
    }

    // a service's icon in a round well: cyan once it's connected
    component Service: Rectangle {
        property string slug
        property bool lit: false
        Layout.preferredWidth: 40; Layout.preferredHeight: 40
        radius: 20
        color: lit ? Theme.accentSoft : Theme.glass
        Icon { anchors.centerIn: parent; name: page.glyph(parent.slug); size: 20; color: parent.lit ? Theme.accent : Theme.text3 }
    }
}
