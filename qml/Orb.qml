import QtQuick
import QtQuick.Shapes

// Jarvis's face, an arc reactor: a glowing core in a solid ring, a segmented ring that turns (slowly when idle, faster
// while listening or speaking, fast and orange while working) and a thin outer ring in a soft halo.
// rings: false is the small version (core, inner ring and a faint halo), for the rail and chat avatars.
Item {
    id: orb
    property string mode: "idle"
    property real level: 0          // the user's voice, 0-1
    property bool rings: true
    property color tint: Theme.stateColor(mode)
    Behavior on tint { ColorAnimation { duration: 450; easing.type: Easing.OutCubic } }
    readonly property real r: Math.min(width, height) / 2
    implicitWidth: 220
    implicitHeight: 220

    // animate only while someone can see it (an item stays "visible" in a hidden window), and leave a small idle one still
    readonly property bool shown: visible && Window.window !== null && Window.window.visible
    property real t: 0      // seconds
    property real spin: 0   // the segmented ring's angle
    FrameAnimation {
        running: orb.shown && (orb.rings || orb.mode !== "idle")
        onTriggered: {
            orb.t += frameTime
            orb.spin = (orb.spin + frameTime * 360 / (orb.mode === "thinking" ? 3 : orb.mode === "idle" ? 14 : 5)) % 360
        }
    }
    property real smoothLevel: 0
    Behavior on smoothLevel { NumberAnimation { duration: 90 } }
    onLevelChanged: smoothLevel = level
    readonly property real pulse: mode === "listening" ? 0.02 + smoothLevel * 0.12
                                : mode === "speaking" ? 0.03 + 0.05 * Math.abs(Math.sin(t * 9) * Math.sin(t * 2.3))
                                : mode === "thinking" ? 0.015 + 0.015 * Math.sin(t * 4)
                                : 0.015 * (1 - Math.cos(t * 2 * Math.PI / 3))  // breathing: 1.0-1.03 over 3 s

    // circle outlines as SVG paths: `n` arcs of `fill` (0-1) of their share of the circle
    function arcs(cx, rad, n, fill) {
        let d = ""
        for (let i = 0; i < n; i++) {
            const a0 = i * 2 * Math.PI / n - Math.PI / 2, a1 = a0 + fill * 2 * Math.PI / n
            d += `M ${cx + rad * Math.cos(a0)} ${cx + rad * Math.sin(a0)} A ${rad} ${rad} 0 0 1 ${cx + rad * Math.cos(a1)} ${cx + rad * Math.sin(a1)} `
        }
        return d
    }

    component Disc: Shape {
        property real radius
        property alias gradient: path.fillGradient
        anchors.centerIn: parent
        width: radius * 2; height: width
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            id: path
            strokeWidth: -1
            PathAngleArc { centerX: radius; centerY: radius; radiusX: radius; radiusY: radius; sweepAngle: 360 }
        }
    }
    component Ring: Shape {
        property real radius
        property real line: 1
        property color stroke
        property string svg: ""   // instead of a whole circle
        anchors.centerIn: parent
        width: orb.r * 2; height: width
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            fillColor: "transparent"
            strokeColor: stroke
            strokeWidth: line
            capStyle: ShapePath.FlatCap
            PathSvg { path: svg !== "" ? svg : orb.arcs(orb.r, radius, 2, 1) }
        }
    }

    // the halo: the big one reaches past the item, to about 1.6x the outer ring; a small one stays inside it
    Disc {
        id: halo
        radius: orb.r * (orb.rings ? 1.35 : 1)
        scale: 1 + orb.pulse * 2.2
        gradient: RadialGradient {
            centerX: halo.radius; centerY: halo.radius; focalX: halo.radius; focalY: halo.radius; centerRadius: halo.radius
            GradientStop { position: 0.2; color: Theme.alpha(orb.tint, orb.rings ? 0.25 : 0.22) }
            GradientStop { position: orb.rings ? 0.62 : 0.5; color: Theme.alpha(orb.tint, orb.rings ? 0.12 : 0.06) }
            GradientStop { position: orb.rings ? 0.82 : 0.75; color: Theme.alpha(orb.tint, orb.rings ? 0.045 : 0.02) }
            GradientStop { position: 1.0; color: Theme.alpha(orb.tint, 0) }
        }
    }

    // the outer rings
    Ring { visible: orb.rings; radius: orb.r * 0.84; stroke: Theme.alpha(orb.tint, 0.3) }
    Ring { visible: orb.rings; radius: orb.r * 0.65; line: Math.max(2, orb.r * 0.05); stroke: Theme.alpha(orb.tint, 0.1) }
    Ring {
        visible: orb.rings
        rotation: orb.spin
        line: Math.max(2, orb.r * 0.05)
        stroke: Theme.alpha(orb.tint, 0.7)
        svg: orb.rings ? orb.arcs(orb.r, orb.r * 0.65, 12, 0.7) : ""
    }

    // the inner ring, a lit gap, and the core with its bloom
    Disc {
        radius: orb.r * (orb.rings ? 0.5 : 0.66)
        scale: 1 + orb.pulse * 0.5
        gradient: RadialGradient {
            centerX: orb.r * (orb.rings ? 0.5 : 0.66); centerY: centerX; focalX: centerX; focalY: centerX; centerRadius: centerX
            GradientStop { position: 0.6; color: Theme.alpha(orb.tint, 0.45) }
            GradientStop { position: 1.0; color: Theme.alpha(orb.tint, 0.08) }
        }
    }
    Ring { radius: orb.r * (orb.rings ? 0.5 : 0.66); line: orb.rings ? 2 : 1.5; stroke: Theme.alpha(orb.tint, 0.95); scale: 1 + orb.pulse * 0.5 }
    Disc {
        id: core
        radius: orb.r * (orb.rings ? 0.33 : 0.44)
        scale: 1 + orb.pulse
        gradient: RadialGradient {
            centerX: core.radius; centerY: core.radius; focalX: core.radius; focalY: core.radius; centerRadius: core.radius
            GradientStop { position: 0.0; color: "white" }
            GradientStop { position: 0.22; color: "white" }
            GradientStop { position: 0.5; color: Qt.lighter(orb.tint, 1.3) }
            GradientStop { position: 0.85; color: orb.tint }
            GradientStop { position: 1.0; color: Theme.alpha(orb.tint, 0.85) }
        }
    }
}
