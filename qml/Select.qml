import QtQuick
import QtQuick.Controls

// A drop-down. model: [{value, label}] (or plain strings); `value` is the chosen one.
ComboBox {
    id: c
    property string value: ""
    signal picked(string value)
    textRole: "label"
    valueRole: "value"
    implicitHeight: 40
    font.family: Theme.font
    font.pixelSize: 14
    currentIndex: Math.max(0, indexOfValue(value))
    onActivated: i => { value = valueAt(i); picked(value) }
    background: Rectangle {
        radius: Theme.radiusSmall
        color: c.hovered ? Theme.cardHover : Theme.bg
        border.width: 1
        border.color: c.popup.visible ? Theme.accent : Theme.lineStrong
    }
    contentItem: Text {
        leftPadding: 14
        text: c.displayText
        font: c.font
        color: Theme.text
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    indicator: Icon { name: "chevron"; size: 16; color: Theme.dim; x: c.width - width - 12; y: (c.height - height) / 2 }
    delegate: ItemDelegate {
        required property var model
        required property int index
        width: c.width - 8
        x: 4
        height: 34
        highlighted: c.highlightedIndex === index
        contentItem: Text { text: model[c.textRole]; font: c.font; color: Theme.text; verticalAlignment: Text.AlignVCenter; leftPadding: 6 }
        background: Rectangle { radius: 8; color: highlighted ? Theme.cardHover : "transparent" }
    }
    popup: Popup {
        y: c.height + 4
        width: c.width
        padding: 4
        implicitHeight: Math.min(contentItem.implicitHeight + 8, 320)
        contentItem: ListView { clip: true; implicitHeight: contentHeight; model: c.popup.visible ? c.delegateModel : null; currentIndex: c.highlightedIndex }
        background: Rectangle { radius: Theme.radiusSmall; color: Theme.raised; border.width: 1; border.color: Theme.lineStrong }
    }
}
