#pragma once
#include <KQuickConfigModule>
#include <QString>

class ScreenBotKcm : public KQuickConfigModule {
    Q_OBJECT
    Q_PROPERTY(QString theme READ theme WRITE setTheme NOTIFY themeChanged)
    Q_PROPERTY(bool passwordLock READ passwordLock WRITE setPasswordLock NOTIFY passwordLockChanged)
    Q_PROPERTY(int lockMinutes READ lockMinutes WRITE setLockMinutes NOTIFY lockMinutesChanged)
    Q_PROPERTY(bool showTimer READ showTimer WRITE setShowTimer NOTIFY showTimerChanged)
    Q_PROPERTY(bool clockVisible READ clockVisible WRITE setClockVisible NOTIFY clockVisibleChanged)
    Q_PROPERTY(QString clockFormat READ clockFormat WRITE setClockFormat NOTIFY clockFormatChanged)
    Q_PROPERTY(bool showDate READ showDate WRITE setShowDate NOTIFY showDateChanged)
    Q_PROPERTY(QString clockPosition READ clockPosition WRITE setClockPosition NOTIFY clockPositionChanged)
    Q_PROPERTY(int clockFontSize READ clockFontSize WRITE setClockFontSize NOTIFY clockFontSizeChanged)
    Q_PROPERTY(bool rainEnabled READ rainEnabled WRITE setRainEnabled NOTIFY rainEnabledChanged)
    Q_PROPERTY(bool snowEnabled READ snowEnabled WRITE setSnowEnabled NOTIFY snowEnabledChanged)
    Q_PROPERTY(bool thunderstormsEnabled READ thunderstormsEnabled WRITE setThunderstormsEnabled NOTIFY thunderstormsEnabledChanged)
    Q_PROPERTY(bool fogEnabled READ fogEnabled WRITE setFogEnabled NOTIFY fogEnabledChanged)
    Q_PROPERTY(bool shootingStarsEnabled READ shootingStarsEnabled WRITE setShootingStarsEnabled NOTIFY shootingStarsEnabledChanged)
    Q_PROPERTY(QString agentDetectionMode READ agentDetectionMode WRITE setAgentDetectionMode NOTIFY agentDetectionModeChanged)
public:
    ScreenBotKcm(QObject *parent, const KPluginMetaData &data);
    QString theme() const { return m_theme; }
    bool passwordLock() const { return m_passwordLock; }
    int lockMinutes() const { return m_lockMinutes; }
    bool showTimer() const { return m_showTimer; }
    bool clockVisible() const { return m_clockVisible; }
    QString clockFormat() const { return m_clockFormat; }
    bool showDate() const { return m_showDate; }
    QString clockPosition() const { return m_clockPosition; }
    int clockFontSize() const { return m_clockFontSize; }
    bool rainEnabled() const { return m_rainEnabled; }
    bool snowEnabled() const { return m_snowEnabled; }
    bool thunderstormsEnabled() const { return m_thunderstormsEnabled; }
    bool fogEnabled() const { return m_fogEnabled; }
    bool shootingStarsEnabled() const { return m_shootingStarsEnabled; }
    QString agentDetectionMode() const { return m_agentDetectionMode; }
    void setTheme(const QString &value);
    void setPasswordLock(bool value);
    void setLockMinutes(int value);
    void setShowTimer(bool value);
    void setClockVisible(bool value);
    void setClockFormat(const QString &value);
    void setShowDate(bool value);
    void setClockPosition(const QString &value);
    void setClockFontSize(int value);
    void setRainEnabled(bool value);
    void setSnowEnabled(bool value);
    void setThunderstormsEnabled(bool value);
    void setFogEnabled(bool value);
    void setShootingStarsEnabled(bool value);
    void setAgentDetectionMode(const QString &value);
    Q_INVOKABLE void resetRememberedAgentChoice();
    void load() override;
    void save() override;
Q_SIGNALS:
    void themeChanged();
    void passwordLockChanged();
    void lockMinutesChanged();
    void showTimerChanged();
    void clockVisibleChanged();
    void clockFormatChanged();
    void showDateChanged();
    void clockPositionChanged();
    void clockFontSizeChanged();
    void rainEnabledChanged();
    void snowEnabledChanged();
    void thunderstormsEnabledChanged();
    void fogEnabledChanged();
    void shootingStarsEnabledChanged();
    void agentDetectionModeChanged();
private:
    void checkModified();
    QString m_theme = QStringLiteral("random");
    bool m_passwordLock = false;
    int m_lockMinutes = 2;
    bool m_showTimer = false;
    QString m_savedTheme = QStringLiteral("random");
    bool m_savedPasswordLock = false;
    int m_savedLockMinutes = 2;
    bool m_savedShowTimer = false;
    bool m_clockVisible = true;
    QString m_clockFormat = QStringLiteral("12h");
    bool m_showDate = false;
    QString m_clockPosition = QStringLiteral("top-center");
    int m_clockFontSize = 48;
    bool m_rainEnabled = false;
    bool m_snowEnabled = false;
    bool m_thunderstormsEnabled = false;
    bool m_fogEnabled = false;
    bool m_shootingStarsEnabled = false;
    QString m_agentDetectionMode = QStringLiteral("ask");
    bool m_savedClockVisible = true;
    QString m_savedClockFormat = QStringLiteral("12h");
    bool m_savedShowDate = false;
    QString m_savedClockPosition = QStringLiteral("top-center");
    int m_savedClockFontSize = 48;
    bool m_savedRainEnabled = false;
    bool m_savedSnowEnabled = false;
    bool m_savedThunderstormsEnabled = false;
    bool m_savedFogEnabled = false;
    bool m_savedShootingStarsEnabled = false;
    QString m_savedAgentDetectionMode = QStringLiteral("ask");
};
