import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// A scrolling page: its header, then the content in a column.
Item {
    id: p
    property string title
    property string hint
    default property alias content: column.data
    property alias actions: header.actions
    property int maxWidth: 1000

    ScrollView {
        id: sv
        anchors { fill: parent; topMargin: 46 }
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            id: column
            x: 34
            width: Math.min(sv.availableWidth - 68, p.maxWidth)
            spacing: 14
            PageHeader { id: header; Layout.fillWidth: true; Layout.bottomMargin: 6; title: p.title; hint: p.hint }
        }
    }
}
