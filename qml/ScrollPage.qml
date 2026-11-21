import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// A scrolling page: its header, then the content in a column (at most `maxWidth` wide, centred). With no title it's
// only the scrolling part, for a page that keeps its own header in place above it (Settings, with its tabs).
Item {
    id: p
    property string title
    property string hint
    default property alias content: column.data
    property alias actions: header.actions
    property int maxWidth: Theme.pageWidth
    property int headroom: Theme.margin  // above the header, or above the content when there's none
    readonly property bool scrolled: sv.contentItem.contentY > 0
    function toTop() { sv.contentItem.contentY = 0 }
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

    ScrollView {
        id: sv
        anchors.fill: parent
        contentWidth: availableWidth
        contentHeight: column.implicitHeight + Theme.margin
        clip: true
        ScrollBar.vertical: Scroller { parent: sv; x: sv.width - width; height: sv.availableHeight }
        ColumnLayout {
            id: column
            width: Math.min(sv.availableWidth - 2 * Theme.margin, p.maxWidth)
            x: (sv.availableWidth - width) / 2
            spacing: Theme.gap
            Item { Layout.preferredHeight: p.headroom - Theme.gap }  // (the top margin; the window buttons sit above it)
            PageHeader { id: header; Layout.fillWidth: true; Layout.bottomMargin: 8; title: p.title; hint: p.hint; visible: p.title !== ""
                         // (in a narrow window the column reaches the window buttons: its actions keep clear of them)
                         Layout.rightMargin: Math.max(0, 112 - (sv.availableWidth - column.x - column.width)) }
            // (the content goes here)
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
