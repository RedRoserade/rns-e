import QtQuick
import QtQuick.Layouts
import ".."


Item {
    Rectangle {
        anchors.fill: parent
        color: Theme.background
    }

    GridLayout {
        anchors.verticalCenter: parent.verticalCenter

        columns: 2
        columnSpacing: 30

        Rectangle {
            Layout.preferredWidth: 160
            Layout.preferredHeight: 160
            border.width: 1
            border.color: Theme.accent
            color: "transparent"
        }

        ColumnLayout {
            Layout.fillWidth: true

            Text { text: "HERTZ 98 FM"; font.pixelSize: Theme.fontSizeTitle; color: Theme.accent }
            Text { text: "98.0"; font.pixelSize: Theme.fontSizeBody; color: Theme.accent }
            // Text { text: "HERTZ FM" }
        }
    }
}