#pragma once
#include <KQuickConfigModule>
#include <QString>

class ScreenBotKcm : public KQuickConfigModule {
    Q_OBJECT
    Q_PROPERTY(QString theme READ theme WRITE setTheme NOTIFY themeChanged)
    Q_PROPERTY(bool passwordLock READ passwordLock WRITE setPasswordLock NOTIFY passwordLockChanged)
    Q_PROPERTY(int lockMinutes READ lockMinutes WRITE setLockMinutes NOTIFY lockMinutesChanged)
    Q_PROPERTY(bool showTimer READ showTimer WRITE setShowTimer NOTIFY showTimerChanged)
public:
    ScreenBotKcm(QObject *parent, const KPluginMetaData &data);
    QString theme() const { return m_theme; }
    bool passwordLock() const { return m_passwordLock; }
    int lockMinutes() const { return m_lockMinutes; }
    bool showTimer() const { return m_showTimer; }
    void setTheme(const QString &value);
    void setPasswordLock(bool value);
    void setLockMinutes(int value);
    void setShowTimer(bool value);
    void load() override;
    void save() override;
Q_SIGNALS:
    void themeChanged();
    void passwordLockChanged();
    void lockMinutesChanged();
    void showTimerChanged();
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
};
