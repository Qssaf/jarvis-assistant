import QtQuick
import QtQuick.Layouts

// A titled glass card for a page: heading, an optional line under it, then the content in a column.
Card {
    id: s
    property string title
    property string description
    default property alias body: col.data
    property alias spacing: col.spacing
    Layout.fillWidth: true
    ColumnLayout {
        id: col
        width: parent.width
        spacing: 16
        ColumnLayout {
            Layout.fillWidth: true
            Layout.bottomMargin: -4
            spacing: 4
            visible: s.title !== "" || s.description !== ""
            Txt { kind: "heading"; text: s.title; visible: text !== ""; Layout.fillWidth: true }
            Txt { kind: "small"; text: s.description; visible: text !== ""; Layout.fillWidth: true }
        }
    }
}
