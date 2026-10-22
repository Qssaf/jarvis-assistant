import QtQuick
import QtQuick.Layouts

// A page's title, the line under it, and buttons on the right, centred on the title line.
RowLayout {
    property string title
    property string hint
    default property alias actions: actionRow.data
    spacing: 16
    ColumnLayout {
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignTop
        Layout.topMargin: Math.max(0, (actionRow.height - titleText.height) / 2)
        spacing: 6
        Txt { id: titleText; kind: "title"; text: title; Layout.fillWidth: true }
        Txt { kind: "small"; text: hint; visible: hint !== ""; font.pixelSize: Theme.px(14); Layout.fillWidth: true }
    }
    Row {
        id: actionRow
        spacing: 8
        Layout.alignment: Qt.AlignTop
        Layout.topMargin: Math.max(0, (titleText.height - height) / 2)
    }
}
