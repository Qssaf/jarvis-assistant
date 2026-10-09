import QtQuick
import QtQuick.Layouts

// A page's title, the line under it, and buttons on the right.
RowLayout {
    property string title
    property string hint
    default property alias actions: actionRow.data
    spacing: 12
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 4
        Txt { kind: "title"; text: title }
        Txt { kind: "small"; text: hint; visible: hint !== ""; font.pixelSize: 14; Layout.fillWidth: true }
    }
    Row { id: actionRow; spacing: 8; Layout.alignment: Qt.AlignBottom }
}
