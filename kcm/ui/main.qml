import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as Controls
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCMUtils

KCMUtils.SimpleKCM {
    ColumnLayout {
        width: parent.width
        spacing: Kirigami.Units.largeSpacing
        Controls.Label {
            Layout.fillWidth: true
            text: "Choose how Bob appears and when KDE locks your screen."
            wrapMode: Text.WordWrap
        }
        Controls.Button {
            objectName: "themePreviewButton"
            text: "Preview"
            icon.name: "view-preview"
            enabled: !kcm.previewRunning
            onClicked: kcm.previewTheme(this)
            Controls.ToolTip.text: "Preview current settings without applying them. Move the mouse or press any key to close."
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
            title: "Theme"
            summary: ["Random", "Space", "Mountains", "Snow", "Forest", "Futuristic City"][["random", "space", "mountains", "snow", "forest", "city"].indexOf(kcm.theme)]
            form.twinFormLayouts: [themeSection.form, clockSection.form, weatherSection.form, liveSkySection.form, agentsSection.form, bobosSection.form, lockSection.form]
            Controls.ComboBox {
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: "Theme:"
                model: ["Random", "Space", "Mountains", "Snow", "Forest", "Futuristic City"]
                currentIndex: Math.max(0, ["random", "space", "mountains", "snow", "forest", "city"].indexOf(kcm.theme))
                onActivated: function(index) { kcm.theme = ["random", "space", "mountains", "snow", "forest", "city"][index] }
            }
        }
        CollapsibleSection {
            id: clockSection
            settings: kcm
            sectionKey: "clock"
            title: "Clock"
            summary: kcm.clockVisible ? "On · " + (kcm.clockFormat === "24h" ? "24-hour" : "12-hour") + " · " + kcm.clockPosition.replace(/-/g, " ") : "Off"
            form.twinFormLayouts: [themeSection.form, clockSection.form, weatherSection.form, liveSkySection.form, agentsSection.form, bobosSection.form, lockSection.form]
            Controls.Switch {
                Kirigami.FormData.label: "Clock:"
                text: checked ? "Visible" : "Hidden"
                checked: kcm.clockVisible
                onToggled: kcm.clockVisible = checked
            }
            Controls.ComboBox {
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: "Time format:"
                model: ["12-hour", "24-hour"]
                currentIndex: kcm.clockFormat === "24h" ? 1 : 0
                enabled: kcm.clockVisible
                onActivated: function(index) { kcm.clockFormat = index === 1 ? "24h" : "12h" }
            }
            Controls.Switch {
                Kirigami.FormData.label: "Date:"
                text: checked ? "Show date below the time" : "Hide date"
                checked: kcm.showDate
                enabled: kcm.clockVisible
                onToggled: kcm.showDate = checked
            }
            Controls.ComboBox {
                Layout.maximumWidth: parent.width
                id: clockPosition
                Kirigami.FormData.label: "Clock position:"
                model: ["Top left", "Top center", "Top right", "Center left", "Center", "Center right", "Bottom left", "Bottom center", "Bottom right"]
                property var values: ["top-left", "top-center", "top-right", "center-left", "center-center", "center-right", "bottom-left", "bottom-center", "bottom-right"]
                currentIndex: Math.max(0, values.indexOf(kcm.clockPosition))
                enabled: kcm.clockVisible
                onActivated: function(index) { kcm.clockPosition = values[index] }
            }
            Controls.SpinBox {
                Kirigami.FormData.label: "Clock font size:"
                from: 16
                to: 72
                stepSize: 1
                editable: true
                value: kcm.clockFontSize
                enabled: kcm.clockVisible
                onValueModified: kcm.clockFontSize = value
                textFromValue: function(value, locale) { return value + " pt" }
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
            title: "Weather"
            summary: kcm.theme === "space" ? "No weather effects in Space" : kcm.liveSkyEnabled ? "Managed by Live Sky" : [kcm.rainEnabled ? "Rain" : "", kcm.snowEnabled ? "Snow" : "", kcm.thunderstormsEnabled ? "Thunderstorms" : "", kcm.fogEnabled ? "Fog" : "", kcm.shootingStarsEnabled ? "Shooting stars" : ""].filter(function(value) { return value.length > 0 }).join(" · ") || "Off"
            form.twinFormLayouts: [themeSection.form, clockSection.form, weatherSection.form, liveSkySection.form, agentsSection.form, bobosSection.form, lockSection.form]
            Controls.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: "Animated weather:"
                text: "Weather and shooting-star effects are disabled in Space. Shooting stars are available on the landscape themes."
                wrapMode: Text.WordWrap
            }
            Controls.Switch {
                Kirigami.FormData.label: "Rain:"
                text: checked ? "Enabled" : "Disabled"
                checked: kcm.rainEnabled
                enabled: !kcm.liveSkyEnabled && kcm.theme !== "space"
                opacity: enabled ? 1.0 : 0.4
                onToggled: kcm.rainEnabled = checked
            }
            Controls.Switch {
                Kirigami.FormData.label: "Snowfall:"
                text: checked ? "Enabled" : "Disabled"
                checked: kcm.snowEnabled
                enabled: !kcm.liveSkyEnabled && kcm.theme !== "space"
                opacity: enabled ? 1.0 : 0.4
                onToggled: kcm.snowEnabled = checked
            }
            Controls.Switch {
                Kirigami.FormData.label: "Thunderstorms:"
                text: checked ? "Enabled" : "Disabled"
                checked: kcm.thunderstormsEnabled
                enabled: !kcm.liveSkyEnabled && kcm.theme !== "space"
                opacity: enabled ? 1.0 : 0.4
                onToggled: kcm.thunderstormsEnabled = checked
            }
            Controls.Switch {
                Kirigami.FormData.label: "Fog:"
                text: checked ? "Enabled" : "Disabled"
                checked: kcm.fogEnabled
                enabled: !kcm.liveSkyEnabled && kcm.theme !== "space"
                opacity: enabled ? 1.0 : 0.4
                onToggled: kcm.fogEnabled = checked
            }
            Controls.Switch {
                Kirigami.FormData.label: "Shooting stars (landscapes):"
                text: checked ? "Enabled" : "Disabled"
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
            title: "Live Sky"
            summary: kcm.liveSkyEnabled ? "On · " + (kcm.liveSkyLocation || "No location selected") + " · °" + kcm.liveSkyUnits.toUpperCase() : "Off"
            form.twinFormLayouts: [themeSection.form, clockSection.form, weatherSection.form, liveSkySection.form, agentsSection.form, bobosSection.form, lockSection.form]
            Controls.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: "Live Sky:"
                text: "Adapt landscape skies and weather to local conditions. In Space, Live Sky shows Earth’s day/night and the Moon phase, without weather effects or shooting stars. Manual weather effects are dimmed while Live Sky is enabled."
                wrapMode: Text.WordWrap
            }
            Controls.Switch {
                Kirigami.FormData.label: "Enable Live Sky:"
                text: checked ? "On" : "Off"
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
                text: "Typed searches are sent to Open-Meteo only while Live Sky is enabled. Choose a suggestion to set your location; Apply saves it. Offline search uses the bundled city catalog. No IP-based lookup is used."
                wrapMode: Text.WordWrap
            }
            Controls.ComboBox {
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: "Temperature units:"
                model: ["Celsius", "Fahrenheit"]
                currentIndex: kcm.liveSkyUnits === "f" ? 1 : 0
                enabled: kcm.liveSkyEnabled
                opacity: enabled ? 1.0 : 0.4
                onActivated: function(index) { kcm.liveSkyUnits = index === 1 ? "f" : "c" }
            }
            Controls.ComboBox {
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: "Weather refresh:"
                model: ["Every 15 minutes", "Every 30 minutes", "Every 60 minutes"]
                currentIndex: [15, 30, 60].indexOf(kcm.liveSkyInterval)
                enabled: kcm.liveSkyEnabled
                opacity: enabled ? 1.0 : 0.4
                onActivated: function(index) { kcm.liveSkyInterval = [15, 30, 60][index] }
            }
            Controls.Switch {
                Kirigami.FormData.label: "Current conditions:"
                text: checked ? "Show weather under the clock" : "Hide weather text"
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
            title: "AI Agents"
            summary: ["Always ask", "Always start screensaver", "Do not start while agents are running"][["ask", "start", "block"].indexOf(kcm.agentDetectionMode)]
            form.twinFormLayouts: [themeSection.form, clockSection.form, weatherSection.form, liveSkySection.form, agentsSection.form, bobosSection.form, lockSection.form]
            Controls.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: "AI Agent Detection:"
                text: "Choose what happens when an active terminal agent is detected. Manual launches always remain available."
                wrapMode: Text.WordWrap
            }
            Controls.ComboBox {
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: "When an agent is active:"
                model: ["Always ask", "Always start screensaver", "Don't start screensaver while agents are running"]
                currentIndex: ["ask", "start", "block"].indexOf(kcm.agentDetectionMode)
                onActivated: function(index) { kcm.agentDetectionMode = ["ask", "start", "block"][index] }
            }
            Controls.Button {
                objectName: "resetAgentChoiceButton"
                Kirigami.FormData.label: "Remembered choice:"
                text: "Reset to Always ask"
                enabled: kcm.agentDetectionMode !== "ask"
                onClicked: kcm.resetRememberedAgentChoice()
            }
        }
        CollapsibleSection {
            id: bobosSection
            settings: kcm
            sectionKey: "bobos"
            title: "BobOS"
            summary: !kcm.phoneEnabled ? "Phone off" : !kcm.bobosEnabled ? "Phone on · BobOS off" : "On · After " + kcm.bobosActivationDelay + " min"
            form.twinFormLayouts: [themeSection.form, clockSection.form, weatherSection.form, liveSkySection.form, agentsSection.form, bobosSection.form, lockSection.form]
            Controls.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
                Kirigami.FormData.label: "Bob's Phone & BobOS 2.0"
                text: "Bob's Phone contains a fictional mobile operating system. Its apps, messages, places, and games are animated drawings only."
                wrapMode: Text.WordWrap
            }
            Controls.Switch {
                Kirigami.FormData.label: "Enable Bob's Phone:"
                text: checked ? "Enabled" : "Disabled"
                checked: kcm.phoneEnabled
                onToggled: kcm.phoneEnabled = checked
            }
            Controls.Switch {
                Kirigami.FormData.label: "Enable BobOS:"
                text: checked ? "Enabled" : "Disabled"
                checked: kcm.bobosEnabled
                enabled: kcm.phoneEnabled
                opacity: enabled ? 1.0 : 0.4
                onToggled: kcm.bobosEnabled = checked
            }
            Controls.SpinBox {
                Kirigami.FormData.label: "BobOS Activation Delay:"
                from: 1
                to: 30
                stepSize: 1
                editable: true
                value: kcm.bobosActivationDelay
                enabled: kcm.phoneEnabled && kcm.bobosEnabled
                opacity: enabled ? 1.0 : 0.4
                onValueModified: kcm.bobosActivationDelay = value
                textFromValue: function(value, locale) { return value + (value === 1 ? " minute" : " minutes") }
                valueFromText: function(text, locale) {
                    var parsed = parseInt(text, 10)
                    return isNaN(parsed) ? 3 : Math.min(30, Math.max(1, parsed))
                }
            }
            Controls.Switch {
                Kirigami.FormData.label: "AI Wi-Fi animation:"
                text: checked ? "Shown before BobOS opens" : "Skipped"
                checked: kcm.showWifiAnimation
                enabled: kcm.phoneEnabled && kcm.bobosEnabled
                opacity: enabled ? 1.0 : 0.4
                onToggled: kcm.showWifiAnimation = checked
            }
            Controls.Button {
                objectName: "bobosPreviewButton"
                Kirigami.FormData.label: "BobOS preview:"
                text: "Preview full adventure"
                enabled: !kcm.previewRunning && kcm.phoneEnabled && kcm.bobosEnabled
                opacity: enabled ? 1.0 : 0.4
                onClicked: kcm.previewBobOS(kcm.showWifiAnimation)
            }
        }
        CollapsibleSection {
            id: lockSection
            settings: kcm
            sectionKey: "lock"
            title: "Lock"
            summary: kcm.passwordLock ? "Password after " + kcm.lockMinutes + " min" : "Screensaver password countdown off"
            form.twinFormLayouts: [themeSection.form, clockSection.form, weatherSection.form, liveSkySection.form, agentsSection.form, bobosSection.form, lockSection.form]
            Controls.Switch {
                id: passwordSwitch
                Kirigami.FormData.label: "Password unlock:"
                text: checked ? "On" : "Off"
                checked: kcm.passwordLock
                onToggled: kcm.passwordLock = checked
            }
            Controls.SpinBox {
                Kirigami.FormData.label: "Require password after:"
                from: 1
                to: 60
                stepSize: 1
                editable: true
                value: kcm.lockMinutes
                enabled: kcm.passwordLock
                opacity: enabled ? 1.0 : 0.4
                onValueModified: kcm.lockMinutes = value
                textFromValue: function(value, locale) { return value + (value === 1 ? " minute" : " minutes") }
                valueFromText: function(text, locale) {
                    var parsed = parseInt(text, 10)
                    return isNaN(parsed) ? 2 : Math.min(60, Math.max(1, parsed))
                }
            }
            Controls.CheckBox {
                Kirigami.FormData.label: "Show countdown:"
                text: "Display time until password is required"
                checked: kcm.showTimer
                enabled: kcm.passwordLock
                opacity: enabled ? 1.0 : 0.4
                onToggled: kcm.showTimer = checked
            }
            Controls.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
                text: "Countdown color preview (elapsed time)"
                Kirigami.FormData.label: "Color transition:"
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
                text: "The countdown begins when Bob appears. Its color smoothly changes green → yellow → orange → red as time runs out. KDE handles the actual password lock."
                wrapMode: Text.WordWrap
            }
            Controls.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 25
                Layout.maximumWidth: parent.width
                text: "For password protection, configure KDE Screen Locking to require the password immediately and disable any unlock grace period. Disabling this option does not disable KDE's separate automatic locking or suspend locks."
                wrapMode: Text.WordWrap
            }
        }
        Controls.Label {
            Layout.fillWidth: true
            text: "Press Apply to save your changes. Changes take effect the next time Bob starts."
            wrapMode: Text.WordWrap
        }
    }
}
