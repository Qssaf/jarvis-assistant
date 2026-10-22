import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Jarvis

// Is everything Jarvis needs working? Each check says what's wrong and where to fix it, plus today's model use.
ScrollPage {
    id: page
    title: "Health"
    hint: "Checks the key, mic, screen, accounts and models, and how to fix them."
    signal goTo(string key)
    property var checks: []
    property var usage: ({})
    property bool running: false

    function run() {
        running = true
        Api.get("/api/health", d => { checks = d.checks; usage = d.usage; running = false },
                e => { running = false; Backend.toast(e.error, true) })
    }
    readonly property int problems: checks.filter(c => c.ok === false).length
    readonly property var models: Object.keys(usage).sort((a, b) => usage[b] - usage[a])
    Component.onCompleted: run()

    actions: [
        Pill { text: "Copy a report"; symbol: "copy"
               onClicked: Api.get("/api/report", d => { Backend.copy(d.text); Backend.toast("Copied. Look it over, then paste it into a bug report", false) },
                                  e => Backend.toast(e.error, true)) },
        Pill { text: "Report a problem"; symbol: "external"; onClicked: Qt.openUrlExternally("https://github.com/Qssaf/jarvis-assistant/issues/new") }
    ]

    Card {
        Layout.fillWidth: true
        ColumnLayout {
            width: parent.width
            spacing: 0
            RowLayout {  // the verdict
                Layout.fillWidth: true
                Layout.bottomMargin: 16
                spacing: 16
                Rectangle {
                    readonly property color tone: page.running ? Theme.accent : page.problems ? Theme.red : Theme.green
                    Layout.preferredWidth: 40; Layout.preferredHeight: 40; radius: 20
                    color: Theme.alpha(tone, 0.14)
                    Icon { anchors.centerIn: parent; size: 18; color: parent.tone
                           name: page.running ? "refresh" : page.problems ? "alert" : "check" }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Txt { kind: "heading"; Layout.fillWidth: true
                          text: page.running ? "Checking…" : page.problems ? `${page.problems} thing${page.problems > 1 ? "s" : ""} to fix` : "Everything works" }
                    Txt { kind: "small"; Layout.fillWidth: true; visible: page.checks.length > 0
                          text: `${page.checks.length - page.problems} of ${page.checks.length} checks pass` }
                }
                Pill { text: "Check again"; symbol: "refresh"; enabled: !page.running; onClicked: page.run() }
            }
            Repeater {
                model: page.checks
                ColumnLayout {
                    required property var modelData
                    readonly property bool bad: modelData.ok === false
                    Layout.fillWidth: true
                    spacing: 0
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.stroke }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: 8; Layout.bottomMargin: 8
                        Layout.minimumHeight: 40  // (56 with the margins)
                        spacing: 16
                        StatusDot { Layout.alignment: Qt.AlignTop; Layout.topMargin: 6  // (lines up with the name)
                                    status: modelData.ok === true ? "ok" : modelData.ok === false ? "error" : "off" }
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignTop
                            spacing: 2
                            Txt { text: modelData.name; weight: 500; Layout.fillWidth: true }
                            Txt { kind: "small"; text: modelData.detail; Layout.fillWidth: true }
                            Txt { kind: "small"; visible: !!modelData.fix; text: "Fix: " + modelData.fix; Layout.fillWidth: true }
                        }
                        Pill { visible: !!modelData.page && bad; symbol: "arrow-right"; onClicked: page.goTo(modelData.page)
                               text: { const to = modelData.page || ""; return "Open " + to.charAt(0).toUpperCase() + to.slice(1) } }
                    }
                }
            }
        }
    }

    Section {
        title: "Model use today"
        description: "Free Google AI Studio keys allow a limited number of requests per model each day. When one runs out, Jarvis "
                     + "uses the next model in that job's list (the Models page) until the quota resets at midnight Pacific time."
        ColumnLayout {
            Layout.fillWidth: true
            Layout.topMargin: page.models.length ? -8 : 0; Layout.bottomMargin: page.models.length ? -12 : 0  // (rows carry their own space)
            spacing: 0
            Repeater {
                model: page.models
                ColumnLayout {
                    required property string modelData
                    required property int index
                    readonly property var parts: modelData.split(" ")
                    Layout.fillWidth: true
                    spacing: 0
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.stroke; visible: index > 0 }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 52
                        spacing: 8
                        Txt { text: parts.slice(1).join(" ") || modelData; weight: 500; wrapMode: Text.NoWrap; elide: Text.ElideRight
                              Layout.fillWidth: parts.length < 2 }
                        Txt { kind: "small"; text: parts[0]; color: Theme.text3; visible: parts.length > 1; Layout.fillWidth: true }
                        Txt { text: page.usage[modelData]; weight: 600; font.features: { "tnum": 1 } }
                        Txt { kind: "small"; text: page.usage[modelData] === 1 ? "request" : "requests" }
                    }
                }
            }
            Txt { kind: "small"; visible: !page.models.length; text: "No requests yet today."; color: Theme.text3 }
        }
    }
}
