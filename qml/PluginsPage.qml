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
    function preset(name, how, value, more) { pname.text = name; kind = how; target.text = value; extra.text = more || "" }
    Component.onCompleted: load()
    function wait(seconds) { return seconds >= 90 ? Math.round(seconds / 60) + " min" : seconds + " s" }
    Timer { interval: 4000; running: page.visible && page.items.some(p => p.status === "connecting" || p.status === "retrying")
            repeat: true; onTriggered: page.load() }

    actions: Pill { text: "Refresh"; symbol: "refresh"; onClicked: page.load() }

    Section {
        title: "Installed"
        visible: page.items.length > 0
        spacing: 8
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            Repeater {
                model: page.items
                ColumnLayout {
                    id: row
                    required property var modelData
                    required property int index
                    property bool confirming: false
                    readonly property bool on: modelData.status !== "off"
                    Layout.fillWidth: true
                    spacing: 0
                    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.stroke; visible: row.index > 0 }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 64
                        spacing: 12
                        Rectangle {
                            Layout.preferredWidth: 40; Layout.preferredHeight: 40; radius: 20
                            color: row.on ? Theme.accentSoft : Theme.glass
                            Icon { anchors.centerIn: parent; name: row.modelData.config.url ? "globe" : "wrench"; size: 20
                                   color: row.on ? Theme.accent : Theme.text3 }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            RowLayout {
                                spacing: 8
                                Txt { text: row.modelData.name; weight: 600; wrapMode: Text.NoWrap }
                                Txt { kind: "label"; visible: row.modelData.status === "ready"; color: Theme.text3
                                      text: row.modelData.tools.length + (row.modelData.tools.length === 1 ? " tool" : " tools") }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                StatusDot {
                                    // (out of reach and retrying by itself: orange, not red)
                                    status: row.modelData.status === "ready" ? "ok" : row.modelData.status === "error" ? "error"
                                          : row.modelData.status === "off" ? "off" : "working"
                                }
                                Txt {
                                    kind: "small"; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap
                                    text: row.modelData.status === "retrying" ? `${row.modelData.error} · trying again in ${page.wait(row.modelData.retry_in)}`
                                        : row.modelData.status === "connecting" && row.modelData.error ? "Trying again…"
                                        : row.modelData.error ? row.modelData.error
                                        : row.modelData.status === "ready" ? (row.modelData.config.url || row.modelData.config.command)
                                        : row.modelData.status === "off" ? "Turned off" : "Connecting… (a sign-in page may open in your browser)"
                                    color: row.modelData.status === "error" ? Theme.red : row.modelData.status === "off" ? Theme.text3 : Theme.text2
                                }
                            }
                        }
                        Pill {
                            visible: row.modelData.status === "error" || row.modelData.status === "retrying"
                            text: "Try now"; symbol: "refresh"
                            onClicked: Api.post(`/api/plugins/${row.modelData.name}/retry`, {}, page.load)
                        }
                        Toggle {
                            implicitWidth: 44
                            checked: row.modelData.enabled
                            onToggled: Api.post(`/api/plugins/${row.modelData.name}/toggle`, {}, page.load)
                        }
                        IconButton {
                            Layout.rightMargin: -8
                            symbol: row.confirming ? "check" : "trash"
                            color: row.confirming ? Theme.red : Theme.text3
                            tip: row.confirming ? "Click again to remove" : "Remove"
                            onClicked: {
                                if (!row.confirming) { row.confirming = true; undo.restart(); return }
                                Api.post(`/api/plugins/${row.modelData.name}/delete`, {}, () => { Backend.toast("Plugin removed", false); page.load() })
                            }
                            Timer { id: undo; interval: 4000; onTriggered: row.confirming = false }
                        }
                    }
                }
            }
        }
    }

    Section {
        title: "Add a plugin"
        description: "Start from a quick pick, or fill in any MCP server. Jarvis connects to it as soon as it's added."
        Flow {
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: [["Home Assistant", "homeassistant", "url", "http://homeassistant.local:8123/api/mcp",
                         "{\"Authorization\": \"Bearer PASTE-A-LONG-LIVED-TOKEN (your profile → Security)\"}"],
                        ["Notion", "notion", "url", "https://mcp.notion.com/mcp"],
                        ["Context7 docs", "context7", "url", "https://mcp.context7.com/mcp"],
                        ["Home folder files", "files", "command", "npx -y @modelcontextprotocol/server-filesystem ~"],
                        ["Playwright browser", "playwright", "command", "npx -y @playwright/mcp@latest --headless"]]
                Chip { required property var modelData; symbol: "plus"; text: modelData[0]; checked: pname.text === modelData[1]
                       onClicked: page.preset(modelData[1], modelData[2], modelData[3], modelData[4]) }
            }
        }
        GridLayout {  // two rows that share their column edges
            Layout.fillWidth: true
            Layout.topMargin: 4
            columns: 3
            columnSpacing: 12
            rowSpacing: 8
            Txt { kind: "label"; text: "Name" }
            Txt { kind: "label"; text: "Type" }
            Txt { kind: "label"; text: page.kind === "url" ? "Address" : "Command" }
            Field { id: pname; Layout.preferredWidth: 180; placeholderText: "e.g. notion" }
            Select {
                Layout.preferredWidth: 160
                model: [{ value: "url", label: "Web address" }, { value: "command", label: "Command" }]
                value: page.kind
                onPicked: v => page.kind = v
            }
            Field { id: target; Layout.fillWidth: true; placeholderText: page.kind === "url" ? "https://example.com/mcp" : "npx -y some-mcp-server" }
            Txt { kind: "label"; text: "Only these tools (optional)"; Layout.columnSpan: 2; Layout.topMargin: 8 }
            Txt { kind: "label"; text: page.kind === "url" ? "Headers (optional)" : "Environment (optional)"; Layout.topMargin: 8 }
            Field { id: only; Layout.columnSpan: 2; Layout.preferredWidth: 352; placeholderText: "comma-separated names" }
            Field { id: extra; Layout.fillWidth: true
                    placeholderText: page.kind === "url" ? "JSON, e.g. {\"Authorization\": \"Bearer …\"}" : "JSON, e.g. {\"API_KEY\": \"…\"}" }
        }
        Pill {
            Layout.alignment: Qt.AlignRight
            text: "Add plugin"
            kind: enabled ? "primary" : ""
            symbol: "plus"
            enabled: pname.text.trim() !== "" && target.text.trim() !== ""
            onClicked: Api.post("/api/plugins", Object.assign({ name: pname.text, tools: only.text },
                                                              page.kind === "url" ? { url: target.text, headers: extra.text } : { command: target.text, env: extra.text }),
                                () => { Backend.toast("Plugin added: connecting…", false); pname.text = target.text = extra.text = only.text = ""; page.load() })
        }
    }
}
