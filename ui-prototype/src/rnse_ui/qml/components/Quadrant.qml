import QtQuick
import QtQuick.Shapes
import QtQuick.Effects

import "../"

Shape {
    id: half

    enum State {
        Disabled = 1,
        Inactive = 2,
        Active = 3
    }

    enum Corner {
        TopLeft = 0,
        TopRight = 1,
        BottomLeft = 2,
        BottomRight = 3
    }

    required property real radius
    required property real thickness
    required property real indicatorThickness
    required property int corner

    function quadrantState(corner) {
        if (!ui.corners[corner]) {
            return Quadrant.State.Disabled;
        }

        if (corner === ui.activeCorner) {
            return Quadrant.State.Active;
        }

        return Quadrant.State.Inactive;
    }

    readonly property int state: quadrantState(half.corner)

    readonly property real angle: Math.asin(height / radius)
    readonly property real angleDegrees: (angle * 180) / Math.PI

    preferredRendererType: Shape.CurveRenderer
    clip: true

    width: radius - (radius * Math.cos(angle)) + thickness

    readonly property bool flipX: corner == Quadrant.Corner.TopLeft || corner == Quadrant.Corner.BottomLeft
    readonly property bool flipY: corner == Quadrant.Corner.BottomRight || corner == Quadrant.Corner.BottomLeft

    readonly property real cx: Math.cos(angle) * radius * -1
    readonly property real cy: half.height

    readonly property color indicatorColor: state == Quadrant.State.Active ? Theme.accent : state == Quadrant.State.Inactive ? Theme.accentDim : Theme.disabled

    readonly property color buttonColor: state == Quadrant.State.Active ? Theme.accentDim : Qt.darker(Theme.disabled, 3)

    // Component.onCompleted: {
    //     console.log("quadrant cx=", half.cx, "cy=", half.cy);
    // }

    // The button
    ShapePath {
        fillColor: "#333"

        fillGradient: RadialGradient {
            centerX: half.cx
            centerY: half.cy
            centerRadius: half.radius + half.thickness
            focalRadius: half.radius - half.thickness * 8

            focalX: centerX
            focalY: centerY

            GradientStop {
                position: 0.75
                color: buttonColor
            }
            GradientStop {
                position: 1.0
                color: Qt.darker(buttonColor, 2)
            }
        }

        strokeColor: "transparent"

        startX: 0
        startY: 0

        PathAngleArc {
            centerX: half.cx
            centerY: half.cy

            radiusX: half.radius + half.indicatorThickness
            radiusY: half.radius + half.indicatorThickness

            startAngle: half.angleDegrees * -1
            sweepAngle: half.angleDegrees
        }

        PathLine {
            relativeX: half.thickness
            relativeY: 0
        }

        PathLine {
            relativeX: 0
            y: 0
        }

        PathLine {
            x: 0
            relativeY: 0
        }
    }

    Shape {

        preferredRendererType: Shape.CurveRenderer

        // The indicator
        ShapePath {
            id: indicator

            fillColor: "transparent"
            strokeColor: half.indicatorColor
            strokeWidth: half.indicatorThickness

            startX: 0
            startY: 0

            PathAngleArc {
                centerX: half.cx
                centerY: half.cy

                radiusX: half.radius + half.indicatorThickness / 2
                radiusY: half.radius + half.indicatorThickness / 2

                startAngle: half.angleDegrees * -1 - 5
                sweepAngle: half.angleDegrees + 5
            }
        }

        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: half.state == Quadrant.State.Active
            shadowColor: Theme.accent
            shadowBlur: 1.0

            shadowHorizontalOffset: 0
            shadowVerticalOffset: 0

            blurMax: 8
        }
    }

    transform: Scale {
        xScale: half.flipX ? -1 : 1
        origin.x: half.width / 2
        yScale: half.flipY ? -1 : 1
        origin.y: half.height / 2
    }
}
