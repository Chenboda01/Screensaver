import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as Controls
import org.kde.kirigami as Kirigami

ColumnLayout {
    id: section
    required property var settings
    required property string sectionKey
    required property string title
    property string summary: ""
    property bool expanded: false
    property bool initialized: false
    readonly property bool modified: settings.modifiedSections.indexOf(sectionKey) !== -1
    property alias form: form
    default property alias contentData: form.data
    objectName: sectionKey + "Section"
    Layout.fillWidth: true
    spacing: Kirigami.Units.smallSpacing

    Component.onCompleted: {
        expanded = settings.sectionExpanded(sectionKey)
        initialized = true
    }
    onExpandedChanged: if (initialized) settings.setSectionExpanded(sectionKey, expanded)

    data: [
        Controls.ToolButton {
            id: header
            objectName: section.sectionKey + "Header"
            Layout.fillWidth: true
            focusPolicy: Qt.StrongFocus
            Accessible.name: section.title
            Accessible.description: section.modified
                ? i18nc("@info:accessible Section state, summary", "%1. %2. Unapplied changes", section.expanded ? i18nc("@info:accessible", "Expanded") : i18nc("@info:accessible", "Collapsed"), section.summary)
                : i18nc("@info:accessible Section state, summary", "%1. %2", section.expanded ? i18nc("@info:accessible", "Expanded") : i18nc("@info:accessible", "Collapsed"), section.summary)
            Accessible.expandable: true
            Accessible.expanded: section.expanded
            onClicked: section.expanded = !section.expanded
            Keys.onReturnPressed: clicked()
            Keys.onEnterPressed: clicked()
            Keys.onLeftPressed: section.expanded = false
            Keys.onRightPressed: section.expanded = true
            contentItem: RowLayout {
                spacing: Kirigami.Units.smallSpacing
                Kirigami.Icon {
                    source: section.expanded ? "arrow-down" : "arrow-right"
                    implicitWidth: Kirigami.Units.iconSizes.small
                    implicitHeight: implicitWidth
                }
                Controls.Label {
                    text: section.title
                    font.bold: true
                }
                Controls.Label {
                    text: "●"
                    visible: section.modified
                    Accessible.ignored: true
                }
                Controls.Label {
                    Layout.fillWidth: true
                    text: section.expanded ? "" : section.summary
                    elide: Text.ElideRight
                    color: Kirigami.Theme.textColor
                }
            }
            Controls.ToolTip.visible: hovered && !section.expanded
            Controls.ToolTip.text: section.summary
        },
        Item {
            Layout.fillWidth: true
            implicitHeight: section.expanded ? form.implicitHeight : 0
            clip: true
            visible: implicitHeight > 0
            enabled: section.expanded
            Behavior on implicitHeight {
                enabled: section.initialized
                NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.InOutQuad }
            }
            Kirigami.FormLayout {
                id: form
                width: parent.width
                visible: section.expanded
            }
        }
    ]
}
