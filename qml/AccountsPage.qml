import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Jarvis

// The user's accounts (through Composio): connect them, and decide what Jarvis may do with each.
ScrollPage {
    id: page
    objectName: "accountsPage"
    title: qsTr("Accounts")
    hint: qsTr("Connect your accounts so Jarvis can read and act on them. You decide what it may do with each.")
    property var items: []
    property bool loading: true
    property bool asking: false  // a load on its way (showing the page again doesn't ask Composio twice)
    property string problem: ""
    property var waiting: null  // an account whose sign-in is open in the browser: {slug, name, until}
    property var approvals: []  // what the user told Jarvis (by voice) not to ask before: [{tool, app, label, said, at}]
    readonly property var connected: items.filter(a => a.connected)
    readonly property var others: items.filter(a => !a.connected)

    function loadApprovals() { Api.get("/api/approvals", d => approvals = d) }
    function askAgain(a) {  // (taking one back can be undone by saying so again, so it's one click; allowing stays the voice's)
        Api.post("/api/approvals/revoke", { tool: a.tool }, d => {
            approvals = d
            Backend.toast(qsTr("Jarvis will ask again before “%1”").arg(a.label), false)
        })
    }

    function load(quiet) {  // quiet: the look while waiting for a sign-in (Refresh stays as it is)
        if (asking) return
        asking = true
        if (!quiet) loading = true
        Api.get("/api/workspaces", d => { items = d; problem = ""; loading = asking = false; signedIn() },
                e => { problem = e.error; loading = asking = false })
    }
    function connect(a, note) {
        Api.post(`/api/workspaces/${a.slug}/connect`, {}, () => {
            Backend.toast(note, false)
            if (!a.connected) waiting = { slug: a.slug, name: a.name, until: Date.now() + 120000 }
        })
    }
    function signedIn() {  // the account being waited for shows as connected: done waiting
        if (waiting && items.some(a => a.slug === waiting.slug && a.connected)) {
            Backend.toast(qsTr("%1 connected").arg(waiting.name), false)
            waiting = null
        }
    }
    function glyph(slug) {  // a line icon for a service (Composio's logos are remote images)
        const known = [[/mail|outlook/, "mail"], [/calendar/, "calendar"], [/drive|dropbox|onedrive/, "cloud"], [/classroom/, "screen"],
                       [/github|gitlab|linear|jira/, "wrench"], [/spotify|youtube|music/, "music"], [/slack|discord|telegram|whatsapp|teams/, "chats"],
                       [/notion|docs|sheets/, "edit"], [/todoist|tasks|trello/, "check"]]
        const hit = known.find(k => k[0].test(slug))
        return hit ? hit[1] : "link"
    }
    Component.onCompleted: { load(); loadApprovals() }
    onVisibleChanged: if (visible) { load(); loadApprovals() }
    Timer {  // after Connect: looks every 3 s for two minutes, until the sign-in in the browser is done
        interval: 3000; repeat: true; running: page.waiting !== null
        onTriggered: {
            if (Date.now() < page.waiting.until) return page.load(true)
            Backend.toast(qsTr("%1 isn't connected yet: press Refresh once you've signed in").arg(page.waiting.name), false)
            page.waiting = null
        }
    }

    actions: Pill { text: qsTr("Refresh"); symbol: "refresh"; enabled: !page.loading; onClicked: { page.load(); page.loadApprovals() } }

    Card {
        Layout.fillWidth: true
        visible: page.problem !== ""
        color: Theme.alpha(Theme.warmSoft, 0.6)
        border.color: Theme.alpha(Theme.warm, 0.25)
        RowLayout {
            width: parent.width
            spacing: 12
            Icon { name: "alert"; color: Theme.warm; size: 18; Layout.preferredWidth: 18; Layout.preferredHeight: 18 }
            Txt { Layout.fillWidth: true; text: qsTr("Couldn't reach your accounts: %1").arg(page.problem) }
        }
    }
    Txt { kind: "small"; text: qsTr("Checking your accounts…"); visible: page.loading && !page.items.length }

    Section {
        title: qsTr("Connected")
        description: qsTr("Choose what Jarvis may do with each account.")
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
                    readonly property bool lit: hover.hovered || confirming || signIn.activeFocus || drop.activeFocus  // (Tab reaches them: they show then too)
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
                                  text: row.modelData.account || qsTr("Connected") }
                        }
                        RowLayout {  // shown on hover: they're rarely needed
                            spacing: 0
                            opacity: row.lit ? 1 : 0
                            Behavior on opacity { NumberAnimation { duration: Theme.fast } }
                            IconButton {
                                id: signIn
                                symbol: "refresh"; size: 32; glyph: 16; color: Theme.text3; tip: qsTr("Sign in again")
                                onClicked: page.connect(row.modelData, qsTr("Sign-in opened in your browser"))
                            }
                            IconButton {
                                id: drop
                                symbol: row.confirming ? "check" : "trash"; size: 32; glyph: 16
                                color: row.confirming ? Theme.red : Theme.text3
                                tip: row.confirming ? qsTr("Click again to disconnect") : qsTr("Disconnect")
                                onClicked: {
                                    if (!row.confirming) { row.confirming = true; undo.restart(); return }
                                    Api.post(`/api/workspaces/${row.modelData.slug}/disconnect`, {}, () => { Backend.toast(qsTr("%1 disconnected").arg(row.modelData.name), false); page.load() })
                                }
                                Timer { id: undo; interval: 4000; onTriggered: row.confirming = false }
                            }
                        }
                        Select {
                            Layout.preferredWidth: 200
                            model: [{ value: "ask", label: qsTr("Ask before changes") }, { value: "full", label: qsTr("Full access") },
                                    { value: "read_only", label: qsTr("Read only") }, { value: "paused", label: qsTr("Paused") }]
                            value: row.modelData.mode
                            onPicked: v => Api.post(`/api/workspaces/${row.modelData.slug}/mode`, { mode: v }, () => Backend.toast(`${row.modelData.name}: ${displayText}`, false))
                        }
                    }
                }
            }
        }
    }

    Section {
        title: qsTr("Jarvis no longer asks before…")
        description: qsTr("You told Jarvis it may do these without asking first. Ask again takes that back.")
        visible: page.approvals.length > 0
        spacing: 8
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            Repeater {
                model: page.approvals
                ColumnLayout {
                    id: allowed
                    required property var modelData
                    required property int index
                    readonly property string day: new Date(modelData.at * 1000).toLocaleDateString(Qt.locale(), "d MMM yyyy")
                    Layout.fillWidth: true
                    spacing: 0
                    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.stroke; visible: allowed.index > 0 }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.minimumHeight: 64
                        spacing: 12
                        Service { slug: allowed.modelData.app }
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.topMargin: 10; Layout.bottomMargin: 10
                            spacing: 2
                            Txt { text: allowed.modelData.label; weight: 600; Layout.fillWidth: true }
                            Txt { kind: "small"; Layout.fillWidth: true; maximumLineCount: 2; elide: Text.ElideRight
                                  text: allowed.modelData.said ? qsTr("You said “%1” on %2").arg(allowed.modelData.said).arg(allowed.day)
                                        : qsTr("Since %1").arg(allowed.day) }
                        }
                        Pill { text: qsTr("Ask again"); Accessible.description: allowed.modelData.label; onClicked: page.askAgain(allowed.modelData) }
                    }
                }
            }
        }
    }

    Section {
        title: page.connected.length ? qsTr("More accounts") : qsTr("Accounts you can connect")
        description: qsTr("Pick one to sign in from your browser, then press Refresh.")
        visible: page.others.length > 0
        Flow {
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: page.others
                Chip {
                    id: tile
                    required property var modelData
                    readonly property bool waits: !!page.waiting && page.waiting.slug === modelData.slug
                    implicitHeight: 36
                    symbol: page.glyph(modelData.slug)
                    dot: waits ? "working" : ""
                    checked: waits
                    text: waits ? qsTr("%1: waiting for sign-in…").arg(modelData.name) : modelData.name
                    onClicked: page.connect(modelData, qsTr("Finish signing in in your browser, then press Refresh"))
                    Tip { text: qsTr("Connect %1").arg(tile.modelData.name); visible: tile.hovered }
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
