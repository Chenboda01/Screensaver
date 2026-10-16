#pragma once
#include <KQuickConfigModule>
#include <QString>
#include "locationsearch.h"

class QProcess;
class QQuickItem;
class QSettings;

class ScreenBotKcm : public KQuickConfigModule {
    Q_OBJECT
    Q_PROPERTY(QStringList modifiedSections READ modifiedSections NOTIFY modifiedSectionsChanged)
    Q_PROPERTY(bool previewRunning READ previewRunning NOTIFY previewRunningChanged)
    Q_PROPERTY(QString previewError READ previewError NOTIFY previewErrorChanged)
    Q_PROPERTY(QString theme READ theme WRITE setTheme NOTIFY themeChanged)
    Q_PROPERTY(bool passwordLock READ passwordLock WRITE setPasswordLock NOTIFY passwordLockChanged)
    Q_PROPERTY(int lockMinutes READ lockMinutes WRITE setLockMinutes NOTIFY lockMinutesChanged)
    Q_PROPERTY(bool showTimer READ showTimer WRITE setShowTimer NOTIFY showTimerChanged)
    Q_PROPERTY(bool nowPlayingEnabled READ nowPlayingEnabled WRITE setNowPlayingEnabled NOTIFY nowPlayingEnabledChanged)
    Q_PROPERTY(bool factsEnabled READ factsEnabled WRITE setFactsEnabled NOTIFY factsEnabledChanged)
    Q_PROPERTY(int factsIntervalMinutes READ factsIntervalMinutes WRITE setFactsIntervalMinutes NOTIFY factsIntervalMinutesChanged)
    Q_PROPERTY(QString factsContentMode READ factsContentMode WRITE setFactsContentMode NOTIFY factsContentModeChanged)
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
    Q_PROPERTY(bool bobWeatherEnabled READ bobWeatherEnabled WRITE setBobWeatherEnabled NOTIFY bobWeatherEnabledChanged)
    Q_PROPERTY(QString bobName READ bobName WRITE setBobName NOTIFY bobNameChanged)
    Q_PROPERTY(QString bobColorPreset READ bobColorPreset WRITE setBobColorPreset NOTIFY bobColorPresetChanged)
    Q_PROPERTY(QString bobCustomColor READ bobCustomColor WRITE setBobCustomColor NOTIFY bobCustomColorChanged)
    Q_PROPERTY(QString bobAccessory READ bobAccessory WRITE setBobAccessory NOTIFY bobAccessoryChanged)
    Q_PROPERTY(bool liveSkyEnabled READ liveSkyEnabled WRITE setLiveSkyEnabled NOTIFY liveSkyEnabledChanged)
    Q_PROPERTY(QStringList liveSkyLocations READ liveSkyLocations CONSTANT)
    Q_PROPERTY(QString liveSkyLocation READ liveSkyLocation WRITE setLiveSkyLocation NOTIFY liveSkyLocationChanged)
    Q_PROPERTY(LocationSearch *locationSearch READ locationSearch CONSTANT)
    Q_PROPERTY(QVariantMap liveSkyPlace READ liveSkyPlace NOTIFY liveSkyLocationChanged)
    Q_PROPERTY(QString liveSkyUnits READ liveSkyUnits WRITE setLiveSkyUnits NOTIFY liveSkyUnitsChanged)
    Q_PROPERTY(int liveSkyInterval READ liveSkyInterval WRITE setLiveSkyInterval NOTIFY liveSkyIntervalChanged)
    Q_PROPERTY(bool liveSkyConditions READ liveSkyConditions WRITE setLiveSkyConditions NOTIFY liveSkyConditionsChanged)
    Q_PROPERTY(QString agentDetectionMode READ agentDetectionMode WRITE setAgentDetectionMode NOTIFY agentDetectionModeChanged)
    Q_PROPERTY(bool agentStatusEnabled READ agentStatusEnabled WRITE setAgentStatusEnabled NOTIFY agentStatusEnabledChanged)
    Q_PROPERTY(int agentPromptTimeout READ agentPromptTimeout WRITE setAgentPromptTimeout NOTIFY agentPromptTimeoutChanged)
    Q_PROPERTY(QString agentPromptTimeoutAction READ agentPromptTimeoutAction WRITE setAgentPromptTimeoutAction NOTIFY agentPromptTimeoutActionChanged)
    Q_PROPERTY(bool phoneEnabled READ phoneEnabled WRITE setPhoneEnabled NOTIFY phoneEnabledChanged)
    Q_PROPERTY(bool bobosEnabled READ bobosEnabled WRITE setBobosEnabled NOTIFY bobosEnabledChanged)
    Q_PROPERTY(int bobosActivationDelay READ bobosActivationDelay WRITE setBobosActivationDelay NOTIFY bobosActivationDelayChanged)
    Q_PROPERTY(bool showWifiAnimation READ showWifiAnimation WRITE setShowWifiAnimation NOTIFY showWifiAnimationChanged)
    Q_PROPERTY(QString performanceMode READ performanceMode WRITE setPerformanceMode NOTIFY performanceModeChanged)
    Q_PROPERTY(bool reduceMotion READ reduceMotion WRITE setReduceMotion NOTIFY reduceMotionChanged)
    Q_PROPERTY(QString burnInProtection READ burnInProtection WRITE setBurnInProtection NOTIFY burnInProtectionChanged)
public:
    ScreenBotKcm(QObject *parent, const KPluginMetaData &data);
    QStringList modifiedSections() const;
    Q_INVOKABLE bool sectionExpanded(const QString &section) const;
    Q_INVOKABLE void setSectionExpanded(const QString &section, bool expanded);
    bool previewRunning() const { return m_previewProcess != nullptr; }
    QString previewError() const { return m_previewError; }
    Q_INVOKABLE void previewTheme(QQuickItem *source = nullptr);
    QString theme() const { return m_theme; }
    bool passwordLock() const { return m_passwordLock; }
    int lockMinutes() const { return m_lockMinutes; }
    bool showTimer() const { return m_showTimer; }
    bool nowPlayingEnabled() const { return m_nowPlayingEnabled; }
    bool factsEnabled() const { return m_factsEnabled; }
    int factsIntervalMinutes() const { return m_factsIntervalMinutes; }
    QString factsContentMode() const { return m_factsContentMode; }
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
    bool bobWeatherEnabled() const { return m_bobWeatherEnabled; }
    QString bobName() const { return m_bobName; }
    QString bobColorPreset() const { return m_bobColorPreset; }
    QString bobCustomColor() const { return m_bobCustomColor; }
    QString bobAccessory() const { return m_bobAccessory; }
    bool liveSkyEnabled() const { return m_liveSkyEnabled; }
    QStringList liveSkyLocations() const { return m_liveSkyLocations; }
    QString liveSkyLocation() const { return m_liveSkyLocation; }
    LocationSearch *locationSearch() { return &m_locationSearch; }
    QVariantMap liveSkyPlace() const { return m_liveSkyPlace; }
    Q_INVOKABLE void selectLiveSkyPlace(int index);
    QString liveSkyUnits() const { return m_liveSkyUnits; }
    int liveSkyInterval() const { return m_liveSkyInterval; }
    bool liveSkyConditions() const { return m_liveSkyConditions; }
    QString agentDetectionMode() const { return m_agentDetectionMode; }
    bool agentStatusEnabled() const { return m_agentStatusEnabled; }
    int agentPromptTimeout() const { return m_agentPromptTimeout; }
    QString agentPromptTimeoutAction() const { return m_agentPromptTimeoutAction; }
    bool phoneEnabled() const { return m_phoneEnabled; }
    bool bobosEnabled() const { return m_bobosEnabled; }
    int bobosActivationDelay() const { return m_bobosActivationDelay; }
    bool showWifiAnimation() const { return m_showWifiAnimation; }
    QString performanceMode() const { return m_performanceMode; }
    bool reduceMotion() const { return m_reduceMotion; }
    QString burnInProtection() const { return m_burnInProtection; }
    void setTheme(const QString &value);
    void setPasswordLock(bool value);
    void setLockMinutes(int value);
    void setShowTimer(bool value);
    void setClockVisible(bool value);
    void setNowPlayingEnabled(bool value);
    void setFactsEnabled(bool value);
    void setFactsIntervalMinutes(int value);
    void setFactsContentMode(const QString &value);
    void setClockFormat(const QString &value);
    void setShowDate(bool value);
    void setClockPosition(const QString &value);
    void setClockFontSize(int value);
    void setRainEnabled(bool value);
    void setSnowEnabled(bool value);
    void setThunderstormsEnabled(bool value);
    void setFogEnabled(bool value);
    void setShootingStarsEnabled(bool value);
    void setBobWeatherEnabled(bool value);
    void setBobName(const QString &value);
    void setBobColorPreset(const QString &value);
    void setBobCustomColor(const QString &value);
    void setBobAccessory(const QString &value);
    void setLiveSkyEnabled(bool value);
    void setLiveSkyLocation(const QString &value);
    void setLiveSkyUnits(const QString &value);
    void setLiveSkyInterval(int value);
    void setLiveSkyConditions(bool value);
    void setAgentDetectionMode(const QString &value);
    void setAgentStatusEnabled(bool value);
    void setAgentPromptTimeout(int value);
    void setAgentPromptTimeoutAction(const QString &value);
    Q_INVOKABLE void resetRememberedAgentChoice();
    Q_INVOKABLE void previewBobOS(bool showWifiAnimation);
    void setPhoneEnabled(bool value);
    void setBobosEnabled(bool value);
    void setBobosActivationDelay(int value);
    void setShowWifiAnimation(bool value);
    void setPerformanceMode(const QString &value);
    void setReduceMotion(bool value);
    void setBurnInProtection(const QString &value);
    void load() override;
    void save() override;
Q_SIGNALS:
    void modifiedSectionsChanged();
    void previewRunningChanged();
    void previewErrorChanged();
    void themeChanged();
    void passwordLockChanged();
    void lockMinutesChanged();
    void showTimerChanged();
    void clockVisibleChanged();
    void nowPlayingEnabledChanged();
    void factsEnabledChanged();
    void factsIntervalMinutesChanged();
    void factsContentModeChanged();
    void clockFormatChanged();
    void showDateChanged();
    void clockPositionChanged();
    void clockFontSizeChanged();
    void rainEnabledChanged();
    void snowEnabledChanged();
    void thunderstormsEnabledChanged();
    void fogEnabledChanged();
    void shootingStarsEnabledChanged();
    void bobWeatherEnabledChanged();
    void bobNameChanged();
    void bobColorPresetChanged();
    void bobCustomColorChanged();
    void bobAccessoryChanged();
    void liveSkyEnabledChanged();
    void liveSkyLocationChanged();
    void liveSkyUnitsChanged();
    void liveSkyIntervalChanged();
    void liveSkyConditionsChanged();
    void agentDetectionModeChanged();
    void agentStatusEnabledChanged();
    void agentPromptTimeoutChanged();
    void agentPromptTimeoutActionChanged();
    void phoneEnabledChanged();
    void bobosEnabledChanged();
    void bobosActivationDelayChanged();
    void showWifiAnimationChanged();
    void performanceModeChanged();
    void reduceMotionChanged();
    void burnInProtectionChanged();
private:
    void writeSettings(QSettings &cfg) const;
    void startPreview(bool bobos, bool wifiAnimation, QQuickItem *source = nullptr);
    QProcess *m_previewProcess = nullptr;
    QString m_previewError;
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
    bool m_nowPlayingEnabled = false;
    bool m_savedNowPlayingEnabled = false;
    bool m_factsEnabled = true;
    int m_factsIntervalMinutes = 3;
    QString m_factsContentMode = QStringLiteral("facts");
    bool m_savedFactsEnabled = true;
    int m_savedFactsIntervalMinutes = 3;
    QString m_savedFactsContentMode = QStringLiteral("facts");
    QString m_clockFormat = QStringLiteral("12h");
    bool m_showDate = false;
    QString m_clockPosition = QStringLiteral("top-center");
    int m_clockFontSize = 48;
    bool m_rainEnabled = false;
    bool m_snowEnabled = false;
    bool m_thunderstormsEnabled = false;
    bool m_fogEnabled = false;
    bool m_shootingStarsEnabled = false;
    bool m_bobWeatherEnabled = true;
    QString m_bobName = QStringLiteral("Bob");
    QString m_bobColorPreset = QStringLiteral("cyan");
    QString m_bobCustomColor = QStringLiteral("#6bf6ff");
    QString m_bobAccessory = QStringLiteral("none");
    bool m_liveSkyEnabled = false;
    QStringList m_liveSkyLocations;
    QString m_liveSkyLocation;
    LocationSearch m_locationSearch;
    QVariantMap m_liveSkyPlace;
    QVariantMap m_savedLiveSkyPlace;
    QString m_liveSkyUnits = QStringLiteral("c");
    int m_liveSkyInterval = 30;
    bool m_liveSkyConditions = true;
    QString m_agentDetectionMode = QStringLiteral("ask");
    bool m_agentStatusEnabled = true;
    int m_agentPromptTimeout = 10;
    QString m_agentPromptTimeoutAction = QStringLiteral("start");
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
    bool m_savedBobWeatherEnabled = true;
    QString m_savedBobName = QStringLiteral("Bob");
    QString m_savedBobColorPreset = QStringLiteral("cyan");
    QString m_savedBobCustomColor = QStringLiteral("#6bf6ff");
    QString m_savedBobAccessory = QStringLiteral("none");
    bool m_savedLiveSkyEnabled = false;
    QString m_savedLiveSkyLocation;
    QString m_savedLiveSkyUnits = QStringLiteral("c");
    int m_savedLiveSkyInterval = 30;
    bool m_savedLiveSkyConditions = true;
    QString m_savedAgentDetectionMode = QStringLiteral("ask");
    bool m_savedAgentStatusEnabled = true;
    int m_savedAgentPromptTimeout = 10;
    QString m_savedAgentPromptTimeoutAction = QStringLiteral("start");
    bool m_phoneEnabled = true;
    bool m_bobosEnabled = true;
    int m_bobosActivationDelay = 3;
    bool m_showWifiAnimation = true;
    QString m_performanceMode = QStringLiteral("balanced");
    bool m_reduceMotion = false;
    QString m_burnInProtection = QStringLiteral("standard");
    bool m_savedPhoneEnabled = true;
    bool m_savedBobosEnabled = true;
    int m_savedBobosActivationDelay = 3;
    bool m_savedShowWifiAnimation = true;
    QString m_savedPerformanceMode = QStringLiteral("balanced");
    bool m_savedReduceMotion = false;
    QString m_savedBurnInProtection = QStringLiteral("standard");
};
