import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as Controls
import QtQuick.Dialogs
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCMUtils

KCMUtils.SimpleKCM {
    ColumnLayout {
        width: parent.width
        spacing: Kirigami.Units.largeSpacing
        Controls.Label {
            Layout.fillWidth: true
            text: i18nc("@label", "Choose how Bob appears and when KDE locks your screen.")
            wrapMode: Text.WordWrap
        }
        Controls.Button {
            objectName: "themePreviewButton"
            text: i18nc("@label", "Preview")
            icon.name: "view-preview"
            enabled: !kcm.previewRunning
            onClicked: kcm.previewTheme(this)
            Controls.ToolTip.text: i18nc("@label", "Preview current settings without applying them. Move the mouse or press any key to close.")
            Controls.ToolTip.visible: hovered
        }
        Kirigami.InlineMessage {
            Layout.fillWidth: true
            Layout.preferredWidth: Kirigami.Units.gridUnit * 30
            Layout.maximumWidth: Kirigami.Units.gridUnit * 30
            visible: kcm.previewError.length > 0
            text: kcm.previewError
            type: Kirigami.MessageType.Error
        }
        CollapsibleSection {
            id: themeSection
            settings: kcm
            sectionKey: "theme"
            title: i18nc("@label", "Theme")
            summary: [i18nc("@item:inlistbox Theme", "Random"), i18nc("@item:inlistbox Theme", "Space"), i18nc("@item:inlistbox Theme", "Mountains"), i18nc("@item:inlistbox Theme", "Snow"), i18nc("@item:inlistbox Theme", "Forest"), i18nc("@item:inlistbox Theme", "Futuristic City"), i18nc("@item:inlistbox Theme", "Aurora"), i18nc("@item:inlistbox Theme", "Ocean / Beach"), i18nc("@item:inlistbox Theme", "Desert"), i18nc("@item:inlistbox Theme", "Underwater"), i18nc("@item:inlistbox Theme", "My photos")][["random", "space", "mountains", "snow", "forest", "city", "aurora", "ocean", "desert", "underwater", "photos"].indexOf(kcm.theme)]
            form.twinFormLayouts: [themeSection.form, appearanceSection.form, clockSection.form, weatherSection.form, liveSkySection.form, agentsSection.form, bobosSection.form, performanceSection.form, lockSection.form]
            Controls.ComboBox {
                implicitContentWidthPolicy: Controls.ComboBox.WidestText
                Layout.maximumWidth: parent.width
                objectName: "themeChoice"
                Kirigami.FormData.label: i18nc("@label", "Theme:")
                model: [i18nc("@label", "Random"), i18nc("@label", "Space"), i18nc("@label", "Mountains"), i18nc("@label", "Snow"), i18nc("@label", "Forest"), i18nc("@label", "Futuristic City"), i18nc("@label", "Aurora"), i18nc("@label", "Ocean / Beach"), i18nc("@label", "Desert"), i18nc("@label", "Underwater"), i18nc("@label", "My photos")]
                currentIndex: Math.max(0, ["random", "space", "mountains", "snow", "forest", "city", "aurora", "ocean", "desert", "underwater", "photos"].indexOf(kcm.theme))
                onActivated: function(index) { kcm.theme = ["random", "space", "mountains", "snow", "forest", "city", "aurora", "ocean", "desert", "underwater", "photos"][index] }
            }
            Controls.TextField {
                id: photoFolderField
                objectName: "photoFolderField"
                Kirigami.FormData.label: i18nc("@label", "Photo folder:")
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: Math.max(0, parent.width - x - Kirigami.Units.largeSpacing)
                Layout.maximumWidth: Math.max(0, parent.width - x - Kirigami.Units.largeSpacing)
                text: kcm.photoFolder
                enabled: kcm.theme === "photos"
                Accessible.name: i18nc("@label", "Local photo folder")
                onTextEdited: kcm.photoFolder = text
                Connections {
                    target: kcm
                    function onPhotoFolderChanged() {
                        if (photoFolderField.text !== kcm.photoFolder) photoFolderField.text = kcm.photoFolder
                    }
                }
            }
            Controls.Button {
                objectName: "photoFolderBrowseButton"
                Kirigami.FormData.label: i18nc("@label", "Choose folder:")
                text: i18nc("@button", "Browse…")
                enabled: kcm.theme === "photos"
                icon.name: "folder-open"
                onClicked: photoFolderDialog.open()
            }
            FolderDialog {
                id: photoFolderDialog
                objectName: "photoFolderDialog"
                title: i18nc("@title:window", "Choose photo folder")
                currentFolder: "file://" + encodeURI(kcm.photoFolder)
                function stageSelectedFolder(folderUrl) {
                    kcm.setPhotoFolderUrl(folderUrl)
                }
                onAccepted: stageSelectedFolder(selectedFolder)
            }
            Controls.Switch {
                objectName: "photoIncludeSubfolders"
                Kirigami.FormData.label: i18nc("@label", "Subfolders:")
                text: checked ? i18nc("@label", "Include subfolders") : i18nc("@label", "Only this folder")
                checked: kcm.photoIncludeSubfolders
                enabled: kcm.theme === "photos"
                onToggled: kcm.photoIncludeSubfolders = checked
            }
            Controls.SpinBox {
                objectName: "photoInterval"
                Kirigami.FormData.label: i18nc("@label", "Seconds per photo:")
                from: 5
                to: 120
                stepSize: 1
                value: kcm.photoInterval
                enabled: kcm.theme === "photos"
                onValueModified: kcm.photoInterval = value
                textFromValue: function(value, locale) { return i18nc("@label Photo display interval in seconds", "%1 sec", value) }
            }
            Controls.ComboBox {
                objectName: "photoOrder"
                implicitContentWidthPolicy: Controls.ComboBox.WidestText
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: i18nc("@label", "Photo order:")
                model: [i18nc("@label Photo order", "By name"), i18nc("@label Photo order", "By date"), i18nc("@label Photo order", "Random")]
                property var values: ["name", "date", "random"]
                currentIndex: Math.max(0, values.indexOf(kcm.photoOrder))
                enabled: kcm.theme === "photos"
                onActivated: function(index) { kcm.photoOrder = values[index] }
            }
            Controls.ComboBox {
                objectName: "photoFit"
                implicitContentWidthPolicy: Controls.ComboBox.WidestText
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: i18nc("@label", "Photo fit:")
                model: [i18nc("@label Photo fit", "Fill screen and crop"), i18nc("@label Photo fit", "Fit whole photo with blurred background")]
                property var values: ["fill", "fit-blur"]
                currentIndex: Math.max(0, values.indexOf(kcm.photoFit))
                enabled: kcm.theme === "photos"
                onActivated: function(index) { kcm.photoFit = values[index] }
            }
            Controls.Label {
                objectName: "photoPrivacyLabel"
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: Math.max(0, parent.width - x - Kirigami.Units.largeSpacing)
                Layout.maximumWidth: Math.max(0, parent.width - x - Kirigami.Units.largeSpacing)
                Kirigami.FormData.label: i18nc("@label Photo privacy", "Privacy:")
                text: i18nc("@info Photo slideshow privacy", "Photos are read only from this local folder when My photos is selected. Hidden entries are skipped, and images are never uploaded. Remember that people nearby can see the photos while the screensaver is running.")
                color: Kirigami.Theme.textColor
                wrapMode: Text.WordWrap
                opacity: kcm.theme === "photos" ? 1.0 : 0.45
            }
        }
        CollapsibleSection {
            id: appearanceSection
            settings: kcm
            sectionKey: "appearance"
            title: i18nc("@label", "Customize Bob")
            summary: i18nc("@info Bob appearance summary", "%1 · %2", kcm.bobName, bobColorPreset.summaryLabels[bobColorPreset.currentIndex])
            form.twinFormLayouts: [themeSection.form, appearanceSection.form, clockSection.form, weatherSection.form, liveSkySection.form, agentsSection.form, bobosSection.form, performanceSection.form, lockSection.form]
            Controls.TextField {
                id: bobNameField
                objectName: "bobNameField"
                Kirigami.FormData.label: i18nc("@label", "Bob's name:")
                text: kcm.bobName
                maximumLength: 64
                Accessible.name: i18nc("@label", "Bob's display name")
                onTextEdited: kcm.bobName = text
                Connections {
                    target: kcm
                    function onBobNameChanged() {
                        if (bobNameField.text !== kcm.bobName) bobNameField.text = kcm.bobName
                    }
                }
            }
            Controls.ComboBox {
                id: bobColorPreset
                objectName: "bobColorPreset"
                implicitContentWidthPolicy: Controls.ComboBox.WidestText
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: i18nc("@label", "Bob's color:")
                model: [i18nc("@item:inlistbox Bob color", "Cyan"), i18nc("@item:inlistbox Bob color", "Green"), i18nc("@item:inlistbox Bob color", "Purple"), i18nc("@item:inlistbox Bob color", "Orange"), i18nc("@item:inlistbox Bob color", "Pink"), i18nc("@item:inlistbox Bob color", "Gold"), i18nc("@item:inlistbox Bob color", "Custom")]
                property var values: ["cyan", "green", "purple", "orange", "pink", "gold", "custom"]
                property var summaryLabels: [i18nc("@label Bob color summary", "Cyan"), i18nc("@label Bob color summary", "Green"), i18nc("@label Bob color summary", "Purple"), i18nc("@label Bob color summary", "Orange"), i18nc("@label Bob color summary", "Pink"), i18nc("@label Bob color summary", "Gold"), i18nc("@label Bob color summary", "Custom color")]
                currentIndex: Math.max(0, values.indexOf(kcm.bobColorPreset))
                onActivated: function(index) { kcm.bobColorPreset = values[index] }
            }
            Controls.Button {
                objectName: "bobCustomColorButton"
                Kirigami.FormData.label: i18nc("@label", "Custom color:")
                text: i18nc("@label", "Choose color…")
                enabled: kcm.bobColorPreset === "custom"
                opacity: enabled ? 1.0 : 0.4
                icon.name: "color-picker"
                onClicked: bobColorDialog.open()
                Rectangle {
                    width: 18
                    height: 18
                    radius: 4
                    color: kcm.bobCustomColor
                    border.color: Kirigami.Theme.textColor
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
            Controls.ComboBox {
                id: bobAccessory
                objectName: "bobAccessory"
                implicitContentWidthPolicy: Controls.ComboBox.WidestText
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: i18nc("@label", "Accessory:")
                model: [i18nc("@item:inlistbox Bob accessory", "None"), i18nc("@item:inlistbox Bob accessory", "Cap"), i18nc("@item:inlistbox Bob accessory", "Bow tie"), i18nc("@item:inlistbox Bob accessory", "Headphones"), i18nc("@item:inlistbox Bob accessory", "Flower"), i18nc("@item:inlistbox Bob accessory", "Crown"), i18nc("@item:inlistbox Bob accessory", "Antenna ball")]
                property var values: ["none", "cap", "bow-tie", "headphones", "flower", "crown", "antenna-ball"]
                currentIndex: Math.max(0, values.indexOf(kcm.bobAccessory))
                onActivated: function(index) { kcm.bobAccessory = values[index] }
            }
            Controls.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: i18nc("@label", "Preview:")
                text: i18nc("@label", "Use Preview above to see Bob with these staged settings. Weather accessories can layer alongside your choice; your headwear stays visible when weather gear would overlap.")
                wrapMode: Text.WordWrap
            }
        }
        CollapsibleSection {
            id: clockSection
            settings: kcm
            sectionKey: "clock"
            title: i18nc("@label", "Clock")
            summary: kcm.clockVisible ? i18nc("@info Clock summary: format, position", "On · %1 · %2", kcm.clockFormat === "24h" ? i18nc("@label", "24-hour") : i18nc("@label", "12-hour"), clockPosition.summaryLabels[clockPosition.currentIndex]) : i18nc("@label Feature state", "Off")
            form.twinFormLayouts: [themeSection.form, appearanceSection.form, clockSection.form, weatherSection.form, liveSkySection.form, agentsSection.form, bobosSection.form, performanceSection.form, lockSection.form]
            Controls.Switch {
                Kirigami.FormData.label: i18nc("@label", "Clock:")
                text: checked ? i18nc("@label", "Visible") : i18nc("@label", "Hidden")
                checked: kcm.clockVisible
                onToggled: kcm.clockVisible = checked
            }
            Controls.ComboBox {
                implicitContentWidthPolicy: Controls.ComboBox.WidestText
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: i18nc("@label", "Time format:")
                model: [i18nc("@label", "12-hour"), i18nc("@label", "24-hour")]
                currentIndex: kcm.clockFormat === "24h" ? 1 : 0
                enabled: kcm.clockVisible
                onActivated: function(index) { kcm.clockFormat = index === 1 ? "24h" : "12h" }
            }
            Controls.Switch {
                Kirigami.FormData.label: i18nc("@label", "Date:")
                text: checked ? i18nc("@label", "Show date below the time") : i18nc("@label", "Hide date")
                checked: kcm.showDate
                enabled: kcm.clockVisible
                onToggled: kcm.showDate = checked
            }
            Controls.ComboBox {
                implicitContentWidthPolicy: Controls.ComboBox.WidestText
                Layout.maximumWidth: parent.width
                id: clockPosition
                Kirigami.FormData.label: i18nc("@label", "Clock position:")
                model: [i18nc("@label", "Top left"), i18nc("@label", "Top center"), i18nc("@label", "Top right"), i18nc("@label", "Center left"), i18nc("@label", "Center"), i18nc("@label", "Center right"), i18nc("@label", "Bottom left"), i18nc("@label", "Bottom center"), i18nc("@label", "Bottom right")]
                readonly property var summaryLabels: [i18nc("@label Clock position summary", "top left"), i18nc("@label Clock position summary", "top center"), i18nc("@label Clock position summary", "top right"), i18nc("@label Clock position summary", "center left"), i18nc("@label Clock position summary", "center center"), i18nc("@label Clock position summary", "center right"), i18nc("@label Clock position summary", "bottom left"), i18nc("@label Clock position summary", "bottom center"), i18nc("@label Clock position summary", "bottom right")]
                property var values: ["top-left", "top-center", "top-right", "center-left", "center-center", "center-right", "bottom-left", "bottom-center", "bottom-right"]
                currentIndex: Math.max(0, values.indexOf(kcm.clockPosition))
                enabled: kcm.clockVisible
                onActivated: function(index) { kcm.clockPosition = values[index] }
            }
            Controls.Switch {
                objectName: "nowPlayingEnabled"
                Kirigami.FormData.label: i18nc("@label", "Show what's playing:")
                text: checked ? i18nc("@label", "Show media title and artist") : i18nc("@label", "Hidden")
                checked: kcm.nowPlayingEnabled
                onToggled: kcm.nowPlayingEnabled = checked
                Accessible.name: i18nc("@label", "Show what's playing")
            }
            Controls.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
                wrapMode: Text.WordWrap
                text: i18nc("@info", "Off by default: media titles can be personal. Shows player metadata on the primary screen only; never controls playback. Previews keep media hidden.")
            }
            Controls.SpinBox {
                Kirigami.FormData.label: i18nc("@label", "Clock font size:")
                from: 16
                to: 72
                stepSize: 1
                editable: true
                value: kcm.clockFontSize
                enabled: kcm.clockVisible
                onValueModified: kcm.clockFontSize = value
                textFromValue: function(value, locale) { return i18nc("@label Font size in points", "%1 pt", value) }
                valueFromText: function(text, locale) {
                    var parsed = parseInt(text, 10)
                    return isNaN(parsed) ? 48 : Math.min(72, Math.max(16, parsed))
                }
            }
        }
        CollapsibleSection {
            id: weatherSection
            settings: kcm
            sectionKey: "weather"
            title: i18nc("@label", "Weather")
            summary: kcm.theme === "space" ? i18nc("@info", "No weather effects in Space") : kcm.liveSkyEnabled ? i18nc("@info", "Managed by Live Sky") : [kcm.rainEnabled ? i18nc("@label Weather", "Rain") : "", kcm.snowEnabled ? i18nc("@label Weather", "Snow") : "", kcm.thunderstormsEnabled ? i18nc("@label Weather", "Thunderstorms") : "", kcm.fogEnabled ? i18nc("@label Weather", "Fog") : "", kcm.shootingStarsEnabled ? i18nc("@label Weather", "Shooting stars") : ""].filter(function(value) { return value.length > 0 }).join(i18nc("Separator between enabled weather effects", " · ")) || i18nc("@label Feature state", "Off")
            form.twinFormLayouts: [themeSection.form, appearanceSection.form, clockSection.form, weatherSection.form, liveSkySection.form, agentsSection.form, bobosSection.form, performanceSection.form, lockSection.form]
            Controls.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: i18nc("@label", "Animated weather:")
                text: i18nc("@label", "Weather and shooting-star effects are disabled in Space. Shooting stars are available on the landscape themes.")
                wrapMode: Text.WordWrap
            }
            Controls.Switch {
                objectName: "bobWeatherEnabledSwitch"
                Kirigami.FormData.label: i18nc("@label", "Bob's weather accessories:")
                text: checked ? i18nc("@label", "Enabled") : i18nc("@label", "Disabled")
                checked: kcm.bobWeatherEnabled
                enabled: kcm.liveSkyEnabled && kcm.theme !== "space"
                opacity: enabled ? 1.0 : 0.7
                onToggled: kcm.bobWeatherEnabled = checked
                Controls.ToolTip.text: i18nc("@info:tooltip", "Bob can wear weather accessories when Live Sky is enabled.")
                Controls.ToolTip.visible: hovered
            }
            Controls.Switch {
                Kirigami.FormData.label: i18nc("@label", "Rain:")
                text: checked ? i18nc("@label", "Enabled") : i18nc("@label", "Disabled")
                checked: kcm.rainEnabled
                enabled: !kcm.liveSkyEnabled && kcm.theme !== "space"
                opacity: enabled ? 1.0 : 0.4
                onToggled: kcm.rainEnabled = checked
            }
            Controls.Switch {
                Kirigami.FormData.label: i18nc("@label", "Snowfall:")
                text: checked ? i18nc("@label", "Enabled") : i18nc("@label", "Disabled")
                checked: kcm.snowEnabled
                enabled: !kcm.liveSkyEnabled && kcm.theme !== "space"
                opacity: enabled ? 1.0 : 0.4
                onToggled: kcm.snowEnabled = checked
            }
            Controls.Switch {
                Kirigami.FormData.label: i18nc("@label", "Thunderstorms:")
                text: checked ? i18nc("@label", "Enabled") : i18nc("@label", "Disabled")
                checked: kcm.thunderstormsEnabled
                enabled: !kcm.liveSkyEnabled && kcm.theme !== "space"
                opacity: enabled ? 1.0 : 0.4
                onToggled: kcm.thunderstormsEnabled = checked
            }
            Controls.Switch {
                Kirigami.FormData.label: i18nc("@label", "Fog:")
                text: checked ? i18nc("@label", "Enabled") : i18nc("@label", "Disabled")
                checked: kcm.fogEnabled
                enabled: !kcm.liveSkyEnabled && kcm.theme !== "space"
                opacity: enabled ? 1.0 : 0.4
                onToggled: kcm.fogEnabled = checked
            }
            Controls.Switch {
                Kirigami.FormData.label: i18nc("@label", "Shooting stars (landscapes):")
                text: checked ? i18nc("@label", "Enabled") : i18nc("@label", "Disabled")
                checked: kcm.shootingStarsEnabled
                enabled: !kcm.liveSkyEnabled && kcm.theme !== "space"
                opacity: enabled ? 1.0 : 0.4
                onToggled: kcm.shootingStarsEnabled = checked
            }
        }
        CollapsibleSection {
            id: liveSkySection
            settings: kcm
            sectionKey: "liveSky"
            title: i18nc("@label", "Live Sky")
            summary: kcm.liveSkyEnabled ? i18nc("@info Live Sky summary: location, temperature unit", "On · %1 · °%2", kcm.liveSkyLocation || i18nc("@info", "No location selected"), kcm.liveSkyUnits.toUpperCase()) : i18nc("@label Feature state", "Off")
            form.twinFormLayouts: [themeSection.form, appearanceSection.form, clockSection.form, weatherSection.form, liveSkySection.form, agentsSection.form, bobosSection.form, performanceSection.form, lockSection.form]
            Controls.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: i18nc("@label", "Live Sky:")
                text: i18nc("@label", "Adapt landscape skies and weather to local conditions. In Space, Live Sky shows Earth’s day/night and the Moon phase, without weather effects or shooting stars. Manual weather effects are dimmed while Live Sky is enabled.")
                wrapMode: Text.WordWrap
            }
            Controls.Switch {
                Kirigami.FormData.label: i18nc("@label", "Enable Live Sky:")
                text: checked ? i18nc("@label", "On") : i18nc("@label", "Off")
                checked: kcm.liveSkyEnabled
                onToggled: kcm.liveSkyEnabled = checked
            }
            CitySearch {
                settings: kcm
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
            }
            Controls.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
                text: i18nc("@label", "Typed searches are sent to Open-Meteo only while Live Sky is enabled. Choose a suggestion to set your location; Apply saves it. Offline search uses the bundled city catalog. No IP-based lookup is used.")
                wrapMode: Text.WordWrap
            }
            Controls.ComboBox {
                implicitContentWidthPolicy: Controls.ComboBox.WidestText
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: i18nc("@label", "Temperature units:")
                model: [i18nc("@label", "Celsius"), i18nc("@label", "Fahrenheit")]
                currentIndex: kcm.liveSkyUnits === "f" ? 1 : 0
                enabled: kcm.liveSkyEnabled
                opacity: enabled ? 1.0 : 0.4
                onActivated: function(index) { kcm.liveSkyUnits = index === 1 ? "f" : "c" }
            }
            Controls.ComboBox {
                implicitContentWidthPolicy: Controls.ComboBox.WidestText
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: i18nc("@label", "Weather refresh:")
                model: [i18ncp("@item:inlistbox Weather refresh interval", "Every %1 minute", "Every %1 minutes", 15), i18ncp("@item:inlistbox Weather refresh interval", "Every %1 minute", "Every %1 minutes", 30), i18ncp("@item:inlistbox Weather refresh interval", "Every %1 minute", "Every %1 minutes", 60)]
                currentIndex: [15, 30, 60].indexOf(kcm.liveSkyInterval)
                enabled: kcm.liveSkyEnabled
                opacity: enabled ? 1.0 : 0.4
                onActivated: function(index) { kcm.liveSkyInterval = [15, 30, 60][index] }
            }
            Controls.Switch {
                Kirigami.FormData.label: i18nc("@label", "Current conditions:")
                text: checked ? i18nc("@label", "Show weather under the clock") : i18nc("@label", "Hide weather text")
                checked: kcm.liveSkyConditions
                enabled: kcm.liveSkyEnabled
                opacity: enabled ? 1.0 : 0.4
                onToggled: kcm.liveSkyConditions = checked
            }
        }
        CollapsibleSection {
            id: agentsSection
            settings: kcm
            sectionKey: "agents"
            title: i18nc("@label", "AI Agents")
            summary: [i18nc("@label", "Always ask"), i18nc("@label", "Always start screensaver"), i18nc("@label", "Do not start while agents are running")][["ask", "start", "block"].indexOf(kcm.agentDetectionMode)]
            form.twinFormLayouts: [themeSection.form, appearanceSection.form, clockSection.form, weatherSection.form, liveSkySection.form, agentsSection.form, bobosSection.form, performanceSection.form, lockSection.form]
            Controls.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: i18nc("@label", "AI Agent Detection:")
                text: i18nc("@label", "Choose what happens when an active terminal agent is detected. Manual launches always remain available.")
                wrapMode: Text.WordWrap
            }
            Controls.ComboBox {
                implicitContentWidthPolicy: Controls.ComboBox.WidestText
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: i18nc("@label", "When an agent is active:")
                model: [i18nc("@label", "Always ask"), i18nc("@label", "Always start screensaver"), i18nc("@label", "Don't start screensaver while agents are running")]
                currentIndex: ["ask", "start", "block"].indexOf(kcm.agentDetectionMode)
                onActivated: function(index) { kcm.agentDetectionMode = ["ask", "start", "block"][index] }
            }
            Controls.Switch {
                objectName: "agentStatusEnabled"
                Kirigami.FormData.label: i18nc("@label", "Show AI agent status on the screensaver:")
                text: checked ? i18nc("@label", "Enabled") : i18nc("@label", "Disabled")
                checked: kcm.agentStatusEnabled
                onToggled: kcm.agentStatusEnabled = checked
            }
            Controls.CheckBox {
                objectName: "agentPromptNever"
                Kirigami.FormData.label: i18nc("@label", "Automatic answer:")
                text: i18nc("@label", "Never (wait for me)")
                visible: kcm.agentDetectionMode === "ask"
                checked: kcm.agentPromptTimeout === 0
                onToggled: kcm.agentPromptTimeout = checked ? 0 : 10
            }
            Controls.SpinBox {
                objectName: "agentPromptTimeout"
                Kirigami.FormData.label: i18nc("@label", "Answer automatically after (s):")
                Accessible.name: i18nc("@label", "Answer automatically after, in seconds")
                visible: kcm.agentDetectionMode === "ask"
                enabled: kcm.agentPromptTimeout !== 0
                from: 5
                to: 120
                value: kcm.agentPromptTimeout || 10
                editable: true
                onValueModified: kcm.agentPromptTimeout = value
            }
            Controls.ComboBox {
                implicitContentWidthPolicy: Controls.ComboBox.WidestText
                objectName: "agentPromptTimeoutAction"
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: i18nc("@label", "When time runs out:")
                visible: kcm.agentDetectionMode === "ask"
                enabled: kcm.agentPromptTimeout !== 0
                model: [i18nc("@label", "Start screensaver (Yes)"), i18nc("@label", "Keep desktop visible (No)")]
                currentIndex: kcm.agentPromptTimeoutAction === "cancel" ? 1 : 0
                onActivated: function(index) { kcm.agentPromptTimeoutAction = index === 1 ? "cancel" : "start" }
            }
            Controls.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
                visible: kcm.agentDetectionMode === "ask"
                text: i18nc("@label", "Interacting with the prompt pauses its countdown. Automatic answers never remember a choice.")
                wrapMode: Text.WordWrap
            }
            Controls.Button {
                objectName: "resetAgentChoiceButton"
                Kirigami.FormData.label: i18nc("@label", "Remembered choice:")
                text: i18nc("@label", "Reset to Always ask")
                enabled: kcm.agentDetectionMode !== "ask"
                onClicked: kcm.resetRememberedAgentChoice()
            }
        }
        CollapsibleSection {
            id: bobosSection
            settings: kcm
            sectionKey: "bobos"
            title: i18nc("@label", "BobOS")
            summary: !kcm.phoneEnabled ? i18nc("@info", "Phone off") : !kcm.bobosEnabled ? i18nc("@info", "Phone on · BobOS off") : i18ncp("@info BobOS delay summary", "On · After %1 min", "On · After %1 min", kcm.bobosActivationDelay)
            form.twinFormLayouts: [themeSection.form, appearanceSection.form, clockSection.form, weatherSection.form, liveSkySection.form, agentsSection.form, bobosSection.form, performanceSection.form, lockSection.form]
            Controls.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: i18nc("@label", "Bob's Phone & BobOS 2.0")
                text: i18nc("@label", "Bob's Phone contains a fictional mobile operating system. Its apps, messages, places, and games are animated drawings only.")
                wrapMode: Text.WordWrap
            }
            Controls.Switch {
                Kirigami.FormData.label: i18nc("@label", "Enable Bob's Phone:")
                text: checked ? i18nc("@label", "Enabled") : i18nc("@label", "Disabled")
                checked: kcm.phoneEnabled
                onToggled: kcm.phoneEnabled = checked
            }
            Controls.Switch {
                Kirigami.FormData.label: i18nc("@label", "Enable BobOS:")
                text: checked ? i18nc("@label", "Enabled") : i18nc("@label", "Disabled")
                checked: kcm.bobosEnabled
                enabled: kcm.phoneEnabled
                opacity: enabled ? 1.0 : 0.4
                onToggled: kcm.bobosEnabled = checked
            }
            Controls.SpinBox {
                objectName: "bobosDelay"
                Kirigami.FormData.label: i18nc("@label", "BobOS Activation Delay:")
                from: 1
                to: 30
                stepSize: 1
                editable: true
                value: kcm.bobosActivationDelay
                enabled: kcm.phoneEnabled && kcm.bobosEnabled
                opacity: enabled ? 1.0 : 0.4
                onValueModified: kcm.bobosActivationDelay = value
                textFromValue: function(value, locale) { return i18ncp("@label Duration", "%1 minute", "%1 minutes", value) }
                valueFromText: function(text, locale) {
                    var parsed = parseInt(text, 10)
                    return isNaN(parsed) ? 3 : Math.min(30, Math.max(1, parsed))
                }
            }
            Controls.Switch {
                Kirigami.FormData.label: i18nc("@label", "AI Wi-Fi animation:")
                text: checked ? i18nc("@label", "Shown before BobOS opens") : i18nc("@label", "Skipped")
                checked: kcm.showWifiAnimation
                enabled: kcm.phoneEnabled && kcm.bobosEnabled
                opacity: enabled ? 1.0 : 0.4
                onToggled: kcm.showWifiAnimation = checked
            }
            Controls.Button {
                objectName: "bobosPreviewButton"
                Kirigami.FormData.label: i18nc("@label", "BobOS preview:")
                text: i18nc("@label", "Preview full adventure")
                enabled: !kcm.previewRunning && kcm.phoneEnabled && kcm.bobosEnabled
                opacity: enabled ? 1.0 : 0.4
                onClicked: kcm.previewBobOS(kcm.showWifiAnimation)
            }
        }
        CollapsibleSection {
            id: performanceSection
            settings: kcm
            sectionKey: "performance"
            title: i18nc("@label", "Performance")
            summary: [i18nc("@label Performance mode", "Smooth"), i18nc("@label Performance mode", "Balanced"), i18nc("@label Performance mode", "Battery saver")][["smooth", "balanced", "battery-saver"].indexOf(kcm.performanceMode)]
            form.twinFormLayouts: [themeSection.form, appearanceSection.form, clockSection.form, weatherSection.form, liveSkySection.form, agentsSection.form, bobosSection.form, performanceSection.form, lockSection.form]
            Controls.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: i18nc("@label", "Frame pacing:")
                text: i18nc("@info", "Balanced runs at 30 fps on AC power, then 15 fps on battery or after 15 minutes. Battery saver uses 10 fps.")
                wrapMode: Text.WordWrap
            }
            Controls.ComboBox {
                objectName: "performanceMode"
                implicitContentWidthPolicy: Controls.ComboBox.WidestText
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: i18nc("@label", "Performance mode:")
                model: [i18nc("@label Performance mode", "Smooth (30 fps)"), i18nc("@label Performance mode", "Balanced"), i18nc("@label Performance mode", "Battery saver (10 fps)")]
                currentIndex: ["smooth", "balanced", "battery-saver"].indexOf(kcm.performanceMode)
                onActivated: function(index) { kcm.performanceMode = ["smooth", "balanced", "battery-saver"][index] }
            }
            Controls.CheckBox {
                objectName: "reduceMotion"
                Kirigami.FormData.label: i18nc("@label", "Motion:")
                text: i18nc("@label", "Reduce motion and flashes")
                checked: kcm.reduceMotion
                onToggled: kcm.reduceMotion = checked
            }
            Controls.ComboBox {
                objectName: "burnInProtection"
                implicitContentWidthPolicy: Controls.ComboBox.WidestText
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: i18nc("@label", "Burn-in protection:")
                model: [i18nc("@label Burn-in protection", "Off"), i18nc("@label Burn-in protection", "Standard"), i18nc("@label Burn-in protection", "Strong")]
                currentIndex: ["off", "standard", "strong"].indexOf(kcm.burnInProtection)
                onActivated: function(index) { kcm.burnInProtection = ["off", "standard", "strong"][index] }
            }
            Controls.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
                text: kcm.burnInProtection === "strong"
                    ? i18nc("@info Burn-in protection", "Moves the scene and clock, then fades to black between 30 and 60 minutes. Any input closes the screensaver and cancels the fade.")
                    : kcm.burnInProtection === "standard"
                        ? i18nc("@info Burn-in protection", "Moves the scene slowly and lets the clock drift within its selected area.")
                        : i18nc("@info Burn-in protection", "Off preserves the original fixed layout and brightness.")
                wrapMode: Text.WordWrap
            }
        }
        CollapsibleSection {
            id: lockSection
            settings: kcm
            sectionKey: "lock"
            title: i18nc("@label", "Lock")
            summary: kcm.passwordLock ? i18ncp("@info Lock delay summary", "Password after %1 min", "Password after %1 min", kcm.lockMinutes) : i18nc("@info", "Screensaver password countdown off")
            form.twinFormLayouts: [themeSection.form, appearanceSection.form, clockSection.form, weatherSection.form, liveSkySection.form, agentsSection.form, bobosSection.form, performanceSection.form, lockSection.form]
            Controls.Switch {
                id: passwordSwitch
                Kirigami.FormData.label: i18nc("@label", "Password unlock:")
                text: checked ? i18nc("@label", "On") : i18nc("@label", "Off")
                checked: kcm.passwordLock
                onToggled: kcm.passwordLock = checked
            }
            Controls.SpinBox {
                Kirigami.FormData.label: i18nc("@label", "Require password after:")
                from: 1
                to: 60
                stepSize: 1
                editable: true
                value: kcm.lockMinutes
                enabled: kcm.passwordLock
                opacity: enabled ? 1.0 : 0.4
                onValueModified: kcm.lockMinutes = value
                textFromValue: function(value, locale) { return i18ncp("@label Duration", "%1 minute", "%1 minutes", value) }
                valueFromText: function(text, locale) {
                    var parsed = parseInt(text, 10)
                    return isNaN(parsed) ? 2 : Math.min(60, Math.max(1, parsed))
                }
            }
            Controls.CheckBox {
                Kirigami.FormData.label: i18nc("@label", "Show countdown:")
                text: i18nc("@label", "Display time until password is required")
                checked: kcm.showTimer
                enabled: kcm.passwordLock
                opacity: enabled ? 1.0 : 0.4
                onToggled: kcm.showTimer = checked
            }
            Controls.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
                text: i18nc("@label", "Countdown color preview (elapsed time)")
                Kirigami.FormData.label: i18nc("@label", "Color transition:")
            }
            Rectangle {
                implicitWidth: 320
                implicitHeight: 14
                radius: 7
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "#2de669" }
                    GradientStop { position: 0.25; color: "#fcdc2b" }
                    GradientStop { position: 0.5; color: "#ff8a21" }
                    GradientStop { position: 0.75; color: "#ff3546" }
                    GradientStop { position: 1.0; color: "#ff3546" }
                }
            }
            Controls.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
                text: i18nc("@label", "The countdown begins when Bob appears. Its color smoothly changes green → yellow → orange → red as time runs out. KDE handles the actual password lock.")
                wrapMode: Text.WordWrap
            }
            Controls.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
                text: i18nc("@label", "For password protection, configure KDE Screen Locking to require the password immediately and disable any unlock grace period. Disabling this option does not disable KDE's separate automatic locking or suspend locks.")
                wrapMode: Text.WordWrap
            }
        }
        Controls.Label {
            Layout.fillWidth: true
            text: i18nc("@label", "Press Apply to save your changes. Changes take effect the next time Bob starts.")
            wrapMode: Text.WordWrap
        }
    }
    ColorDialog {
        id: bobColorDialog
        objectName: "bobColorDialog"
        title: i18nc("@title:window", "Choose Bob's color")
        selectedColor: kcm.bobCustomColor
        onAccepted: kcm.bobCustomColor = selectedColor.toString()
    }
}
