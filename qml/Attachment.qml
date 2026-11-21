import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import Jarvis

// A file attached to a message: a picture as its thumbnail, anything else as a tile with its type, name and size (one
// that's gone stays a plain tile). A click (or Enter) opens it with its default app; `removable` adds a remove button.
AbstractButton {
    id: t
    required property string path
    property bool removable: false
    property int side: 56  // a picture's thumbnail (other tiles are 56 high)
    signal removed()
    readonly property var info: Backend.fileInfo(path)
    readonly property bool picture: info.kind === "picture" && thumb.status !== Image.Error
    readonly property string symbol: ({ picture: "image", audio: "music", video: "film", folder: "folder" })[info.kind] || "note"
    readonly property string detail: !info.exists ? qsTr("Moved or deleted") : info.kind === "folder" ? qsTr("Folder")
                                   : [info.ext, info.size].filter(s => s !== "").join(" · ")
    implicitWidth: picture ? side : Theme.fileTile
    implicitHeight: picture ? side : 56
    hoverEnabled: true
    focusPolicy: Qt.TabFocus  // (Tab reaches it; a click leaves the typing where it was)
    Keys.onReturnPressed: click()
    Keys.onEnterPressed: click()
    Keys.onDeletePressed: if (removable) removed()
    Accessible.name: info.name + ", " + detail
    onClicked: Backend.openFile(path)
    Tip { text: t.info.name; visible: (t.hovered || t.visualFocus) && !remove.hovered && (t.picture || name.truncated) }
    HoverHandler { cursorShape: Qt.PointingHandCursor }

    background: Rectangle {
        radius: 12
        color: t.picture ? "transparent" : t.hovered ? Theme.glassHover : Theme.glass
        border.width: t.picture ? 0 : 1
        border.color: t.hovered ? Theme.strokeStrong : Theme.stroke
        Behavior on color { ColorAnimation { duration: Theme.fast } }
        Focus { keyboard: true; visible: t.visualFocus }
    }
    contentItem: Item {
        Image {
            id: thumb
            anchors.fill: parent
            visible: t.picture
            source: t.info.kind === "picture" ? Backend.fileUrl(t.path) : ""
            fillMode: Image.PreserveAspectCrop
            sourceSize: Qt.size(t.side * 2, t.side * 2)  // (sharp on a 2x screen, and a big photo isn't kept whole)
            asynchronous: true
            layer.enabled: GraphicsInfo.api !== GraphicsInfo.Software  // (rounded by a shader: the software renderer has none)
            layer.effect: MultiEffect { maskEnabled: true; maskSource: mask; maskThresholdMin: 0.5; maskSpreadAtMin: 1 }
        }
        Rectangle { id: mask; anchors.fill: parent; radius: 12; visible: false; layer.enabled: true }
        Rectangle {  // a picture's edge, lit under the mouse
            anchors.fill: parent
            visible: t.picture
            radius: 12
            color: t.hovered ? Theme.alpha(Theme.text, 0.08) : "transparent"
            border.width: 1
            border.color: t.hovered ? Theme.alpha(Theme.text, 0.3) : Theme.strokeStrong
            Behavior on color { ColorAnimation { duration: Theme.fast } }
        }

        Rectangle {  // the type
            id: well
            visible: !t.picture
            anchors { left: parent.left; leftMargin: 8; verticalCenter: parent.verticalCenter }
            width: 40; height: 40; radius: 10
            color: t.info.exists ? Theme.accentSoft : Theme.glass
            Icon { anchors.centerIn: parent; name: t.symbol; size: 20; color: t.info.exists ? Theme.accent : Theme.text3 }
        }
        Column {
            visible: !t.picture
            anchors { left: well.right; leftMargin: 10; right: remove.visible ? remove.left : parent.right; rightMargin: remove.visible ? 2 : 12
                      verticalCenter: parent.verticalCenter }
            spacing: 2
            Txt { id: name; width: parent.width; text: t.info.name; weight: 500; font.pixelSize: Theme.px(13); wrapMode: Text.NoWrap
                  elide: Text.ElideMiddle; color: t.info.exists ? Theme.text : Theme.text2 }
            Txt { width: parent.width; text: t.detail; kind: "small"; font.pixelSize: Theme.px(12); wrapMode: Text.NoWrap; elide: Text.ElideRight
                  color: t.info.exists ? Theme.text2 : Theme.text3 }
        }
        IconButton {
            id: remove
            visible: t.removable
            anchors { right: parent.right; rightMargin: t.picture ? -6 : 6; top: t.picture ? parent.top : undefined; topMargin: -6
                      verticalCenter: t.picture ? undefined : parent.verticalCenter }  // (out of a picture's corner: less of it hidden)
            size: 24; glyph: 12; symbol: "close"
            tint: t.picture ? Theme.popover : "transparent"
            iconColor: t.picture || hovered ? Theme.text : Theme.text2
            tip: qsTr("Remove %1").arg(t.info.name)
            onClicked: t.removed()
            Rectangle {  // (its edge: off the picture it would melt into the glass around)
                anchors.fill: parent
                visible: t.picture
                radius: width / 2
                color: "transparent"
                border.width: 1
                border.color: parent.hovered ? Theme.alpha(Theme.text, 0.35) : Theme.strokeStrong
            }
        }
    }
    scale: down ? 0.97 : 1
    Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
}
