import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// A scrolling page: its header, then the content in a column (at most `maxWidth` wide, centred).
Item {
    id: p
    property string title
    property string hint
    default property alias content: column.data
    property alias actions: header.actions
    property int maxWidth: Theme.pageWidth
    property bool index: false  // a long page (Settings): its sections listed beside it, to jump to one
    readonly property bool indexed: index && sv.availableWidth >= 860 && sections.length > 1
    readonly property int side: indexed ? 220 : 0  // the list and the gap after it
    readonly property var sections: {
        let out = []
        for (const c of column.children)
            if (c.description !== undefined && c.title && c.visible) out.push(c)  // (a Section)
        return out
    }
    property int picked: -1  // the one just jumped to (the last ones can't reach the top), until the user scrolls
    readonly property int currentSection: {
        if (picked >= 0) return picked
        let now = 0
        for (let i = 0; i < sections.length; i++)
            if (sections[i].y <= sv.contentItem.contentY + 120) now = i
        return now
    }
    function jump(i) {
        glide.to = Math.max(0, Math.min(sections[i].y - Theme.margin, sv.contentHeight - sv.height))
        glide.restart()
        picked = i
    }
    NumberAnimation { id: glide; target: sv.contentItem; property: "contentY"; duration: 260; easing.type: Easing.OutCubic }
    Connections {  // a control Tab reaches that's out of sight is scrolled into view
        target: p.Window.window
        function onActiveFocusItemChanged() {
            const item = p.Window.window.activeFocusItem
            if (!item || !(item.focusReason === Qt.TabFocusReason || item.focusReason === Qt.BacktabFocusReason)) return
            for (let up = item.parent; up !== column; up = up.parent)
                if (!up) return  // (not on this page)
            const y = item.mapToItem(column, 0, 0).y, top = sv.contentItem.contentY
            if (y < top + Theme.margin) sv.contentItem.contentY = Math.max(0, y - Theme.margin)
            else if (y + item.height > top + sv.height - Theme.margin) sv.contentItem.contentY = y + item.height - sv.height + Theme.margin
        }
    }
    Connections {
        target: sv.contentItem
        function onContentYChanged() { if (!glide.running) p.picked = -1 }
    }

    ScrollView {
        id: sv
        anchors.fill: parent
        contentWidth: availableWidth
        contentHeight: column.implicitHeight + Theme.margin
        clip: true
        ScrollBar.vertical: Scroller { parent: sv; x: sv.width - width; height: sv.availableHeight }
        ColumnLayout {
            id: column
            width: Math.min(sv.availableWidth - 2 * Theme.margin - p.side, p.maxWidth)
            x: (sv.availableWidth - width - p.side) / 2 + (p.LayoutMirroring.enabled ? 0 : p.side)
            spacing: Theme.gap
            Item { Layout.preferredHeight: Theme.margin - Theme.gap }  // (the top margin; the window buttons sit above it)
            PageHeader { id: header; Layout.fillWidth: true; Layout.bottomMargin: 8; title: p.title; hint: p.hint
                         // (in a narrow window the column reaches the window buttons: its actions keep clear of them)
                         Layout.rightMargin: Math.max(0, 112 - (sv.availableWidth - column.x - column.width)) }
            // (the content goes here)
        }
    }
    Column {  // the sections: it rides up with the page's first one, then stays at the top
        visible: p.indexed
        x: p.LayoutMirroring.enabled ? column.x + column.width + 24 : column.x - p.side
        y: p.sections.length ? Math.max(Theme.margin, p.sections[0].y - sv.contentItem.contentY) : Theme.margin
        spacing: 2
        Repeater {
            model: p.indexed ? p.sections : []
            AbstractButton {
                id: jumper
                required property var modelData
                required property int index
                readonly property bool current: p.currentSection === index
                width: 196; height: 32
                hoverEnabled: true
                Accessible.name: modelData.title
                onClicked: p.jump(index)
                background: Rectangle {
                    radius: 10
                    color: jumper.current ? Theme.accentSoft : jumper.hovered ? Theme.glassHover : "transparent"
                    Behavior on color { ColorAnimation { duration: Theme.fast } }
                    Focus { visible: jumper.visualFocus }
                }
                contentItem: Txt {
                    text: jumper.modelData.title
                    leftPadding: 12; rightPadding: 8
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight; wrapMode: Text.NoWrap
                    font.pixelSize: Theme.px(13)
                    weight: jumper.current ? 600 : 400
                    color: jumper.current || jumper.hovered ? Theme.text : Theme.text2
                }
            }
        }
    }
    Rectangle {  // content fades out above the window's bottom edge instead of being cut by it
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: 32
        visible: sv.contentItem.contentY < sv.contentHeight - sv.height - 1
        bottomRightRadius: Window.window && Window.window.visibility === Window.Maximized ? 0 : Theme.radiusWindow
        gradient: Gradient {
            GradientStop { position: 0; color: Theme.alpha(Theme.bgBottom, 0) }
            GradientStop { position: 1; color: Theme.bgBottom }
        }
    }
}
