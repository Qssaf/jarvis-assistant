import QtQuick
import QtQuick.Layouts
import Jarvis

// One line of the conversation: your words on the right, Jarvis's on the left, tools and notices quietly in between.
Item {
    id: m
    required property string who
    required property string text
    required property string caption
    required property real time
    readonly property bool mine: who === "you"
    readonly property real column: Math.min(width - 56, 760)
    implicitHeight: body.implicitHeight + (who === "tool" || who === "thinking" ? 0 : 6)

    function linkify(t) {  // plain text with links made clickable, for Markdown
        return t.replace(/(^|\s)(https?:\/\/[^\s<>()]+)/g, "$1<$2>")
    }

    Loader {
        id: body
        anchors.horizontalCenter: parent.horizontalCenter
        width: m.column
        sourceComponent: m.who === "you" ? you : m.who === "jarvis" ? jarvis : m.who === "image" ? picture : m.who === "tool" ? tool : notice
    }

    Component {
        id: you
        Item {
            implicitHeight: bubble.height + 8
            Rectangle {
                id: bubble
                anchors.right: parent.right
                y: 8
                width: Math.min(words.implicitWidth + 32, parent.width * 0.78)
                height: words.implicitHeight + 20
                radius: 18
                bottomRightRadius: 6
                color: Theme.alpha(Theme.accent, 0.2)
                border.width: 1
                border.color: Theme.alpha(Theme.accent, 0.28)
                Txt { id: words; anchors.centerIn: parent; width: parent.width - 32; text: m.text; textFormat: Text.PlainText }
            }
        }
    }
    Component {
        id: jarvis
        RowLayout {
            spacing: 12
            Orb { Layout.alignment: Qt.AlignTop; Layout.topMargin: 10; Layout.preferredWidth: 26; Layout.preferredHeight: 26; rings: false; mode: "idle" }
            Txt {
                id: said
                Layout.fillWidth: true
                Layout.topMargin: 12
                text: m.linkify(m.text)
                textFormat: Text.MarkdownText
                font.pixelSize: 15
                lineHeight: 1.18
                HoverHandler { id: hover }
                IconButton {
                    anchors { right: parent.right; top: parent.top; topMargin: -6 }
                    visible: hover.hovered
                    size: 26; glyph: 13; symbol: "copy"; tip: "Copy"
                    onClicked: Backend.copy(m.text)
                }
            }
        }
    }
    Component {
        id: tool
        Row {
            leftPadding: 38
            spacing: 7
            Rectangle { width: 6; height: 6; radius: 3; color: Theme.warm; anchors.verticalCenter: parent.verticalCenter; opacity: 0.8 }
            Txt { kind: "small"; text: Backend.toolLabel(m.text); color: Theme.faint; wrapMode: Text.NoWrap }
        }
    }
    Component {
        id: notice
        Rectangle {
            implicitHeight: words.implicitHeight + 18
            radius: 12
            color: m.who === "thinking" ? "transparent" : Theme.alpha(Theme.card, 0.8)
            border.width: m.who === "thinking" ? 0 : 1
            border.color: Theme.line
            Txt {
                id: words
                anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; leftMargin: m.who === "thinking" ? 38 : 14; rightMargin: 14 }
                kind: "small"
                font.italic: m.who === "thinking"
                text: m.linkify(m.text)
                textFormat: Text.MarkdownText
            }
        }
    }
    Component {
        id: picture
        Column {
            leftPadding: 38
            topPadding: 8
            spacing: 6
            Rectangle {
                width: Math.min(img.implicitWidth, 420); height: width * (img.implicitHeight / Math.max(1, img.implicitWidth))
                radius: 14
                clip: true
                color: Theme.card
                Image {
                    id: img
                    anchors.fill: parent
                    source: "file://" + m.text
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                    sourceSize.width: 840
                }
                TapHandler { onTapped: Backend.open(m.text) }
                HoverHandler { cursorShape: Qt.PointingHandCursor }
            }
            Txt { kind: "small"; text: m.caption; visible: m.caption !== ""; width: 420 }
        }
    }
}
