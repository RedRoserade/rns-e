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
    readonly property int panelTop: Theme.panelVerticalPaddingPx
    readonly property int panelBottom: height - Theme.panelVerticalPaddingPx
    
    readonly property int panelHeight: height - (Theme.panelVerticalPaddingPx * 2)
    
    readonly property real panelInset: 50   // x of the panel's corners
    readonly property real panelBulge: 50    // how far the sides bow at mid-height

    
    readonly property real arcRadius: (width - (Theme.panelHorizontalPaddingPx * 2)) / 2
    readonly property real arcAngle: Math.asin(panelHeight / 2 / arcRadius)
    readonly property real arcAngleDegrees: (arcAngle * 180) / Math.PI

    // Where the top/bottom line intersect the arc
    readonly property real horizontalArcIntersectionLeft: Theme.panelHorizontalPaddingPx + arcRadius - (arcRadius * Math.cos(arcAngle))
    readonly property real horizontalArcIntersectionRight: width - horizontalArcIntersectionLeft

    readonly property real arcTop: panelTop
    readonly property real arcBottom: panelBottom
    readonly property real arcEndX: 72       // x of the arc's tips
    readonly property real arcOuterX: 8      // outer edge at mid-height
    readonly property real arcInnerX: Theme.panelHorizontalPaddingPx

    readonly property real midY: height / 2

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
            fillGradient: LinearGradient {
                x1: 0; y1: frame.panelTop
                x2: 0; y2: frame.panelBottom
                GradientStop { position: 0.0; color: Qt.darker(Theme.accent, 9) }
                GradientStop { position: 0.35; color: Theme.background }
                GradientStop { position: 1.0; color: Theme.background }
            }

            // Quadratic sides: the point at t=0.5 sits halfway between the
            // tips and the control point, so control = 2*mid - tip.
            startX: frame.horizontalArcIntersectionLeft; startY: frame.panelTop

            // Top            
            PathLine { x: frame.horizontalArcIntersectionRight; y: frame.panelTop }

            // Right
            PathAngleArc {
                centerX: frame.width / 2
                centerY: frame.height / 2

                radiusX: frame.arcRadius
                radiusY: frame.arcRadius

                startAngle: (frame.arcAngleDegrees * -1)
                sweepAngle: frame.arcAngleDegrees * 2
            }
            
            // Bottom
            PathLine { x: frame.horizontalArcIntersectionLeft; y: frame.panelBottom }
            
            // Left
            PathAngleArc {
                centerX: frame.width / 2
                centerY: frame.height / 2

                radiusX: frame.arcRadius
                radiusY: frame.arcRadius

                startAngle: (frame.arcAngleDegrees * -1) + 180
                sweepAngle: frame.arcAngleDegrees * 2
            }
        }
    }

    Quadrant { 
        id: topRight

        state: Quadrant.State.Inactive
        corner: Quadrant.Corner.TopRight
        radius: frame.arcRadius + 5
        thickness: Theme.panelHorizontalPaddingPx - 5
        indicatorThickness: 5

        height: panelHeight / 2

        anchors.right: frame.right

        y: frame.panelTop
    }


    Quadrant { 
        id: bottomRight

        state: Quadrant.State.Disabled
        radius: frame.arcRadius + 5
        thickness: Theme.panelHorizontalPaddingPx - 5
        indicatorThickness: 5
        corner: Quadrant.Corner.BottomRight

        height: panelHeight / 2

        anchors.right: frame.right

        y: frame.height / 2
    }

    Quadrant { 
        id: bottomLeft

        state: Quadrant.State.Inactive
        radius: frame.arcRadius + 5
        thickness: Theme.panelHorizontalPaddingPx - 5
        indicatorThickness: 5
        corner: Quadrant.Corner.BottomLeft

        height: panelHeight / 2

        anchors.left: frame.left

        y: frame.height / 2
    }


    Quadrant { 
        id: topLeft

        state: Quadrant.State.Active
        radius: frame.arcRadius + 5
        thickness: Theme.panelHorizontalPaddingPx - 5
        indicatorThickness: 5
        corner: Quadrant.Corner.TopLeft

        height: panelHeight / 2

        anchors.left: frame.left

        y: frame.panelTop
    }

    // Tabs at mid-height that split each arc into its two halves.
    Repeater {
        model: 2
        Item {
            anchors.left: index == 0 ? frame.left : undefined
            anchors.right: index == 1 ? frame.right : undefined
            y: frame.midY - height / 2
            width: frame.arcInnerX - 5
            height: 4
            Rectangle { anchors.fill: parent; color: Theme.background }
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width; height: 2
                color: Theme.tabIdle
            }
        }
    }

    // Top bar
    Rectangle {
        id: topBar
        
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
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

                color: frame.activeCorner === 0 ? Theme.text : Theme.textDim
                
                font.family: frame.activeCorner === 0 ? Theme.fontFamilyBold : Theme.fontFamily
                font.pixelSize: Theme.cornerSize
                font.bold: Theme.fontBoldSynthetic
                
                Behavior on color { ColorAnimation { duration: Theme.animMs } }
            }
        
            // Title
            Text {
                text: frame.title
                
                Layout.fillWidth: true
                Layout.minimumWidth: 200
                horizontalAlignment: Text.AlignHCenter

                color: Theme.accent
                font.family: Theme.fontFamilyBold
                font.pixelSize: Theme.titleSize
                font.bold: Theme.fontBoldSynthetic
            }

            Text {
                Layout.minimumWidth: 100
                horizontalAlignment: Text.AlignRight

                text: frame.corners[1] || ""

                color: frame.activeCorner === 1 ? Theme.text : Theme.textDim
                
                font.family: frame.activeCorner === 1 ? Theme.fontFamilyBold : Theme.fontFamily
                font.pixelSize: Theme.cornerSize
                font.bold: Theme.fontBoldSynthetic
                
                Behavior on color { ColorAnimation { duration: Theme.animMs } }
            }
        }
    }

    // Bottom bar
    Rectangle {
        id: bottomBar
        
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: Theme.panelVerticalPaddingPx
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

                color: frame.activeCorner === 2 ? Theme.text : Theme.textDim
                
                font.family: frame.activeCorner === 2 ? Theme.fontFamilyBold : Theme.fontFamily
                font.pixelSize: Theme.cornerSize
                font.bold: Theme.fontBoldSynthetic
                
                Behavior on color { ColorAnimation { duration: Theme.animMs } }
            }
        
            Text {
                Layout.minimumWidth: 100
                horizontalAlignment: Text.AlignRight
                Layout.fillWidth: true

                text: frame.corners[3] || ""

                color: frame.activeCorner === 3 ? Theme.text : Theme.textDim
                
                font.family: frame.activeCorner === 3 ? Theme.fontFamilyBold : Theme.fontFamily
                font.pixelSize: Theme.cornerSize
                font.bold: Theme.fontBoldSynthetic
                
                Behavior on color { ColorAnimation { duration: Theme.animMs } }
            }
        }
    }

    Item {
        id: contentArea

        x: frame.panelInset - frame.panelBulge
        y: frame.panelTop
        width: frame.width - 2 * x
        height: frame.panelBottom - frame.panelTop
    }

    
}
