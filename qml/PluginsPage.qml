import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Jarvis

// Plugins are MCP servers: more tools for Jarvis, from a web address or a command on this PC.
ScrollPage {
    id: page
    title: "Plugins"
    hint: "Give Jarvis more tools with MCP servers: a web address, or a command that runs on this PC."
    property var items: []
    property string kind: "url"

    function load() { Api.get("/api/plugins", d => items = d) }
    function preset(name, how, value) { pname.text = name; kind = how; target.text = value }
    Component.onCompleted: load()
    Timer { interval: 4000; running: page.visible && page.items.some(p => p.status === "connecting"); repeat: true; onTriggered: page.load() }

    actions: Pill { text: "Refresh"; symbol: "refresh"; onClicked: page.load() }

    Repeater {
        model: page.items
        Card {
            id: card
            required property var modelData
            property bool confirming: false
            Layout.fillWidth: true
            RowLayout {
                width: parent.width
                spacing: 14
                Rectangle {
                    Layout.preferredWidth: 10; Layout.preferredHeight: 10; radius: 5
                    color: card.modelData.status === "ready" ? Theme.green : card.modelData.status === "error" ? Theme.red
                         : card.modelData.status === "off" ? Theme.faint : Theme.warm
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Txt { text: card.modelData.name; font.weight: Font.DemiBold }
                    Txt {
                        kind: "small"; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap
                        text: card.modelData.error ? card.modelData.error
                            : card.modelData.status === "ready" ? `${card.modelData.tools.length} tools · ${card.modelData.config.url || card.modelData.config.command}`
                            : card.modelData.status === "off" ? "Turned off" : "Connecting… (a sign-in page may open in your browser)"
                        color: card.modelData.error ? Theme.red : Theme.dim
                    }
                }
                Toggle {
                    implicitWidth: 44
                    checked: card.modelData.enabled
                    onToggled: Api.post(`/api/plugins/${card.modelData.name}/toggle`, {}, page.load)
                }
                Pill {
                    text: card.confirming ? "Click again" : "Remove"
                    kind: "danger"
                    onClicked: {
                        if (!card.confirming) { card.confirming = true; undo.restart(); return }
                        Api.post(`/api/plugins/${card.modelData.name}/delete`, {}, () => { Backend.toast("Plugin removed", false); page.load() })
                    }
                    Timer { id: undo; interval: 4000; onTriggered: card.confirming = false }
                }
            }
        }
    }

    Card {
        Layout.fillWidth: true
        ColumnLayout {
            width: parent.width
            spacing: 12
            Txt { kind: "heading"; text: "Add a plugin" }
            Flow {
                Layout.fillWidth: true
                spacing: 8
                Txt { kind: "small"; text: "Quick picks:"; height: 32; verticalAlignment: Text.AlignVCenter }
                Repeater {
                    model: [["Notion (official)", "notion", "url", "https://mcp.notion.com/mcp"],
                            ["Docs lookup (Context7)", "context7", "url", "https://mcp.context7.com/mcp"],
                            ["Files in my home folder", "files", "command", "npx -y @modelcontextprotocol/server-filesystem ~"],
                            ["Headless browser (Playwright)", "playwright", "command", "npx -y @playwright/mcp@latest --headless"]]
                    Pill { required property var modelData; implicitHeight: 32; text: modelData[0]; onClicked: page.preset(modelData[1], modelData[2], modelData[3]) }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Field { id: pname; Layout.preferredWidth: 180; placeholderText: "name" }
                Select {
                    Layout.preferredWidth: 150
                    model: [{ value: "url", label: "Web address" }, { value: "command", label: "Command" }]
                    value: page.kind
                    onPicked: v => page.kind = v
                }
                Field { id: target; Layout.fillWidth: true; placeholderText: page.kind === "url" ? "https://example.com/mcp" : "npx -y some-mcp-server" }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Field { id: extra; Layout.fillWidth: true
                        placeholderText: page.kind === "url" ? "headers as JSON (optional), e.g. {\"Authorization\": \"Bearer …\"}" : "environment as JSON (optional)" }
                Field { id: only; Layout.preferredWidth: 220; placeholderText: "only these tools (optional)" }
            }
            Pill {
                text: "Add plugin"
                kind: "primary"
                symbol: "plus"
                enabled: pname.text.trim() !== "" && target.text.trim() !== ""
                onClicked: Api.post("/api/plugins", Object.assign({ name: pname.text, tools: only.text },
                                                                  page.kind === "url" ? { url: target.text, headers: extra.text } : { command: target.text, env: extra.text }),
                                    () => { Backend.toast("Plugin added: connecting…", false); pname.text = target.text = extra.text = only.text = ""; page.load() })
            }
        }
    }
    Item { Layout.preferredHeight: 20 }
}
