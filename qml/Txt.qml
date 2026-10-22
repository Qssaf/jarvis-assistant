import QtQuick

// Text in Jarvis's type scale: kind "display", "title", "heading", "body", "small", "label" ("caps" is the old name of label).
Text {
    property string kind: "body"
    readonly property bool isLabel: kind === "label" || kind === "caps"
    font.family: Theme.font
    font.pixelSize: Theme.px(kind === "display" ? 36 : kind === "title" ? 28 : kind === "heading" ? 17 : kind === "small" ? 13 : isLabel ? 12 : 14)
    // (Inter is one variable font: Qt only shows weights under 700 through its axis, so set `weight`, not font.weight)
    property int weight: kind === "display" || kind === "title" || kind === "heading" || isLabel ? 600 : 400
    font.weight: weight
    font.variableAxes: ({ "wght": weight })
    font.letterSpacing: kind === "display" ? -0.8 : kind === "title" ? -0.5 : isLabel ? 0.3 : 0
    color: kind === "small" || isLabel ? Theme.text2 : Theme.text
    wrapMode: Text.Wrap
    linkColor: Theme.accent
    onLinkActivated: link => { if (/^(https?|mailto):/i.test(link)) Qt.openUrlExternally(link) }  // (text can come from anywhere)
}
