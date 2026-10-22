pragma Singleton
import QtQuick

// Jarvis's look ("Glass"): frosted surfaces over a deep navy canvas, cyan as the signature, orange while working.
QtObject {
    // canvas
    readonly property color bg: "#05080d"
    readonly property color bgTop: "#08121c"
    readonly property color bgBottom: "#04070b"

    // glass
    readonly property color glass: "#0bffffff"        // cards, rows, chips
    readonly property color glassHover: "#12ffffff"
    readonly property color glassStrong: "#bf0e1822"  // floating: rail, composer, toasts
    readonly property color popover: "#f20e1822"      // menus over content (no blur behind, so nearly opaque)
    readonly property color stroke: "#14ffffff"       // 1px hairline around glass
    readonly property color strokeStrong: "#24ffffff" // focused fields, popovers, the window edge
    readonly property color highlight: "#0fffffff"    // light catching the top edge of glass
    readonly property color track: "#1affffff"        // empty bars, toggles off
    readonly property color shadow: "#59000000"

    // text
    readonly property color text: "#eaf6ff"
    readonly property color text2: "#93a9b9"
    readonly property color text3: "#5e7586"

    // colour
    readonly property color accent: "#3fd8ff"       // Jarvis's cyan
    readonly property color accentSoft: "#243fd8ff"
    readonly property color accentInk: "#04202b"    // text and icons on solid cyan
    readonly property color listen: "#7cf0ff"
    readonly property color speak: "#7cf0ff"
    readonly property color warm: "#ff9d3f"         // Jarvis's orange: working
    readonly property color warmSoft: "#24ff9d3f"
    readonly property color green: "#4ade80"
    readonly property color red: "#f87171"

    // older names, kept for pages not yet moved over
    readonly property color panel: glassStrong
    readonly property color card: glass
    readonly property color cardHover: glassHover
    readonly property color raised: track
    readonly property color line: stroke
    readonly property color lineStrong: strokeStrong
    readonly property color dim: text2
    readonly property color faint: text3
    readonly property color ink: accentInk
    readonly property color accentDeep: "#1b9cc4"

    readonly property string font: "Inter Variable"
    readonly property string mono: "JetBrainsMono Nerd Font"
    property real scale: 1.0  // Settings → Text size
    function px(n) { return Math.round(n * scale) }  // (font sizes stay whole pixels)

    readonly property int radiusWindow: 22
    readonly property int radius: 20         // cards
    readonly property int radiusControl: 12  // fields, selects, text areas
    readonly property int radiusSmall: 8

    readonly property int margin: 40         // around a page's content
    readonly property int pageWidth: 920     // a page's content column at most
    readonly property int pad: 20            // inside a card
    readonly property int gap: 16            // between cards
    readonly property int fast: 140          // hover and press, ms

    function stateColor(s) {
        return s === "listening" ? listen : s === "thinking" ? warm : s === "speaking" ? speak : accent
    }
    function stateName(s) {
        return s === "listening" ? "Listening" : s === "thinking" ? "Working" : s === "speaking" ? "Speaking" : "Ready"
    }
    function alpha(c, a) { return Qt.rgba(c.r, c.g, c.b, c.a * a) }  // (scales: alpha(glass, 0.5) is half as strong)
}
