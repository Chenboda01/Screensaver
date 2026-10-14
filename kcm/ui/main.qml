import QtQuick
import QtQuick.Controls as Controls
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCMUtils

KCMUtils.SimpleKCM {
    Kirigami.FormLayout {
        anchors.fill: parent
        Controls.Label {
            Kirigami.FormData.label: "ScreenBot screensaver"
            text: "Choose how Bob appears and when KDE locks your screen."
            wrapMode: Text.WordWrap
        }
        Controls.ComboBox {
            Kirigami.FormData.label: "Theme:"
            model: ["Random", "Space", "Mountains", "Snow", "Forest", "Futuristic City"]
            currentIndex: Math.max(0, ["random", "space", "mountains", "snow", "forest", "city"].indexOf(kcm.theme))
            onActivated: function(index) { kcm.theme = ["random", "space", "mountains", "snow", "forest", "city"][index] }
        }
        Controls.Switch {
            Kirigami.FormData.label: "Clock:"
            text: checked ? "Visible" : "Hidden"
            checked: kcm.clockVisible
            onToggled: kcm.clockVisible = checked
        }
        Controls.ComboBox {
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
        Controls.Label {
            Kirigami.FormData.label: "Animated weather:"
            text: "Choose any effects to layer over the scene. Shooting stars appear in Space."
            wrapMode: Text.WordWrap
        }
        Controls.Switch {
            Kirigami.FormData.label: "Rain:"
            text: checked ? "Enabled" : "Disabled"
            checked: kcm.rainEnabled
            onToggled: kcm.rainEnabled = checked
        }
        Controls.Switch {
            Kirigami.FormData.label: "Snowfall:"
            text: checked ? "Enabled" : "Disabled"
            checked: kcm.snowEnabled
            onToggled: kcm.snowEnabled = checked
        }
        Controls.Switch {
            Kirigami.FormData.label: "Thunderstorms:"
            text: checked ? "Enabled" : "Disabled"
            checked: kcm.thunderstormsEnabled
            onToggled: kcm.thunderstormsEnabled = checked
        }
        Controls.Switch {
            Kirigami.FormData.label: "Fog:"
            text: checked ? "Enabled" : "Disabled"
            checked: kcm.fogEnabled
            onToggled: kcm.fogEnabled = checked
        }
        Controls.Switch {
            Kirigami.FormData.label: "Shooting stars:"
            text: checked ? "Enabled" : "Disabled"
            checked: kcm.shootingStarsEnabled
            onToggled: kcm.shootingStarsEnabled = checked
        }
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
            text: "The countdown begins when Bob appears. Its color smoothly changes green → yellow → orange → red as time runs out. KDE handles the actual password lock."
            wrapMode: Text.WordWrap
        }
        Controls.Label {
            text: "For password protection, configure KDE Screen Locking to require the password immediately and disable any unlock grace period. Disabling this option does not disable KDE's separate automatic locking or suspend locks."
            wrapMode: Text.WordWrap
        }
        Controls.Label {
            text: "Press Apply to save your changes. Changes take effect the next time Bob starts."
            wrapMode: Text.WordWrap
        }
    }
}
