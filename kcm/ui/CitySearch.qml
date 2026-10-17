import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as Controls
import org.kde.kirigami as Kirigami

ColumnLayout {
    property string objectPrefix: ""
    property var settings
    Kirigami.FormData.label: i18nc("@label", "City:")
            Layout.fillWidth: true
            enabled: settings.liveSkyEnabled
            opacity: enabled ? 1.0 : 0.4
            spacing: Kirigami.Units.smallSpacing
            Controls.TextField {
                id: citySearch
                objectName: objectPrefix + "citySearch"
                Layout.fillWidth: true
                placeholderText: i18nc("@info:placeholder", "Type your city…")
                Accessible.name: i18nc("@label", "Search city")
                onTextEdited: { suggestions.visible = true; settings.locationSearch.search(text) }
                Keys.onDownPressed: suggestions.currentIndex = Math.min(suggestions.count - 1, suggestions.currentIndex + 1)
                Keys.onUpPressed: suggestions.currentIndex = Math.max(0, suggestions.currentIndex - 1)
                Keys.onEscapePressed: suggestions.visible = false
                onAccepted: if (suggestions.visible && suggestions.currentIndex >= 0) chooseCity(suggestions.currentIndex)
                function chooseCity(index) {
                    settings.selectLiveSkyPlace(index)
                    text = ""
                    suggestions.visible = false
                    forceActiveFocus()
                }
            }
            ListView {
                id: suggestions
                objectName: objectPrefix + "citySuggestions"
                Layout.fillWidth: true
                implicitHeight: Math.min(contentHeight, Kirigami.Units.gridUnit * 12)
                clip: true
                model: settings.locationSearch.results
                currentIndex: count > 0 ? 0 : -1
                Controls.ScrollBar.vertical: Controls.ScrollBar {}
                delegate: Controls.ItemDelegate {
                    required property var modelData
                    required property int index
                    width: ListView.view.width
                    text: modelData.display
                    highlighted: ListView.isCurrentItem
                    onClicked: citySearch.chooseCity(index)
                }
            }
            Controls.Label {
                Layout.fillWidth: true
                visible: text.length > 0
                text: settings.locationSearch.status
                wrapMode: Text.WordWrap
            }
            Controls.Label {
                Layout.fillWidth: true
                text: settings.liveSkyLocation.length === 0 ? i18nc("@info", "No location selected.")
                    : settings.liveSkyPlace.latitude !== undefined
                        ? i18nc("@info Selected city, latitude, longitude", "Selected: %1 (%2, %3)", settings.liveSkyLocation,
                            Number(settings.liveSkyPlace.latitude).toFixed(2), Number(settings.liveSkyPlace.longitude).toFixed(2))
                        : i18nc("@info Selected city without coordinates", "Selected: %1 — coordinates will be resolved when online", settings.liveSkyLocation)
                wrapMode: Text.WordWrap
            }
            Connections {
                target: settings
                function onLiveSkyLocationChanged() { citySearch.text = ""; suggestions.visible = false }
            }
        }
