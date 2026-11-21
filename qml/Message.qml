import QtQuick
import QtQuick.Effects
import Jarvis

// One line of the conversation: your words on the right, Jarvis's on the left, tools and notices quietly in between.
Item {
    id: m
    required property string who
    required property string text
    required property string caption
    required property real time
    readonly property bool mine: who === "you"
    property real column: Math.min(width - 80, 760)
    property real rise: 0  // (the list animates new messages in with it)
    readonly property int thumb: 88  // a picture you sent, as a thumbnail
    readonly property int gap: who === "you" ? 20 : who === "jarvis" ? 10 : who === "system" ? 14 : who === "thinking" ? 4 : 8
    implicitHeight: body.implicitHeight + gap
    transform: Translate { y: m.rise }

    function linkify(t) {  // plain text with links made clickable, for Markdown
        return t.replace(/(^|\s)(https?:\/\/[^\s<>()]+)/g, "$1<$2>")
    }

    HoverHandler { id: hover }
    Loader {
        id: body
        x: (m.width - m.column) / 2
        y: m.gap
        width: m.column
        sourceComponent: m.who === "you" ? you : m.who === "jarvis" ? jarvis : m.who === "image" ? picture : m.who === "tool" ? tool
                       : m.who === "system" ? note : thinking
    }

    Component {
        id: you
        Item {
            id: mine
            readonly property var sent: Backend.attachedIn(m.text)  // (files go as "(attached: path)" notes: shown as tiles)
            readonly property real most: width * 0.7
            readonly property var rows: {  // the tiles in lines as wide as the bubble's widest, each against the bubble's side
                const out = [[]]
                let used = 0
                for (const path of sent.files) {
                    const wide = Backend.fileInfo(path).kind === "picture" ? m.thumb : Theme.fileTile
                    if (out[out.length - 1].length && used + 8 + wide > most) {
                        out.push([])
                        used = 0
                    }
                    used += (out[out.length - 1].length ? 8 : 0) + wide
                    out[out.length - 1].push(path)
                }
                return out
            }
            implicitHeight: stack.implicitHeight
            Column {
                id: stack
                anchors.right: parent.right
                spacing: 6
                Repeater {
                    model: mine.sent.files.length ? mine.rows : []
                    Row {
                        required property var modelData
                        anchors.right: parent.right
                        spacing: 8
                        Repeater { model: parent.modelData; Attachment { required property string modelData; path: modelData; side: m.thumb } }
                    }
                }
                Rectangle {
                    id: bubble
                    anchors.right: parent.right
                    visible: mine.sent.text !== ""
                    width: Math.min(words.implicitWidth, mine.most - 32) + 32
                    height: words.implicitHeight + 22
                    radius: Theme.radius
                    bottomRightRadius: 6
                    color: Theme.accentSoft
                    border.width: 1
                    border.color: Theme.alpha(Theme.accent, 0.25)
                    Txt { id: words; x: 16; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 32
                          text: mine.sent.text; textFormat: Text.PlainText; font.pixelSize: Theme.px(15); lineHeight: 1.1
                          horizontalAlignment: undefined }  // (a message goes the way its own words read)
                }
            }
        }
    }
    Component {
        id: jarvis
        Item {
            implicitHeight: Math.max(24, said.implicitHeight)
            Orb { anchors.left: parent.left; width: 24; height: 24; y: 1; rings: false; mode: "idle" }
            TextEdit {  // (not a Txt: a part of the reply can be selected and copied)
                id: said
                objectName: "reply"
                anchors { left: parent.left; leftMargin: 36; right: parent.right }
                text: m.linkify(m.text)
                textFormat: TextEdit.MarkdownText
                readOnly: true
                selectByMouse: true
                wrapMode: TextEdit.Wrap
                font.family: Theme.font
                font.pixelSize: Theme.px(15)
                font.weight: 400
                font.variableAxes: ({ "wght": 400 })
                color: Theme.text
                selectionColor: Theme.alpha(Theme.accent, 0.4)
                selectedTextColor: Theme.text
                Component.onCompleted: Backend.spaceLines(textDocument, 1.3)  // (as Txt's lineHeight: TextEdit has none)
                onLinkActivated: link => { if (/^(https?|mailto):/i.test(link)) Qt.openUrlExternally(link) }  // (as Txt's)
                HoverHandler { cursorShape: said.hoveredLink ? Qt.PointingHandCursor : Qt.IBeamCursor }
            }
            IconButton {
                anchors { left: parent.right; leftMargin: 8 }
                opacity: hover.hovered || activeFocus ? 1 : 0  // (Tab reaches it: it shows then too)
                Behavior on opacity { NumberAnimation { duration: Theme.fast } }
                size: 28; glyph: 14; symbol: "copy"; tip: qsTr("Copy")
                onClicked: Backend.copy(m.text)
            }
        }
    }
    Component {
        id: tool
        Item {
            implicitHeight: 28
            Chip { anchors { left: parent.left; leftMargin: 36 } implicitHeight: 28; enabled: false; dot: "working"; text: Backend.toolLabel(m.text) }
        }
    }
    Component {
        id: note
        Item {
            implicitHeight: words.implicitHeight + 12
            Rectangle {
                anchors.centerIn: parent
                width: Math.min(words.implicitWidth, parent.width - 28) + 28
                height: parent.height
                radius: height / 2
                color: Theme.alpha(Theme.glass, 0.7)
                border.width: 1
                border.color: Theme.alpha(Theme.stroke, 0.7)
                Txt {
                    id: words
                    anchors.centerIn: parent
                    width: Math.min(implicitWidth, parent.parent.width - 28)
                    kind: "small"
                    color: Theme.text2
                    horizontalAlignment: Text.AlignHCenter
                    // (without the emoji background notices start with: they clash with the line icons)
                    text: m.linkify(m.text.replace(/^(?:[\u2300-\u27bf\u2b00-\u2bff]|[\ud83c-\ud83e][\udc00-\udfff])\ufe0f?\s*/, ""))
                    textFormat: Text.MarkdownText
                }
            }
        }
    }
    Component {
        id: thinking
        Item {
            implicitHeight: words.implicitHeight
            Txt { id: words; anchors { left: parent.left; leftMargin: 36; right: parent.right }
                  kind: "small"; color: Theme.text3; font.italic: true; text: m.linkify(m.text); textFormat: Text.MarkdownText
                  horizontalAlignment: undefined }
        }
    }
    Component {
        id: picture
        Item {
            implicitHeight: shown.implicitHeight
            Column {
                id: shown
                anchors { left: parent.left; leftMargin: 36 }
                topPadding: 4
                spacing: 8
                Item {
                    width: Math.min(img.implicitWidth, 420); height: width * (img.implicitHeight / Math.max(1, img.implicitWidth))
                    Image {
                        id: img
                        anchors.fill: parent
                        source: Backend.fileUrl(m.text)
                        fillMode: Image.PreserveAspectFit
                        asynchronous: true
                        sourceSize.width: 840
                        layer.enabled: true
                        layer.effect: MultiEffect { maskEnabled: true; maskSource: mask; maskThresholdMin: 0.5; maskSpreadAtMin: 1 }
                    }
                    Rectangle { id: mask; anchors.fill: parent; radius: 16; visible: false; layer.enabled: true }
                    Rectangle { anchors.fill: parent; radius: 16; color: "transparent"; border.width: 1; border.color: Theme.stroke }
                    TapHandler { onTapped: Backend.openImage(m.text) }
                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                }
                Txt { kind: "small"; text: m.caption; visible: m.caption !== ""; width: 420 }
            }
        }
    }
}
