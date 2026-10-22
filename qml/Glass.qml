import QtQuick
import QtQuick.Effects

// A frosted surface: a faint fill, a hairline, and light catching its top edge. `floating` for things that hover over
// the page (rail, composer, toasts, menus): a stronger fill and a soft shadow.
Rectangle {
    id: g
    property bool floating: false
    color: floating ? Theme.glassStrong : Theme.glass
    radius: Theme.radius
    border.width: 1
    border.color: Theme.stroke

    RectangularShadow {
        visible: g.floating
        z: -1
        anchors.fill: parent
        radius: g.radius
        blur: 30
        offset.y: 10
        color: Theme.shadow
    }
    Rectangle {  // the top edge
        x: g.radius; y: 0
        width: Math.max(0, g.width - 2 * g.radius); height: 1
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "transparent" }
            GradientStop { position: 0.5; color: Theme.highlight }
            GradientStop { position: 1; color: "transparent" }
        }
    }
}
