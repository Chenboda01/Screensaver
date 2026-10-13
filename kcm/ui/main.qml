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
