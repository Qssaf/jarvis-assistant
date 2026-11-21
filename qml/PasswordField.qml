import QtQuick

// A password box that can show what's in it. Typed blind and only once, a slip (another keyboard layout, Caps Lock, a
// missed key) can't be seen, and the password is then "wrong" the first time it's needed.
Field {
    id: f
    property bool shown: false
    echoMode: shown ? TextInput.Normal : TextInput.Password
    leftPadding: LayoutMirroring.enabled ? 46 : 14  // (paddings don't mirror by themselves; the button's anchors do)
    rightPadding: LayoutMirroring.enabled ? 14 : 46
    onTextChanged: if (text === "") shown = false  // (emptied: the next one starts hidden)
    IconButton {
        anchors { right: parent.right; rightMargin: 6; verticalCenter: parent.verticalCenter }
        symbol: f.shown ? "eye-off" : "eye"
        size: 32; glyph: 16; color: Theme.text3
        tip: f.shown ? qsTr("Hide it") : qsTr("Show what you typed")
        onClicked: f.shown = !f.shown
    }
}
