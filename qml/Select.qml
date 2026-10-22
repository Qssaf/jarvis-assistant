import QtQuick
import QtQuick.Controls

// A drop-down. model: [{value, label}] (or plain strings); `value` is the chosen one.
ComboBox {
    id: c
    property string value: ""
    signal picked(string value)
    textRole: "label"
    valueRole: "value"
    implicitHeight: 44
    hoverEnabled: true
    font.family: Theme.font
    font.pixelSize: Theme.px(14)
    // (not a binding: it wouldn't re-run when the list arrives after the value, and picking an item would break it)
    function sync() { currentIndex = Math.max(0, indexOfValue(value)) }
    onValueChanged: sync()
    onModelChanged: Qt.callLater(sync)  // (once the new list is in place)
    onCountChanged: Qt.callLater(sync)
    Component.onCompleted: sync()
    onActivated: i => { value = valueAt(i); picked(value) }
    background: Rectangle {
        radius: Theme.radiusControl
        color: c.hovered || c.popup.visible ? Theme.glassHover : Theme.glass
        border.width: 1
        border.color: c.popup.visible ? Theme.accent : Theme.stroke
        Behavior on color { ColorAnimation { duration: Theme.fast } }
        Focus { visible: c.popup.visible }
    }
    contentItem: Text {
        leftPadding: 14
        rightPadding: 36
        text: c.displayText
        font: c.font
        color: Theme.text
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    indicator: Icon { name: "chevron"; size: 16; color: c.popup.visible ? Theme.accent : Theme.text2; x: c.width - width - 14; y: (c.height - height) / 2
                      rotation: c.popup.visible ? 180 : 0; Behavior on rotation { NumberAnimation { duration: Theme.fast } } }
    delegate: ItemDelegate {
        id: d
        required property var model
        required property int index
        readonly property bool chosen: c.currentIndex === index
        width: c.popup.availableWidth
        height: 36
        highlighted: c.highlightedIndex === index
        contentItem: Item {
            Text { anchors { left: parent.left; leftMargin: 10; right: tick.left; rightMargin: 8; verticalCenter: parent.verticalCenter }
                   text: d.model[c.textRole]; font: c.font; elide: Text.ElideRight; color: d.chosen ? Theme.accent : Theme.text }
            Icon { id: tick; name: "check"; size: 16; color: Theme.accent; visible: d.chosen
                   anchors { right: parent.right; rightMargin: 8; verticalCenter: parent.verticalCenter } }
        }
        background: Rectangle { radius: Theme.radiusSmall; color: d.highlighted ? Theme.glassHover : "transparent" }
    }
    popup: Popup {
        y: c.height + 6
        width: c.width
        padding: 5
        implicitHeight: Math.min(contentItem.implicitHeight + 10, 320)
        contentItem: ListView { clip: true; implicitHeight: contentHeight; model: c.popup.visible ? c.delegateModel : null
                                currentIndex: c.highlightedIndex; ScrollBar.vertical: Scroller {} }
        background: Glass { floating: true; color: Theme.popover; radius: Theme.radiusControl; border.color: Theme.strokeStrong }
        enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.fast } }
    }
}
