import QtQuick

// A delete that can't be undone takes two clicks, as on Chats, Accounts and Plugins: the first arms it (a red check that
// says "Click again…"), a second within 4 s does it (confirmed), and left alone it disarms.
IconButton {
    id: b
    property string label: qsTr("Delete")  // what it does: its tip until it's armed
    property string again: qsTr("Click again to delete")
    property string idleSymbol: "trash"
    property bool armed: false
    signal confirmed()
    size: 32
    glyph: 16
    symbol: armed ? "check" : idleSymbol
    color: Theme.text3
    tint: armed ? Theme.alpha(Theme.red, 0.14) : "transparent"
    iconColor: armed || hovered ? Theme.red : color
    tip: armed ? again : label
    onClicked: {
        if (!armed) { armed = true; undo.restart(); return }
        armed = false
        undo.stop()
        confirmed()
    }
    Timer { id: undo; interval: 4000; onTriggered: b.armed = false }
}
