import QtQuick

// Text in Jarvis's type scale: kind "title", "heading", "body", "small", "caps".
Text {
    property string kind: "body"
    font.family: Theme.font
    font.pixelSize: kind === "title" ? 26 : kind === "heading" ? 16 : kind === "small" ? 13 : kind === "caps" ? 11 : 14
    font.weight: kind === "title" ? Font.Bold : kind === "heading" ? Font.DemiBold : kind === "caps" ? Font.Bold : Font.Normal
    font.letterSpacing: kind === "caps" ? 1.4 : kind === "title" ? -0.4 : 0
    font.capitalization: kind === "caps" ? Font.AllUppercase : Font.MixedCase
    color: kind === "small" || kind === "caps" ? Theme.dim : Theme.text
    wrapMode: Text.Wrap
    linkColor: Theme.accent
    onLinkActivated: link => { if (/^(https?|mailto):/i.test(link)) Qt.openUrlExternally(link) }  // (text can come from anywhere)
}
