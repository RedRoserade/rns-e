import QtQuick
import QtQuick.Shapes
import QtQuick.Layouts

import "components/"

// The chrome every RNS-E screen shares (manual p. 27-28):
//
//    TL label          Title            TR label
//   (  ╭──────────────────────────────────╮  )
//   (  │ subtitle                         │  )
//   (  │        screen content            │  )
//  ═(  │                                  │  )═   <- tabs split each arc in two
//   (  │                                  │  )
//   (  ╰──────────────────────────────────╯  )
//    BL label                           BR label
//
// Each arc half belongs to the corner next to it and lights up while that
// corner's submenu is open (p. 18; p. 57 fig. 54).
//
// Children of Frame go inside the panel (see `default property` below).
// All geometry is in real 800x480 pixels.
Item {
    id: frame
    width: 800
    height: 480

    property string title
    property string subtitle
    property var corners: ["", "", "", ""]  // labels TL, TR, BL, BR
    property int activeCorner: -1          // 0..3, or -1

    // --- geometry -----------------------------------------------------------
    // Panel: straight top and bottom edges, sides bowing outwards.
    readonly property int panelTop: Theme.barHeight
    readonly property int panelBottom: frame.height - Theme.barHeight

    readonly property int panelHeight: frame.height - (Theme.barHeight * 2)

    readonly property real arcRadius: (frame.width - (Theme.panelHorizontalPaddingPx * 2)) / 2
    readonly property real arcAngle: Math.asin(panelHeight / 2 / arcRadius)
    readonly property real arcAngleDegrees: (arcAngle * 180) / Math.PI

    // Where the top/bottom line intersect the arc
    readonly property real horizontalArcIntersectionLeft: Theme.panelHorizontalPaddingPx + arcRadius - (arcRadius * Math.cos(arcAngle))
    readonly property real horizontalArcIntersectionRight: frame.width - horizontalArcIntersectionLeft

    readonly property real arcInnerX: Theme.panelHorizontalPaddingPx

    readonly property real midX: frame.width / 2
    readonly property real midY: frame.height / 2

    readonly property real quadrantHeight: frame.panelHeight / 2

    // Children of a Frame land in the panel area.
    default property alias content: contentArea.data

    Rectangle {
        anchors.fill: parent
        color: Theme.background
    }

    // --- the panel --------------------------------------------------------
    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer

        ShapePath {
            strokeColor: Theme.accent
            strokeWidth: 1.5
            fillColor: Theme.background

            startX: frame.horizontalArcIntersectionLeft
            startY: frame.panelTop

            // Top
            PathLine {
                x: frame.horizontalArcIntersectionRight
                relativeY: 0
            }

            // Right
            PathAngleArc {
                centerX: frame.midX
                centerY: frame.midY

                radiusX: frame.arcRadius
                radiusY: frame.arcRadius

                startAngle: (frame.arcAngleDegrees * -1)
                sweepAngle: frame.arcAngleDegrees * 2
            }

            // Bottom
            PathLine {
                x: frame.horizontalArcIntersectionLeft
                y: frame.panelBottom
            }

            // Left
            PathAngleArc {
                centerX: frame.midX
                centerY: frame.midY

                radiusX: frame.arcRadius
                radiusY: frame.arcRadius

                startAngle: (frame.arcAngleDegrees * -1) + 180
                sweepAngle: frame.arcAngleDegrees * 2
            }
        }
    }

    Quadrant {
        id: topRight

        anchors.top: topBar.bottom
        anchors.right: frame.right

        corner: Quadrant.Corner.TopRight
        radius: frame.arcRadius + 5
        thickness: Theme.panelHorizontalPaddingPx - 5
        indicatorThickness: 5

        height: frame.quadrantHeight
    }

    Quadrant {
        id: bottomRight

        anchors.bottom: bottomBar.top
        anchors.right: frame.right

        radius: frame.arcRadius + 5
        thickness: Theme.panelHorizontalPaddingPx - 5
        indicatorThickness: 5
        corner: Quadrant.Corner.BottomRight

        height: frame.quadrantHeight
    }

    Quadrant {
        id: bottomLeft

        anchors.bottom: bottomBar.top
        anchors.left: frame.left

        radius: frame.arcRadius + 5
        thickness: Theme.panelHorizontalPaddingPx - 5
        indicatorThickness: 5
        corner: Quadrant.Corner.BottomLeft

        height: frame.quadrantHeight
    }

    Quadrant {
        id: topLeft

        anchors.top: topBar.bottom
        anchors.left: frame.left

        corner: Quadrant.Corner.TopLeft
        radius: frame.arcRadius + 5
        thickness: Theme.panelHorizontalPaddingPx - 5
        indicatorThickness: 5

        height: frame.quadrantHeight
    }

    // Tabs at mid-height that split each arc into its two halves.
    // Repeater {
    //     model: 2
    //     Item {
    //         anchors.left: index == 0 ? frame.left : undefined
    //         anchors.right: index == 1 ? frame.right : undefined
    //         y: frame.midY - height / 2
    //         width: frame.arcInnerX - 5
    //         height: 4
    //         Rectangle {
    //             anchors.fill: parent
    //             color: Theme.background
    //         }
    //         Rectangle {
    //             anchors.verticalCenter: parent.verticalCenter
    //             width: parent.width
    //             height: 2
    //             color: Theme.tabIdle
    //         }
    //     }
    // }

    // Top bar
    Rectangle {
        id: topBar

        anchors.top: frame.top
        anchors.left: frame.left
        anchors.right: frame.right
        height: Theme.panelVerticalPaddingPx
        color: Theme.background

        RowLayout {
            anchors.fill: topBar
            anchors.leftMargin: Theme.panelHorizontalPaddingPx / 2
            anchors.rightMargin: Theme.panelHorizontalPaddingPx / 2

            // Top corner labels
            Text {
                Layout.minimumWidth: 100
                horizontalAlignment: Text.AlignLeft

                text: frame.corners[0] || ""

                color: frame.activeCorner === 0 ? Theme.accent : Theme.accentDim

                font.family: frame.activeCorner === 0 ? Theme.fontFamilyBold : Theme.fontFamily
                font.pixelSize: Theme.fontSizeCorner
                font.bold: Theme.fontBoldSynthetic

                Behavior on color {
                    ColorAnimation {
                        duration: Theme.animMs
                    }
                }
            }

            // Title
            Text {
                text: frame.title

                Layout.fillWidth: true
                Layout.minimumWidth: 200
                horizontalAlignment: Text.AlignHCenter

                color: Theme.accent
                font.family: Theme.fontFamilyBold
                font.pixelSize: Theme.fontSizeTitle
                font.bold: Theme.fontBoldSynthetic
            }

            Text {
                Layout.minimumWidth: 100
                horizontalAlignment: Text.AlignRight

                text: frame.corners[1] || ""

                color: frame.activeCorner === 1 ? Theme.accent : Theme.accentDim

                font.family: frame.activeCorner === 1 ? Theme.fontFamilyBold : Theme.fontFamily
                font.pixelSize: Theme.fontSizeCorner
                font.bold: Theme.fontBoldSynthetic

                Behavior on color {
                    ColorAnimation {
                        duration: Theme.animMs
                    }
                }
            }
        }
    }

    // Bottom bar
    Rectangle {
        id: bottomBar

        anchors.bottom: frame.bottom
        anchors.left: frame.left
        anchors.right: frame.right

        height: Theme.barHeight
        color: Theme.background

        RowLayout {
            anchors.fill: bottomBar
            anchors.leftMargin: Theme.panelHorizontalPaddingPx / 2
            anchors.rightMargin: Theme.panelHorizontalPaddingPx / 2

            // Bottom corner labels
            Text {
                Layout.minimumWidth: 100
                horizontalAlignment: Text.AlignLeft
                Layout.fillWidth: true

                text: frame.corners[2] || ""

                color: frame.activeCorner === 2 ? Theme.accent : Theme.accentDim

                font.family: frame.activeCorner === 2 ? Theme.fontFamilyBold : Theme.fontFamily
                font.pixelSize: Theme.fontSizeCorner
                font.bold: Theme.fontBoldSynthetic

                Behavior on color {
                    ColorAnimation {
                        duration: Theme.animMs
                    }
                }
            }

            Text {
                Layout.minimumWidth: 100
                horizontalAlignment: Text.AlignRight
                Layout.fillWidth: true

                text: frame.corners[3] || ""

                color: frame.activeCorner === 3 ? Theme.accent : Theme.accentDim

                font.family: frame.activeCorner === 3 ? Theme.fontFamilyBold : Theme.fontFamily
                font.pixelSize: Theme.fontSizeCorner
                font.bold: Theme.fontBoldSynthetic

                Behavior on color {
                    ColorAnimation {
                        duration: Theme.animMs
                    }
                }
            }
        }
    }

    Item {
        id: contentArea

        x: frame.horizontalArcIntersectionLeft
        y: frame.panelTop + 1

        width: frame.width - 2 * x
        height: frame.panelBottom - frame.panelTop - 2
    }
}
