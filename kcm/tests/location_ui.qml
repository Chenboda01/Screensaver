import QtQuick
import org.kde.kirigami as Kirigami
import "../ui"

Rectangle {
    width: 640
    height: 480
    color: Kirigami.Theme.backgroundColor
    CitySearch {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Kirigami.Units.largeSpacing
        settings: kcm
    }
}
