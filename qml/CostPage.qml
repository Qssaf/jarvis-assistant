import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Jarvis

// What Jarvis's model use would cost at Google's paid-tier prices (the free key and Google sign-ins bill nothing): the
// period's total, a bar per day, and a row per model, costliest first.
ScrollPage {
    id: page
    objectName: "costPage"
    title: qsTr("Cost")
    hint: qsTr("What Jarvis's model use would cost at Google's paid-tier prices.")
    property int days: 1
    property var report: ({ total: 0, tokens: 0, unpriced: 0, unmeasured: 0, days: [], models: [] })
    readonly property real most: Math.max(...report.days.map(d => d.cost), 0)

    function load() { Api.get("/api/cost?days=" + days, d => report = d, e => Backend.toast(e.error, true)) }
    function money(c) {  // (cents; a few calls cost fractions of one, which mustn't read as free)
        return c === null ? qsTr("no price") : c > 0 && c < 0.0001 ? "<$0.0001" : "$" + (c > 0 && c < 0.01 ? c.toFixed(4) : c.toFixed(2))
    }
    function count(n) {
        return n >= 1e6 ? (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(n >= 1e4 ? 0 : 1) + "K" : String(n)
    }
    function dayName(stamp) { return Qt.formatDate(new Date(stamp + "T12:00:00"), page.days > 7 ? "d MMM" : "ddd") }
    onDaysChanged: load()
    onVisibleChanged: if (visible) load()
    Component.onCompleted: load()

    actions: [
        Repeater {
            model: [[1, qsTr("Today")], [7, qsTr("7 days")], [30, qsTr("30 days")]]
            Chip { required property var modelData; text: modelData[1]; checked: page.days === modelData[0]; onClicked: page.days = modelData[0]
                   Accessible.role: Accessible.RadioButton; Accessible.checkable: true; Accessible.checked: checked }
        }
    ]

    Card {
        Layout.fillWidth: true
        ColumnLayout {
            width: parent.width
            spacing: 18
            RowLayout {
                Layout.fillWidth: true
                spacing: 16
                Rectangle {
                    Layout.preferredWidth: 40; Layout.preferredHeight: 40; radius: 20
                    Layout.alignment: Qt.AlignTop
                    color: Theme.accentSoft
                    Icon { anchors.centerIn: parent; size: 18; color: Theme.accent; name: "coin" }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Txt { kind: "title"; text: page.money(page.report.total); font.features: { "tnum": 1 }; Layout.fillWidth: true }
                    Txt { kind: "small"; Layout.fillWidth: true
                          text: qsTr("%1 tokens at paid-tier prices").arg(page.count(page.report.tokens)) }
                    Txt { kind: "small"; Layout.fillWidth: true; color: Theme.warm; visible: page.report.unmeasured > 0
                          text: qsTr("%n request(s) came back without token counts (most from before Jarvis started counting them), so they aren't in the total.", "", page.report.unmeasured) }
                }
            }
            // a bar per day: how the period's cost was spread
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 120
                visible: page.days > 1
                Row {
                    id: bars
                    anchors.fill: parent
                    spacing: page.days > 7 ? 4 : 10
                    readonly property real each: (width - spacing * (page.report.days.length - 1)) / Math.max(page.report.days.length, 1)
                    Repeater {
                        model: page.report.days
                        Item {
                            id: bar
                            required property var modelData
                            required property int index
                            width: bars.each
                            height: bars.height
                            readonly property bool last: index === page.report.days.length - 1
                            readonly property string said: qsTr("%1: %2").arg(Qt.formatDate(new Date(modelData.day + "T12:00:00"), "ddd d MMM"))
                                                                      .arg(page.money(modelData.cost))
                            Accessible.role: Accessible.StaticText  // (the tooltip is hover-only: screen readers get it here)
                            Accessible.name: said
                            Rectangle {
                                anchors { bottom: label.top; bottomMargin: 6; left: parent.left; right: parent.right }
                                height: Math.max(3, (parent.height - label.height - 6) * (page.most ? bar.modelData.cost / page.most : 0))
                                radius: Math.min(4, width / 2)
                                color: bar.modelData.cost > 0 ? (bar.last ? Theme.accent : Theme.alpha(Theme.accent, 0.45)) : Theme.track
                                Behavior on height { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
                            }
                            Txt {
                                id: label
                                anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter }
                                kind: "small"; color: bar.last ? Theme.text2 : Theme.text3
                                text: page.dayName(bar.modelData.day)
                                visible: page.days <= 7 || bar.index % 5 === (page.report.days.length - 1) % 5  // (every fifth of 30)
                            }
                            HoverHandler { id: over }
                            Tip { visible: over.hovered; text: bar.said }
                        }
                    }
                }
            }
            Txt {
                kind: "small"; Layout.fillWidth: true; color: Theme.text3
                text: qsTr("Nothing is billed on the free tier or through a Google sign-in: this is what the same use would cost with "
                           + "billing on. Google Search fees aren't counted.")
            }
        }
    }

    Section {
        title: qsTr("By model")
        description: page.report.unpriced ? qsTr("%n model(s) have no known price, so they aren't in the total.", "", page.report.unpriced) : ""
        ColumnLayout {
            Layout.fillWidth: true
            Layout.topMargin: page.report.models.length ? -8 : 0; Layout.bottomMargin: page.report.models.length ? -12 : 0
            spacing: 0
            Repeater {
                model: page.report.models
                ColumnLayout {
                    id: row
                    required property var modelData
                    required property int index
                    readonly property var parts: modelData.key.split(" ")
                    Layout.fillWidth: true
                    spacing: 0
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.stroke; visible: row.index > 0 }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 56
                        spacing: 12
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 1
                            Txt { text: row.parts.slice(1).join(" ") || row.modelData.key; weight: 500; elide: Text.ElideRight
                                  wrapMode: Text.NoWrap; Layout.fillWidth: true }
                            Txt { kind: "small"; color: Theme.text3; Layout.fillWidth: true
                                  text: qsTr("%1 · %n request(s)", "", row.modelData.requests).arg(Api.provider(row.parts[0])) }
                        }
                        Txt { kind: "small"; font.features: { "tnum": 1 }
                              text: qsTr("%1 in · %2 out").arg(page.count(row.modelData.input)).arg(page.count(row.modelData.output)) }
                        Txt { text: page.money(row.modelData.cost); weight: 600; font.features: { "tnum": 1 }
                              color: row.modelData.cost === null ? Theme.text3 : Theme.text
                              horizontalAlignment: Text.AlignRight; Layout.preferredWidth: 72 }
                    }
                }
            }
            Txt { kind: "small"; visible: !page.report.models.length; color: Theme.text3
                  text: page.days === 1 ? qsTr("No model use yet today.") : qsTr("No model use in this period.") }
        }
    }
}
