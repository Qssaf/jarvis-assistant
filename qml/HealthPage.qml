import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Jarvis

// Is everything Jarvis needs working? Each check says what's wrong and where to fix it, plus today's model use.
ScrollPage {
    id: page
    title: "Health"
    hint: "The key, the microphone, the screen, mouse and keyboard, accounts and models. Anything red says how to fix it."
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
    Component.onCompleted: run()

    RowLayout {
        Layout.fillWidth: true
        spacing: 10
        Txt { kind: "small"; Layout.fillWidth: true
              text: page.running ? "Checking…" : page.problems ? `${page.problems} thing${page.problems > 1 ? "s" : ""} to fix` : "Everything works" }
        Pill { text: "Copy a report"; symbol: "copy"
               onClicked: Api.get("/api/report", d => { Backend.copy(d.text); Backend.toast("Copied. Look it over, then paste it into a bug report", false) },
                                  e => Backend.toast(e.error, true)) }
        Pill { text: "Report a problem"; symbol: "external"; onClicked: Qt.openUrlExternally("https://github.com/Qssaf/jarvis-assistant/issues/new") }
        Pill { text: "Check again"; symbol: "refresh"; enabled: !page.running; onClicked: page.run() }
    }

    Card {
        Layout.fillWidth: true
        padding: 22
        ColumnLayout {
            width: parent.width
            spacing: 14
            Repeater {
                model: page.checks
                RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 12
                    Rectangle {
                        Layout.preferredWidth: 10; Layout.preferredHeight: 10; radius: 5
                        Layout.alignment: Qt.AlignTop; Layout.topMargin: 5
                        color: modelData.ok === true ? Theme.green : modelData.ok === false ? Theme.red : Theme.faint
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Txt { text: modelData.name; font.weight: Font.DemiBold }
                        Txt { kind: "small"; text: modelData.detail; Layout.fillWidth: true }
                        Txt { kind: "small"; visible: !!modelData.fix; text: "Fix: " + modelData.fix; color: Theme.warm; Layout.fillWidth: true }
                    }
                    Pill { visible: !!modelData.page && modelData.ok === false; text: "Open"; onClicked: page.goTo(modelData.page) }
                }
            }
        }
    }

    Card {
        Layout.fillWidth: true
        padding: 22
        ColumnLayout {
            width: parent.width
            spacing: 10
            Txt { kind: "heading"; text: "Model use today" }
            Txt { kind: "small"; Layout.fillWidth: true
                  text: "Free Google AI Studio keys allow a limited number of requests per model each day. When one runs out, Jarvis "
                        + "uses the next model in that job's list (the Models page) until the quota resets at midnight Pacific time." }
            Repeater {
                model: Object.keys(page.usage).sort((a, b) => page.usage[b] - page.usage[a])
                RowLayout {
                    required property string modelData
                    Layout.fillWidth: true
                    Txt { text: modelData; Layout.fillWidth: true; font.family: Theme.mono; font.pixelSize: 12 }
                    Txt { text: page.usage[modelData] + " requests"; color: Theme.accent; font.pixelSize: 13 }
                }
            }
            Txt { kind: "small"; visible: !Object.keys(page.usage).length; text: "No requests yet today." }
        }
    }
    Item { Layout.preferredHeight: 24 }
}
