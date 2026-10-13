#include "screenbotkcm.h"
#include <KPluginFactory>
#include <QSettings>
#include <QStandardPaths>
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
                 || m_lockMinutes != m_savedLockMinutes || m_showTimer != m_savedShowTimer);
}

void ScreenBotKcm::load() {
    QSettings cfg(configFile(), QSettings::IniFormat);
    const QString theme = cfg.value(QStringLiteral("Screensaver/theme"), QStringLiteral("random")).toString();
    const QString validTheme = (theme == QLatin1String("space") || theme == QLatin1String("mountains") || theme == QLatin1String("random") || theme == QLatin1String("snow") || theme == QLatin1String("forest") || theme == QLatin1String("city")) ? theme : QStringLiteral("random");
    const bool lock = cfg.value(QStringLiteral("Screensaver/password_lock"), false).toBool();
    const int mins = qBound(1, cfg.value(QStringLiteral("Screensaver/lock_minutes"), 2).toInt(), 60);
    const bool show = cfg.value(QStringLiteral("Screensaver/show_timer"), false).toBool();
    if (m_theme != validTheme) { m_theme = validTheme; Q_EMIT themeChanged(); }
    if (m_passwordLock != lock) { m_passwordLock = lock; Q_EMIT passwordLockChanged(); }
    if (m_lockMinutes != mins) { m_lockMinutes = mins; Q_EMIT lockMinutesChanged(); }
    if (m_showTimer != show) { m_showTimer = show; Q_EMIT showTimerChanged(); }
    m_savedTheme = m_theme;
    m_savedPasswordLock = m_passwordLock;
    m_savedLockMinutes = m_lockMinutes;
    m_savedShowTimer = m_showTimer;
    setNeedsSave(false);
}

void ScreenBotKcm::save() {
    QSettings cfg(configFile(), QSettings::IniFormat);
    cfg.setValue(QStringLiteral("Screensaver/theme"), m_theme);
    cfg.setValue(QStringLiteral("Screensaver/password_lock"), m_passwordLock);
    cfg.setValue(QStringLiteral("Screensaver/lock_minutes"), m_lockMinutes);
    cfg.setValue(QStringLiteral("Screensaver/show_timer"), m_showTimer);
    cfg.sync();
    if (cfg.status() != QSettings::NoError) {
        qWarning("Could not write ScreenBot settings.");
        return;
    }
    m_savedTheme = m_theme;
    m_savedPasswordLock = m_passwordLock;
    m_savedLockMinutes = m_lockMinutes;
    m_savedShowTimer = m_showTimer;
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

#include "screenbotkcm.moc"
