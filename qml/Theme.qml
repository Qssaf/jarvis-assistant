pragma Singleton
import QtQuick

// Jarvis's look: deep navy surfaces, cyan as the signature, orange while working.
QtObject {
    readonly property color bg: "#04080d"
    readonly property color panel: "#050b11"
    readonly property color card: "#0a1621"
    readonly property color cardHover: "#0e1e2b"
    readonly property color raised: "#12293a"
    readonly property color line: "#2216364a"
    readonly property color lineStrong: "#9916364a"
    readonly property color text: "#d6f3ff"
    readonly property color dim: "#6d8a9b"
    readonly property color faint: "#4a6373"
    readonly property color ink: "#04080d"          // dark text on a bright fill

    readonly property color accent: "#3fd8ff"       // Jarvis's cyan
    readonly property color accentDeep: "#1b9cc4"
    readonly property color listen: "#7cf0ff"
    readonly property color speak: "#7cf0ff"
    readonly property color warm: "#ff9d3f"         // Jarvis's orange
    readonly property color red: "#f87171"
    readonly property color green: "#4ade80"

    readonly property string font: "Inter Variable"
    readonly property string mono: "JetBrainsMono Nerd Font"
    readonly property int radius: 14
    readonly property int radiusSmall: 10

    function stateColor(s) {
        return s === "listening" ? listen : s === "thinking" ? warm : s === "speaking" ? speak : accent
    }
    function stateName(s) {
        return s === "listening" ? "Listening" : s === "thinking" ? "Working" : s === "speaking" ? "Speaking" : "Ready"
    }
    function alpha(c, a) { return Qt.rgba(c.r, c.g, c.b, a) }
}
