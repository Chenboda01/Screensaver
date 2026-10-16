#include "screenbotkcm.h"
#include <KPluginFactory>
#include <QSettings>
#include <QProcess>
#include <QDir>
#include <QStandardPaths>
#include <QStringList>
#include <QtGlobal>

K_PLUGIN_CLASS_WITH_JSON(ScreenBotKcm, "kcm_screenbot_screensaver.json")

static QString configFile() {
    return QStandardPaths::writableLocation(QStandardPaths::ConfigLocation)
           + QStringLiteral("/screenbot-screensaver.ini");
}

ScreenBotKcm::ScreenBotKcm(QObject *parent, const KPluginMetaData &data)
    : KQuickConfigModule(parent, data) {
    setButtons(Apply);
    setSupportsInstantApply(false);
    load();
}

void ScreenBotKcm::checkModified() {
    setNeedsSave(m_theme != m_savedTheme || m_passwordLock != m_savedPasswordLock
                 || m_lockMinutes != m_savedLockMinutes || m_showTimer != m_savedShowTimer
                 || m_clockVisible != m_savedClockVisible || m_clockFormat != m_savedClockFormat
                 || m_showDate != m_savedShowDate || m_clockPosition != m_savedClockPosition
                 || m_clockFontSize != m_savedClockFontSize || m_rainEnabled != m_savedRainEnabled
                 || m_snowEnabled != m_savedSnowEnabled
                 || m_thunderstormsEnabled != m_savedThunderstormsEnabled
                 || m_fogEnabled != m_savedFogEnabled
                 || m_shootingStarsEnabled != m_savedShootingStarsEnabled
                 || m_agentDetectionMode != m_savedAgentDetectionMode
                 || m_phoneEnabled != m_savedPhoneEnabled
                 || m_bobosEnabled != m_savedBobosEnabled
                 || m_bobosActivationDelay != m_savedBobosActivationDelay
                 || m_showWifiAnimation != m_savedShowWifiAnimation);
}

void ScreenBotKcm::load() {
    QSettings cfg(configFile(), QSettings::IniFormat);
    const QString theme = cfg.value(QStringLiteral("Screensaver/theme"), QStringLiteral("random")).toString();
    const QString validTheme = (theme == QLatin1String("space") || theme == QLatin1String("mountains") || theme == QLatin1String("random") || theme == QLatin1String("snow") || theme == QLatin1String("forest") || theme == QLatin1String("city")) ? theme : QStringLiteral("random");
    const bool lock = cfg.value(QStringLiteral("Screensaver/password_lock"), false).toBool();
    const int mins = qBound(1, cfg.value(QStringLiteral("Screensaver/lock_minutes"), 2).toInt(), 60);
    const bool show = cfg.value(QStringLiteral("Screensaver/show_timer"), false).toBool();
    const bool clockVisible = cfg.value(QStringLiteral("Screensaver/show_clock"), true).toBool();
    const QString clockFormat = cfg.value(QStringLiteral("Screensaver/clock_format"), QStringLiteral("12h")).toString();
    const QString validClockFormat = clockFormat == QLatin1String("24h") ? clockFormat : QStringLiteral("12h");
    const bool showDate = cfg.value(QStringLiteral("Screensaver/show_date"), false).toBool();
    const QStringList clockPositions = {
        QStringLiteral("top-left"), QStringLiteral("top-center"), QStringLiteral("top-right"),
        QStringLiteral("center-left"), QStringLiteral("center-center"), QStringLiteral("center-right"),
        QStringLiteral("bottom-left"), QStringLiteral("bottom-center"), QStringLiteral("bottom-right")
    };
    const QString clockPosition = cfg.value(QStringLiteral("Screensaver/clock_position"), QStringLiteral("top-center")).toString();
    const QString validClockPosition = clockPositions.contains(clockPosition) ? clockPosition : QStringLiteral("top-center");
    const int clockFontSize = qBound(16, cfg.value(QStringLiteral("Screensaver/clock_font_size"), 48).toInt(), 72);
    const bool rain = cfg.value(QStringLiteral("Screensaver/rain_enabled"), false).toBool();
    const bool snow = cfg.value(QStringLiteral("Screensaver/snow_enabled"), false).toBool();
    const bool thunderstorms = cfg.value(QStringLiteral("Screensaver/thunderstorms_enabled"), false).toBool();
    const bool fog = cfg.value(QStringLiteral("Screensaver/fog_enabled"), false).toBool();
    const bool shootingStars = cfg.value(QStringLiteral("Screensaver/shooting_stars_enabled"), false).toBool();
    const QString requestedAgentMode = cfg.value(QStringLiteral("Screensaver/agent_detection_mode"), QStringLiteral("ask")).toString();
    const QString agentMode = requestedAgentMode == QLatin1String("start") || requestedAgentMode == QLatin1String("block")
        ? requestedAgentMode : QStringLiteral("ask");
    const bool phone = cfg.value(QStringLiteral("Screensaver/bob_phone_enabled"),
                                  cfg.value(QStringLiteral("Screensaver/ai_backpack_enabled"), true)).toBool();
    const bool bobos = cfg.value(QStringLiteral("Screensaver/bobos_enabled"), true).toBool();
    const int bobosDelay = qBound(1, cfg.value(QStringLiteral("Screensaver/bobos_activation_delay"), 3).toInt(), 30);
    const bool wifiAnimation = cfg.value(QStringLiteral("Screensaver/show_wifi_animation"), true).toBool();
    if (m_theme != validTheme) { m_theme = validTheme; Q_EMIT themeChanged(); }
    if (m_passwordLock != lock) { m_passwordLock = lock; Q_EMIT passwordLockChanged(); }
    if (m_lockMinutes != mins) { m_lockMinutes = mins; Q_EMIT lockMinutesChanged(); }
    if (m_showTimer != show) { m_showTimer = show; Q_EMIT showTimerChanged(); }
    if (m_clockVisible != clockVisible) { m_clockVisible = clockVisible; Q_EMIT clockVisibleChanged(); }
    if (m_clockFormat != validClockFormat) { m_clockFormat = validClockFormat; Q_EMIT clockFormatChanged(); }
    if (m_showDate != showDate) { m_showDate = showDate; Q_EMIT showDateChanged(); }
    if (m_clockPosition != validClockPosition) { m_clockPosition = validClockPosition; Q_EMIT clockPositionChanged(); }
    if (m_clockFontSize != clockFontSize) { m_clockFontSize = clockFontSize; Q_EMIT clockFontSizeChanged(); }
    if (m_rainEnabled != rain) { m_rainEnabled = rain; Q_EMIT rainEnabledChanged(); }
    if (m_snowEnabled != snow) { m_snowEnabled = snow; Q_EMIT snowEnabledChanged(); }
    if (m_thunderstormsEnabled != thunderstorms) { m_thunderstormsEnabled = thunderstorms; Q_EMIT thunderstormsEnabledChanged(); }
    if (m_fogEnabled != fog) { m_fogEnabled = fog; Q_EMIT fogEnabledChanged(); }
    if (m_shootingStarsEnabled != shootingStars) { m_shootingStarsEnabled = shootingStars; Q_EMIT shootingStarsEnabledChanged(); }
    if (m_agentDetectionMode != agentMode) { m_agentDetectionMode = agentMode; Q_EMIT agentDetectionModeChanged(); }
    if (m_phoneEnabled != phone) { m_phoneEnabled = phone; Q_EMIT phoneEnabledChanged(); }
    if (m_bobosEnabled != bobos) { m_bobosEnabled = bobos; Q_EMIT bobosEnabledChanged(); }
    if (m_bobosActivationDelay != bobosDelay) { m_bobosActivationDelay = bobosDelay; Q_EMIT bobosActivationDelayChanged(); }
    if (m_showWifiAnimation != wifiAnimation) { m_showWifiAnimation = wifiAnimation; Q_EMIT showWifiAnimationChanged(); }
    m_savedTheme = m_theme;
    m_savedPasswordLock = m_passwordLock;
    m_savedLockMinutes = m_lockMinutes;
    m_savedShowTimer = m_showTimer;
    m_savedClockVisible = m_clockVisible;
    m_savedClockFormat = m_clockFormat;
    m_savedShowDate = m_showDate;
    m_savedClockPosition = m_clockPosition;
    m_savedClockFontSize = m_clockFontSize;
    m_savedRainEnabled = m_rainEnabled;
    m_savedSnowEnabled = m_snowEnabled;
    m_savedThunderstormsEnabled = m_thunderstormsEnabled;
    m_savedFogEnabled = m_fogEnabled;
    m_savedShootingStarsEnabled = m_shootingStarsEnabled;
    m_savedAgentDetectionMode = m_agentDetectionMode;
    m_savedPhoneEnabled = m_phoneEnabled;
    m_savedBobosEnabled = m_bobosEnabled;
    m_savedBobosActivationDelay = m_bobosActivationDelay;
    m_savedShowWifiAnimation = m_showWifiAnimation;
    setNeedsSave(false);
}

void ScreenBotKcm::save() {
    QSettings cfg(configFile(), QSettings::IniFormat);
    cfg.setValue(QStringLiteral("Screensaver/theme"), m_theme);
    cfg.setValue(QStringLiteral("Screensaver/password_lock"), m_passwordLock);
    cfg.setValue(QStringLiteral("Screensaver/lock_minutes"), m_lockMinutes);
    cfg.setValue(QStringLiteral("Screensaver/show_timer"), m_showTimer);
    cfg.setValue(QStringLiteral("Screensaver/show_clock"), m_clockVisible);
    cfg.setValue(QStringLiteral("Screensaver/clock_format"), m_clockFormat);
    cfg.setValue(QStringLiteral("Screensaver/show_date"), m_showDate);
    cfg.setValue(QStringLiteral("Screensaver/clock_position"), m_clockPosition);
    cfg.setValue(QStringLiteral("Screensaver/clock_font_size"), m_clockFontSize);
    cfg.setValue(QStringLiteral("Screensaver/rain_enabled"), m_rainEnabled);
    cfg.setValue(QStringLiteral("Screensaver/snow_enabled"), m_snowEnabled);
    cfg.setValue(QStringLiteral("Screensaver/thunderstorms_enabled"), m_thunderstormsEnabled);
    cfg.setValue(QStringLiteral("Screensaver/fog_enabled"), m_fogEnabled);
    cfg.setValue(QStringLiteral("Screensaver/shooting_stars_enabled"), m_shootingStarsEnabled);
    cfg.setValue(QStringLiteral("Screensaver/agent_detection_mode"), m_agentDetectionMode);
    cfg.setValue(QStringLiteral("Screensaver/bob_phone_enabled"), m_phoneEnabled);
    cfg.setValue(QStringLiteral("Screensaver/bobos_enabled"), m_bobosEnabled);
    cfg.setValue(QStringLiteral("Screensaver/bobos_activation_delay"), m_bobosActivationDelay);
    cfg.setValue(QStringLiteral("Screensaver/show_wifi_animation"), m_showWifiAnimation);
    cfg.sync();
    if (cfg.status() != QSettings::NoError) {
        qWarning("Could not write ScreenBot settings.");
        return;
    }
    m_savedTheme = m_theme;
    m_savedPasswordLock = m_passwordLock;
    m_savedLockMinutes = m_lockMinutes;
    m_savedShowTimer = m_showTimer;
    m_savedClockVisible = m_clockVisible;
    m_savedClockFormat = m_clockFormat;
    m_savedShowDate = m_showDate;
    m_savedClockPosition = m_clockPosition;
    m_savedClockFontSize = m_clockFontSize;
    m_savedRainEnabled = m_rainEnabled;
    m_savedSnowEnabled = m_snowEnabled;
    m_savedThunderstormsEnabled = m_thunderstormsEnabled;
    m_savedFogEnabled = m_fogEnabled;
    m_savedShootingStarsEnabled = m_shootingStarsEnabled;
    m_savedAgentDetectionMode = m_agentDetectionMode;
    m_savedPhoneEnabled = m_phoneEnabled;
    m_savedBobosEnabled = m_bobosEnabled;
    m_savedBobosActivationDelay = m_bobosActivationDelay;
    m_savedShowWifiAnimation = m_showWifiAnimation;
    setNeedsSave(false);
}

void ScreenBotKcm::setTheme(const QString &value) {
    if (value != QLatin1String("space") && value != QLatin1String("mountains") && value != QLatin1String("random") && value != QLatin1String("snow") && value != QLatin1String("forest") && value != QLatin1String("city")) return;
    if (value == m_theme) return;
    m_theme = value;
    Q_EMIT themeChanged();
    checkModified();
}

void ScreenBotKcm::setPasswordLock(bool value) {
    if (value == m_passwordLock) return;
    m_passwordLock = value;
    Q_EMIT passwordLockChanged();
    checkModified();
}

void ScreenBotKcm::setLockMinutes(int value) {
    value = qBound(1, value, 60);
    if (value == m_lockMinutes) return;
    m_lockMinutes = value;
    Q_EMIT lockMinutesChanged();
    checkModified();
}

void ScreenBotKcm::setShowTimer(bool value) {
    if (value == m_showTimer) return;
    m_showTimer = value;
    Q_EMIT showTimerChanged();
    checkModified();
}

void ScreenBotKcm::setClockVisible(bool value) {
    if (value == m_clockVisible) return;
    m_clockVisible = value;
    Q_EMIT clockVisibleChanged();
    checkModified();
}

void ScreenBotKcm::setClockFormat(const QString &value) {
    if (value != QLatin1String("12h") && value != QLatin1String("24h")) return;
    if (value == m_clockFormat) return;
    m_clockFormat = value;
    Q_EMIT clockFormatChanged();
    checkModified();
}

void ScreenBotKcm::setShowDate(bool value) {
    if (value == m_showDate) return;
    m_showDate = value;
    Q_EMIT showDateChanged();
    checkModified();
}

void ScreenBotKcm::setClockPosition(const QString &value) {
    static const QStringList positions = {
        QStringLiteral("top-left"), QStringLiteral("top-center"), QStringLiteral("top-right"),
        QStringLiteral("center-left"), QStringLiteral("center-center"), QStringLiteral("center-right"),
        QStringLiteral("bottom-left"), QStringLiteral("bottom-center"), QStringLiteral("bottom-right")
    };
    if (!positions.contains(value) || value == m_clockPosition) return;
    m_clockPosition = value;
    Q_EMIT clockPositionChanged();
    checkModified();
}

void ScreenBotKcm::setClockFontSize(int value) {
    value = qBound(16, value, 72);
    if (value == m_clockFontSize) return;
    m_clockFontSize = value;
    Q_EMIT clockFontSizeChanged();
    checkModified();
}

void ScreenBotKcm::setRainEnabled(bool value) {
    if (value == m_rainEnabled) return;
    m_rainEnabled = value;
    Q_EMIT rainEnabledChanged();
    checkModified();
}

void ScreenBotKcm::setSnowEnabled(bool value) {
    if (value == m_snowEnabled) return;
    m_snowEnabled = value;
    Q_EMIT snowEnabledChanged();
    checkModified();
}

void ScreenBotKcm::setThunderstormsEnabled(bool value) {
    if (value == m_thunderstormsEnabled) return;
    m_thunderstormsEnabled = value;
    Q_EMIT thunderstormsEnabledChanged();
    checkModified();
}

void ScreenBotKcm::setFogEnabled(bool value) {
    if (value == m_fogEnabled) return;
    m_fogEnabled = value;
    Q_EMIT fogEnabledChanged();
    checkModified();
}

void ScreenBotKcm::setShootingStarsEnabled(bool value) {
    if (value == m_shootingStarsEnabled) return;
    m_shootingStarsEnabled = value;
    Q_EMIT shootingStarsEnabledChanged();
    checkModified();
}

void ScreenBotKcm::setAgentDetectionMode(const QString &value) {
    if (value != QLatin1String("ask") && value != QLatin1String("start") && value != QLatin1String("block")) return;
    if (value == m_agentDetectionMode) return;
    m_agentDetectionMode = value;
    Q_EMIT agentDetectionModeChanged();
    checkModified();
}

void ScreenBotKcm::resetRememberedAgentChoice() {
    setAgentDetectionMode(QStringLiteral("ask"));
}

void ScreenBotKcm::setPhoneEnabled(bool value) {
    if (value == m_phoneEnabled) return;
    m_phoneEnabled = value;
    Q_EMIT phoneEnabledChanged();
    checkModified();
}

void ScreenBotKcm::setBobosEnabled(bool value) {
    if (value == m_bobosEnabled) return;
    m_bobosEnabled = value;
    Q_EMIT bobosEnabledChanged();
    checkModified();
}

void ScreenBotKcm::setBobosActivationDelay(int value) {
    value = qBound(1, value, 30);
    if (value == m_bobosActivationDelay) return;
    m_bobosActivationDelay = value;
    Q_EMIT bobosActivationDelayChanged();
    checkModified();
}

void ScreenBotKcm::setShowWifiAnimation(bool value) {
    if (value == m_showWifiAnimation) return;
    m_showWifiAnimation = value;
    Q_EMIT showWifiAnimationChanged();
    checkModified();
}

void ScreenBotKcm::previewBobOS(bool showWifiAnimation) {
    const QString script = QDir::homePath() + QStringLiteral("/ScreenBot/screensaver/screensaver.py");
    QStringList arguments{script, QStringLiteral("--preview-bobos")};
    arguments.append(showWifiAnimation ? QStringLiteral("--wifi-animation")
                                      : QStringLiteral("--no-wifi-animation"));
    if (!QProcess::startDetached(QStringLiteral("/usr/bin/python"), arguments,
                                 QDir::homePath() + QStringLiteral("/ScreenBot/screensaver"))) {
        qWarning("Could not start the BobOS preview.");
    }
}

#include "screenbotkcm.moc"
