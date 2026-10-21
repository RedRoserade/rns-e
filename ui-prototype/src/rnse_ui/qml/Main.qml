import QtQuick
import QtQuick.Window

Window {
    width: 800
    height: 480
    visible: true
    visibility: fullscreen ? Window.FullScreen : Window.Windowed
    title: "RNS-E"
    color: "blue"

    Frame {
        // On a bigger fullscreen display, keep 800x480 and centre it.
        anchors.centerIn: parent

        title: ui.title
        subtitle: ui.subtitle
        corners: ui.corners
        activeCorner: ui.activeCorner

        Loader {
            anchors.fill: parent
            source: ui.screenSource
        }
    }

    // Hide the mouse pointer in the car.
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.NoButton
        cursorShape: fullscreen ? Qt.BlankCursor : Qt.ArrowCursor
    }
}
