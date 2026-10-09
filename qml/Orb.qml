import QtQuick
import QtQuick.Shapes

// Jarvis's face: a glowing orb that breathes when idle, follows your voice when listening, pulses when speaking and
// spins its rings while working.
Item {
    id: orb
    property string mode: "idle"
    property real level: 0          // the user's voice, 0-1
    property bool rings: true
    property color tint: Theme.stateColor(mode)
    Behavior on tint { ColorAnimation { duration: 450; easing.type: Easing.OutCubic } }
    readonly property real r: Math.min(width, height) / 2
    implicitWidth: 200
    implicitHeight: 200

    // animate only while someone can see it (an item stays "visible" in a hidden window)
    readonly property bool shown: visible && Window.window !== null && Window.window.visible
    property real t: 0  // seconds, for the breathing and pulsing
    NumberAnimation on t { from: 0; to: 1000; duration: 1000000; loops: Animation.Infinite; running: orb.shown }
    property real smoothLevel: 0
    Behavior on smoothLevel { NumberAnimation { duration: 90 } }
    onLevelChanged: smoothLevel = level
    readonly property real pulse: mode === "listening" ? 0.04 + smoothLevel * 0.22
                                : mode === "speaking" ? 0.05 + 0.05 * Math.sin(t * 9) * Math.sin(t * 2.3)
                                : mode === "thinking" ? 0.03 * Math.sin(t * 4)
                                : 0.025 * Math.sin(t * 1.6)

    // the halo
    Shape {
        anchors.centerIn: parent
        width: orb.r * 2; height: width
        scale: 1 + orb.pulse * 1.6
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: 0
            fillGradient: RadialGradient {
                centerX: orb.r; centerY: orb.r; focalX: orb.r; focalY: orb.r; centerRadius: orb.r; focalRadius: 0
                GradientStop { position: 0.30; color: Theme.alpha(orb.tint, 0.38) }
                GradientStop { position: 0.62; color: Theme.alpha(orb.tint, 0.10) }
                GradientStop { position: 1.0; color: Theme.alpha(orb.tint, 0.0) }
            }
            PathAngleArc { centerX: orb.r; centerY: orb.r; radiusX: orb.r; radiusY: orb.r; startAngle: 0; sweepAngle: 360 }
        }
    }

    // two thin rings: slow when idle, fast while working
    Repeater {
        model: orb.rings ? 2 : 0
        Shape {
            required property int index
            anchors.centerIn: parent
            width: orb.r * (index === 0 ? 1.18 : 1.02); height: width
            preferredRendererType: Shape.CurveRenderer
            opacity: orb.mode === "thinking" ? 0.95 : 0.45
            Behavior on opacity { NumberAnimation { duration: 300 } }
            RotationAnimation on rotation {
                from: index === 0 ? 0 : 360; to: index === 0 ? 360 : 0; loops: Animation.Infinite; running: orb.shown
                duration: orb.mode === "thinking" ? (index === 0 ? 1400 : 2100) : (index === 0 ? 14000 : 21000)
            }
            ShapePath {
                fillColor: "transparent"
                strokeColor: Theme.alpha(orb.tint, 0.9)
                strokeWidth: Math.max(1.5, orb.r * 0.022)
                capStyle: ShapePath.RoundCap
                PathAngleArc {
                    centerX: width / 2; centerY: height / 2; radiusX: width / 2 - 2; radiusY: height / 2 - 2
                    startAngle: index * 140; sweepAngle: index === 0 ? 92 : 58
                }
            }
            ShapePath {
                fillColor: "transparent"
                strokeColor: Theme.alpha(orb.tint, 0.35)
                strokeWidth: Math.max(1, orb.r * 0.012)
                capStyle: ShapePath.RoundCap
                PathAngleArc {
                    centerX: width / 2; centerY: height / 2; radiusX: width / 2 - 2; radiusY: height / 2 - 2
                    startAngle: index * 140 + 180; sweepAngle: 40
                }
            }
        }
    }

    // the core
    Shape {
        anchors.centerIn: parent
        width: orb.r * 0.86; height: width
        scale: 1 + orb.pulse
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: 0
            fillGradient: RadialGradient {
                readonly property real c: orb.r * 0.43
                centerX: c; centerY: c; centerRadius: c; focalX: c * 0.72; focalY: c * 0.62; focalRadius: 0
                GradientStop { position: 0.0; color: Qt.lighter(orb.tint, 1.65) }
                GradientStop { position: 0.45; color: orb.tint }
                GradientStop { position: 1.0; color: Qt.darker(orb.tint, orb.mode === "idle" ? 2.4 : 1.9) }
            }
            PathAngleArc { centerX: orb.r * 0.43; centerY: orb.r * 0.43; radiusX: orb.r * 0.43; radiusY: orb.r * 0.43; startAngle: 0; sweepAngle: 360 }
        }
    }
}
