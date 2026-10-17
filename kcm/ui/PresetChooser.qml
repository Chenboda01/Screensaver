import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as Controls
import org.kde.kirigami as Kirigami

ColumnLayout {
    id: chooser
    required property var settings
    readonly property var presets: [
        {key: "calm", name: i18nc("@item Preset", "Calm"), description: i18nc("@info Preset", "Quiet skies and gentle motion")},
        {key: "fun", name: i18nc("@item Preset", "Fun"), description: i18nc("@info Preset", "Playful adventures and discoveries")},
        {key: "live-sky", name: i18nc("@item Preset", "Live Sky"), description: i18nc("@info Preset", "A window to your local weather")},
        {key: "photos", name: i18nc("@item Preset", "Photo frame"), description: i18nc("@info Preset", "Your pictures, quietly on display")},
        {key: "battery-saver", name: i18nc("@item Preset", "Battery saver"), description: i18nc("@info Preset", "Fewer effects and lower power use")}
    ]
    Controls.Label {
        objectName: "activePresetLabel"
        Layout.fillWidth: true
        text: i18nc("@label Current preset", "Preset: %1", chooser.presets.find(p => p.key === chooser.settings.preset)?.name ?? i18nc("@item Preset", "Custom"))
        font.bold: true
        Accessible.role: Accessible.StaticText
    }
    GridLayout {
        Layout.fillWidth: true
        columns: Math.max(1, Math.min(5, Math.floor(width / (Kirigami.Units.gridUnit * 9))))
        rowSpacing: Kirigami.Units.smallSpacing
        columnSpacing: Kirigami.Units.smallSpacing
        Repeater {
            model: chooser.presets
            Controls.Button {
                id: card
                required property var modelData
                objectName: "preset-" + modelData.key
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 9
                Layout.minimumWidth: Kirigami.Units.gridUnit * 7
                checkable: true
                checked: chooser.settings.preset === modelData.key
                focusPolicy: Qt.StrongFocus
                Accessible.name: modelData.name
                Accessible.description: modelData.description
                text: modelData.name
                onClicked: {
                    chooser.settings.applyPreset(modelData.key)
                    if (modelData.key === "photos") chooser.settings.openSection("theme")
                    else if (chooser.settings.liveSkyEnabled && chooser.settings.liveSkyLocation.length === 0)
                        chooser.settings.openSection("liveSky")
                }
                contentItem: ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    Image {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Kirigami.Units.gridUnit * 4
                        source: "presets/" + card.modelData.key + ".webp"
                        fillMode: Image.PreserveAspectCrop
                        clip: true
                        Accessible.ignored: true
                    }
                    Controls.Label {
                        Layout.fillWidth: true
                        text: card.modelData.name
                        font.bold: true
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                    }
                    Controls.Label {
                        Layout.fillWidth: true
                        text: card.modelData.description
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
        }
    }
}
