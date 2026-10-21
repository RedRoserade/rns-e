import QtQuick
import QtQuick.Shapes

import "../"

Shape {

    enum State { Disabled = 1, Inactive = 2, Active = 3 }

    enum Corner { TopLeft = 1, TopRight = 2, BottomLeft = 3, BottomRight = 4 }

    id: half

    required property real radius
    required property real thickness
    required property real indicatorThickness
    required property int corner

    required property int state

    readonly property real angle: Math.asin(height / radius)
    readonly property real angleDegrees: (angle * 180) / Math.PI

    preferredRendererType: Shape.CurveRenderer
    clip: true

    width: radius - (radius * Math.cos(angle)) + thickness

    readonly property bool flipX: corner == Quadrant.Corner.TopLeft || corner == Quadrant.Corner.BottomLeft
    readonly property bool flipY: corner == Quadrant.Corner.BottomRight || corner == Quadrant.Corner.BottomLeft

    readonly property real cx: Math.cos(angle) * radius * -1
    readonly property real cy: half.height

    readonly property color indicatorColor: state == Quadrant.State.Active
        ? Theme.accent
        : state == Quadrant.State.Inactive
            ? Theme.accentDim
                : Theme.disabled

    // The button
    ShapePath {
        fillColor: "#333"
        strokeColor: "transparent"

        startX: 0
        startY: 0

        PathAngleArc {
            centerX: half.cx
            centerY: half.cy

            radiusX: half.radius
            radiusY: half.radius

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

    // The indicator
    ShapePath {
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

    transform: Scale { 
        xScale: half.flipX ? -1 : 1; origin.x: half.width / 2
        yScale: half.flipY ? -1 : 1; origin.y: half.height / 2
    }
}