import QtQuick
import ".."

// Stands in for any screen without its own qml/screens/<id>.qml.
// Also a minimal example of a screen listening to the knob.
Item {
    id: root
    property int knob: 0

    Connections {
        target: ui
        function onKnobRotated(delta) { root.knob += delta }
        function onKnobPressed() { root.knob = 0 }
    }

    Column {
        anchors.centerIn: parent
        spacing: 8

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: ui.screenId
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSizeBody
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "no qml/screens/" + ui.screenId + ".qml yet"
            color: Theme.textDim
            font.family: Theme.fontFamily
            font.pixelSize: 16
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "knob: " + root.knob
            color: Theme.textDim
            font.family: Theme.fontFamily
            font.pixelSize: 16
        }
    }
}
