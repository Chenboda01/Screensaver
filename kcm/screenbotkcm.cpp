#include "screenbotkcm.h"
#include <KPluginFactory>
#include <KLocalizedString>
#include <QSettings>
#include <QUrl>
#include <QProcess>
#include <QDir>
#include <QFile>
#include <QStandardPaths>
#include <QStringList>
#include <QtGlobal>
#include <QQuickItem>
#include <QQuickWindow>
#include <QScreen>
#include <QTemporaryFile>
#include <QColor>
#include <QTextBoundaryFinder>

K_PLUGIN_CLASS_WITH_JSON(ScreenBotKcm, "kcm_screenbot_screensaver.json")

static QString configFile() {
    return QStandardPaths::writableLocation(QStandardPaths::ConfigLocation)
           + QStringLiteral("/screenbot-screensaver.ini");
}

static QString sanitizedBobName(QString value) {
    QString safe;
    for (qsizetype index = 0; index < value.size(); ++index) {
        const QChar character = value.at(index);
        if (character.isHighSurrogate() && index + 1 < value.size()
            && value.at(index + 1).isLowSurrogate()) {
            safe.append(character);
            safe.append(value.at(++index));
            continue;
        }
        if (character.isSpace()) {
            safe.append(QLatin1Char(' '));
            continue;
        }
        if (character == QChar(0x200d)) {
            safe.append(character);
            continue;
        }
        const auto category = character.category();
        if (category == QChar::Other_Control || category == QChar::Other_Format
            || category == QChar::Other_Surrogate) continue;
        safe.append(character);
    }
    safe = safe.simplified();
    QTextBoundaryFinder boundaryFinder(QTextBoundaryFinder::Grapheme, safe);
    qsizetype end = 0;
    for (int grapheme = 0; grapheme < 16; ++grapheme) {
        const qsizetype next = boundaryFinder.toNextBoundary();
        if (next < 0) break;
        end = next;
    }
    safe.truncate(end);
    return safe.isEmpty() ? QStringLiteral("Bob") : safe;
}

static bool validBobColor(const QString &value) {
    return value.size() == 7 && value.front() == QLatin1Char('#')
        && QColor(value).isValid();
}

static bool validBobAccessory(const QString &value) {
    return value == QLatin1String("none") || value == QLatin1String("cap")
        || value == QLatin1String("bow-tie") || value == QLatin1String("headphones")
        || value == QLatin1String("flower") || value == QLatin1String("crown")
        || value == QLatin1String("antenna-ball");
}

ScreenBotKcm::ScreenBotKcm(QObject *parent, const KPluginMetaData &data)
    : KQuickConfigModule(parent, data) {
    setButtons(Apply);
    setSupportsInstantApply(false);
    const QString locationsPath = QStandardPaths::locate(
        QStandardPaths::GenericDataLocation,
        QStringLiteral("screenbot-screensaver/countries_and_cities.txt"));
    QFile locationsFile(locationsPath);
    if (locationsFile.open(QIODevice::ReadOnly | QIODevice::Text)) {
        while (!locationsFile.atEnd()) {
            const QString entry = QString::fromUtf8(locationsFile.readLine()).trimmed();
            const qsizetype separator = entry.indexOf(QLatin1Char(','));
            if (separator <= 0 || separator == entry.size() - 1) continue;
            const QString country = entry.left(separator).trimmed();
            const QString city = entry.mid(separator + 1).trimmed();
            if (!country.isEmpty() && !city.isEmpty())
                m_liveSkyLocations.append(city + QStringLiteral(", ") + country);
        }
    }
    m_locationSearch.setCatalog(m_liveSkyLocations);
    load();
}

QStringList ScreenBotKcm::modifiedSections() const {
    QStringList sections;
    if (m_theme != m_savedTheme || m_photoFolder != m_savedPhotoFolder
        || m_photoIncludeSubfolders != m_savedPhotoIncludeSubfolders
        || m_photoInterval != m_savedPhotoInterval || m_photoOrder != m_savedPhotoOrder
        || m_photoFit != m_savedPhotoFit) sections.append(QStringLiteral("theme"));
    if (m_clockVisible != m_savedClockVisible
        || m_clockFormat != m_savedClockFormat
        || m_showDate != m_savedShowDate
        || m_clockPosition != m_savedClockPosition
        || m_clockFontSize != m_savedClockFontSize) sections.append(QStringLiteral("clock"));
    if (m_rainEnabled != m_savedRainEnabled
        || m_snowEnabled != m_savedSnowEnabled
        || m_thunderstormsEnabled != m_savedThunderstormsEnabled
        || m_fogEnabled != m_savedFogEnabled
        || m_shootingStarsEnabled != m_savedShootingStarsEnabled
        || m_bobWeatherEnabled != m_savedBobWeatherEnabled) sections.append(QStringLiteral("weather"));
    if (m_liveSkyEnabled != m_savedLiveSkyEnabled
        || m_liveSkyLocation != m_savedLiveSkyLocation
        || m_liveSkyPlace != m_savedLiveSkyPlace
        || m_liveSkyUnits != m_savedLiveSkyUnits
        || m_liveSkyInterval != m_savedLiveSkyInterval
        || m_liveSkyConditions != m_savedLiveSkyConditions) sections.append(QStringLiteral("liveSky"));
    if (m_agentDetectionMode != m_savedAgentDetectionMode
        || m_agentStatusEnabled != m_savedAgentStatusEnabled
        || m_agentPromptTimeout != m_savedAgentPromptTimeout
        || m_agentPromptTimeoutAction != m_savedAgentPromptTimeoutAction) sections.append(QStringLiteral("agents"));
    if (m_phoneEnabled != m_savedPhoneEnabled
        || m_bobosEnabled != m_savedBobosEnabled
        || m_bobosActivationDelay != m_savedBobosActivationDelay
        || m_showWifiAnimation != m_savedShowWifiAnimation) sections.append(QStringLiteral("bobos"));
    if (m_bobName != m_savedBobName || m_bobColorPreset != m_savedBobColorPreset
        || m_bobCustomColor != m_savedBobCustomColor || m_bobAccessory != m_savedBobAccessory)
        sections.append(QStringLiteral("appearance"));
    if (m_performanceMode != m_savedPerformanceMode || m_reduceMotion != m_savedReduceMotion
        || m_burnInProtection != m_savedBurnInProtection)
        sections.append(QStringLiteral("performance"));
    if (m_passwordLock != m_savedPasswordLock
        || m_lockMinutes != m_savedLockMinutes
        || m_showTimer != m_savedShowTimer) sections.append(QStringLiteral("lock"));
    return sections;
}

void ScreenBotKcm::checkModified() {
    setNeedsSave(!modifiedSections().isEmpty());
    Q_EMIT modifiedSectionsChanged();
}

bool ScreenBotKcm::sectionExpanded(const QString &section) const {
    QSettings state(QStandardPaths::writableLocation(QStandardPaths::ConfigLocation)
                    + QStringLiteral("/screenbot-kcm-state.ini"), QSettings::IniFormat);
    return state.value(QStringLiteral("Sections/") + section, section == QLatin1String("theme")).toBool();
}

void ScreenBotKcm::setSectionExpanded(const QString &section, bool expanded) {
    const QStringList sections{QStringLiteral("theme"), QStringLiteral("appearance"), QStringLiteral("clock"), QStringLiteral("weather"),
        QStringLiteral("liveSky"), QStringLiteral("agents"), QStringLiteral("bobos"),
        QStringLiteral("performance"), QStringLiteral("lock")};
    if (!sections.contains(section)) return;
    QSettings state(QStandardPaths::writableLocation(QStandardPaths::ConfigLocation)
                    + QStringLiteral("/screenbot-kcm-state.ini"), QSettings::IniFormat);
    state.setValue(QStringLiteral("Sections/") + section, expanded);
    state.sync();
}

void ScreenBotKcm::load() {
    QSettings cfg(configFile(), QSettings::IniFormat);
    const QString theme = cfg.value(QStringLiteral("Screensaver/theme"), QStringLiteral("random")).toString();
    const QString validTheme = (theme == QLatin1String("space") || theme == QLatin1String("mountains") || theme == QLatin1String("random") || theme == QLatin1String("snow") || theme == QLatin1String("forest") || theme == QLatin1String("city") || theme == QLatin1String("aurora") || theme == QLatin1String("ocean") || theme == QLatin1String("desert") || theme == QLatin1String("underwater") || theme == QLatin1String("photos")) ? theme : QStringLiteral("random");
    const QString defaultPhotoFolder = QDir::homePath() + QStringLiteral("/Pictures");
    const QString requestedPhotoFolder = cfg.value(QStringLiteral("Screensaver/photo_folder"), defaultPhotoFolder).toString().trimmed();
    const QString photoFolder = requestedPhotoFolder.isEmpty() ? defaultPhotoFolder : QDir::cleanPath(requestedPhotoFolder);
    const bool photoIncludeSubfolders = cfg.value(QStringLiteral("Screensaver/photo_include_subfolders"), false).toBool();
    const int photoInterval = qBound(5, cfg.value(QStringLiteral("Screensaver/photo_interval_seconds"), 15).toInt(), 120);
    const QString requestedPhotoOrder = cfg.value(QStringLiteral("Screensaver/photo_order"), QStringLiteral("name")).toString();
    const QString photoOrder = requestedPhotoOrder == QLatin1String("date") || requestedPhotoOrder == QLatin1String("random")
        ? requestedPhotoOrder : QStringLiteral("name");
    const QString requestedPhotoFit = cfg.value(QStringLiteral("Screensaver/photo_fit"), QStringLiteral("fill")).toString();
    const QString photoFit = requestedPhotoFit == QLatin1String("fit-blur") ? requestedPhotoFit : QStringLiteral("fill");
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
    const bool bobWeather = cfg.value(QStringLiteral("Screensaver/bob_weather_enabled"), true).toBool();
    const QString bobName = sanitizedBobName(cfg.value(QStringLiteral("Screensaver/bob_name"), QStringLiteral("Bob")).toString());
    const QString requestedBobColorPreset = cfg.value(QStringLiteral("Screensaver/bob_color_preset"), QStringLiteral("cyan")).toString().toLower();
    const QStringList bobColorPresets{QStringLiteral("cyan"), QStringLiteral("green"), QStringLiteral("purple"),
        QStringLiteral("orange"), QStringLiteral("pink"), QStringLiteral("gold"), QStringLiteral("custom")};
    const QString bobColorPreset = bobColorPresets.contains(requestedBobColorPreset)
        ? requestedBobColorPreset : QStringLiteral("cyan");
    QString bobCustomColor = cfg.value(QStringLiteral("Screensaver/bob_custom_color"), QStringLiteral("#6bf6ff")).toString().toLower();
    if (!validBobColor(bobCustomColor)) bobCustomColor = QStringLiteral("#6bf6ff");
    const QString requestedBobAccessory = cfg.value(QStringLiteral("Screensaver/bob_accessory"), QStringLiteral("none")).toString().toLower();
    const QString bobAccessory = validBobAccessory(requestedBobAccessory) ? requestedBobAccessory : QStringLiteral("none");
    const bool liveSky = cfg.value(QStringLiteral("Screensaver/live_sky_enabled"), false).toBool();
    const QVariant locationValue = cfg.value(QStringLiteral("Screensaver/live_sky_location"));
    const QString requestedLiveSkyLocation = locationValue.metaType().id() == QMetaType::QStringList
        ? locationValue.toStringList().join(QStringLiteral(", ")) : locationValue.toString();
    const QString liveSkyLocation = requestedLiveSkyLocation;
    QVariantMap place;
    const QString latitudeKey = QStringLiteral("Screensaver/live_sky_latitude");
    const QString longitudeKey = QStringLiteral("Screensaver/live_sky_longitude");
    bool latitudeOk = false, longitudeOk = false;
    const double latitude = cfg.value(latitudeKey).toDouble(&latitudeOk);
    const double longitude = cfg.value(longitudeKey).toDouble(&longitudeOk);
    if (!liveSkyLocation.isEmpty() && latitudeOk && longitudeOk
        && qIsFinite(latitude) && qIsFinite(longitude)
        && qAbs(latitude) <= 90 && qAbs(longitude) <= 180) {
        place = {{QStringLiteral("latitude"), latitude}, {QStringLiteral("longitude"), longitude},
                 {QStringLiteral("timezone"), cfg.value(QStringLiteral("Screensaver/live_sky_timezone")).toString()}};
    }
    m_liveSkyPlace = place;
    m_locationSearch.setEnabled(liveSky);
    m_locationSearch.search(QString());
    const QString requestedLiveSkyUnits = cfg.value(QStringLiteral("Screensaver/live_sky_units"), QStringLiteral("c")).toString();
    const QString liveSkyUnits = requestedLiveSkyUnits == QLatin1String("f") ? QStringLiteral("f") : QStringLiteral("c");
    const int requestedLiveSkyInterval = cfg.value(QStringLiteral("Screensaver/live_sky_interval"), 30).toInt();
    const int liveSkyInterval = requestedLiveSkyInterval == 15 || requestedLiveSkyInterval == 60
        ? requestedLiveSkyInterval : 30;
    const bool liveSkyConditions = cfg.value(QStringLiteral("Screensaver/live_sky_conditions"), true).toBool();
    const QString requestedAgentMode = cfg.value(QStringLiteral("Screensaver/agent_detection_mode"), QStringLiteral("ask")).toString();
    const bool agentStatusEnabled = cfg.value(QStringLiteral("Screensaver/agent_status_enabled"), true).toBool();
    const QString agentMode = requestedAgentMode == QLatin1String("start") || requestedAgentMode == QLatin1String("block")
        ? requestedAgentMode : QStringLiteral("ask");
    bool timeoutOk = false;
    const int requestedTimeout = cfg.value(QStringLiteral("Screensaver/agent_prompt_timeout_seconds"), 10).toInt(&timeoutOk);
    const int promptTimeout = !timeoutOk ? 10 : (requestedTimeout == 0 ? 0 : qBound(5, requestedTimeout, 120));
    const QString requestedTimeoutAction = cfg.value(QStringLiteral("Screensaver/agent_prompt_timeout_action"), QStringLiteral("start")).toString();
    const QString promptTimeoutAction = requestedTimeoutAction == QLatin1String("cancel") ? requestedTimeoutAction : QStringLiteral("start");
    const bool phone = cfg.value(QStringLiteral("Screensaver/bob_phone_enabled"),
                                  cfg.value(QStringLiteral("Screensaver/ai_backpack_enabled"), true)).toBool();
    const bool bobos = cfg.value(QStringLiteral("Screensaver/bobos_enabled"), true).toBool();
    const int bobosDelay = qBound(1, cfg.value(QStringLiteral("Screensaver/bobos_activation_delay"), 3).toInt(), 30);
    const bool wifiAnimation = cfg.value(QStringLiteral("Screensaver/show_wifi_animation"), true).toBool();
    const QString requestedPerformanceMode = cfg.value(QStringLiteral("Screensaver/performance_mode"), QStringLiteral("balanced")).toString();
    const QString performanceMode = requestedPerformanceMode == QLatin1String("smooth")
        || requestedPerformanceMode == QLatin1String("battery-saver")
        ? requestedPerformanceMode : QStringLiteral("balanced");
    const bool reduceMotion = cfg.value(QStringLiteral("Screensaver/reduce_motion"), false).toBool();
    const QString requestedBurnInProtection = cfg.value(QStringLiteral("Screensaver/burn_in_protection"), QStringLiteral("standard")).toString();
    const QString burnInProtection = requestedBurnInProtection == QLatin1String("off")
        || requestedBurnInProtection == QLatin1String("strong")
        ? requestedBurnInProtection : QStringLiteral("standard");
    if (m_theme != validTheme) { m_theme = validTheme; Q_EMIT themeChanged(); }
    if (m_photoFolder != photoFolder) { m_photoFolder = photoFolder; Q_EMIT photoFolderChanged(); }
    if (m_photoIncludeSubfolders != photoIncludeSubfolders) { m_photoIncludeSubfolders = photoIncludeSubfolders; Q_EMIT photoIncludeSubfoldersChanged(); }
    if (m_photoInterval != photoInterval) { m_photoInterval = photoInterval; Q_EMIT photoIntervalChanged(); }
    if (m_photoOrder != photoOrder) { m_photoOrder = photoOrder; Q_EMIT photoOrderChanged(); }
    if (m_photoFit != photoFit) { m_photoFit = photoFit; Q_EMIT photoFitChanged(); }
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
    if (m_bobWeatherEnabled != bobWeather) { m_bobWeatherEnabled = bobWeather; Q_EMIT bobWeatherEnabledChanged(); }
    if (m_bobName != bobName) { m_bobName = bobName; Q_EMIT bobNameChanged(); }
    if (m_bobColorPreset != bobColorPreset) { m_bobColorPreset = bobColorPreset; Q_EMIT bobColorPresetChanged(); }
    if (m_bobCustomColor != bobCustomColor) { m_bobCustomColor = bobCustomColor; Q_EMIT bobCustomColorChanged(); }
    if (m_bobAccessory != bobAccessory) { m_bobAccessory = bobAccessory; Q_EMIT bobAccessoryChanged(); }
    if (m_liveSkyEnabled != liveSky) { m_liveSkyEnabled = liveSky; Q_EMIT liveSkyEnabledChanged(); }
    m_liveSkyLocation = liveSkyLocation;
    Q_EMIT liveSkyLocationChanged();
    if (m_liveSkyUnits != liveSkyUnits) { m_liveSkyUnits = liveSkyUnits; Q_EMIT liveSkyUnitsChanged(); }
    if (m_liveSkyInterval != liveSkyInterval) { m_liveSkyInterval = liveSkyInterval; Q_EMIT liveSkyIntervalChanged(); }
    if (m_liveSkyConditions != liveSkyConditions) { m_liveSkyConditions = liveSkyConditions; Q_EMIT liveSkyConditionsChanged(); }
    if (m_agentDetectionMode != agentMode) { m_agentDetectionMode = agentMode; Q_EMIT agentDetectionModeChanged(); }
    if (m_agentStatusEnabled != agentStatusEnabled) { m_agentStatusEnabled = agentStatusEnabled; Q_EMIT agentStatusEnabledChanged(); }
    if (m_agentPromptTimeout != promptTimeout) { m_agentPromptTimeout = promptTimeout; Q_EMIT agentPromptTimeoutChanged(); }
    if (m_agentPromptTimeoutAction != promptTimeoutAction) { m_agentPromptTimeoutAction = promptTimeoutAction; Q_EMIT agentPromptTimeoutActionChanged(); }
    if (m_phoneEnabled != phone) { m_phoneEnabled = phone; Q_EMIT phoneEnabledChanged(); }
    if (m_bobosEnabled != bobos) { m_bobosEnabled = bobos; Q_EMIT bobosEnabledChanged(); }
    if (m_bobosActivationDelay != bobosDelay) { m_bobosActivationDelay = bobosDelay; Q_EMIT bobosActivationDelayChanged(); }
    if (m_showWifiAnimation != wifiAnimation) { m_showWifiAnimation = wifiAnimation; Q_EMIT showWifiAnimationChanged(); }
    if (m_performanceMode != performanceMode) { m_performanceMode = performanceMode; Q_EMIT performanceModeChanged(); }
    if (m_reduceMotion != reduceMotion) { m_reduceMotion = reduceMotion; Q_EMIT reduceMotionChanged(); }
    if (m_burnInProtection != burnInProtection) { m_burnInProtection = burnInProtection; Q_EMIT burnInProtectionChanged(); }
    m_savedTheme = m_theme;
    m_savedPhotoFolder = m_photoFolder;
    m_savedPhotoIncludeSubfolders = m_photoIncludeSubfolders;
    m_savedPhotoInterval = m_photoInterval;
    m_savedPhotoOrder = m_photoOrder;
    m_savedPhotoFit = m_photoFit;
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
    m_savedBobWeatherEnabled = m_bobWeatherEnabled;
    m_savedBobName = m_bobName;
    m_savedBobColorPreset = m_bobColorPreset;
    m_savedBobCustomColor = m_bobCustomColor;
    m_savedBobAccessory = m_bobAccessory;
    m_savedLiveSkyEnabled = m_liveSkyEnabled;
    m_savedLiveSkyLocation = m_liveSkyLocation;
    m_savedLiveSkyPlace = m_liveSkyPlace;
    m_savedLiveSkyUnits = m_liveSkyUnits;
    m_savedLiveSkyInterval = m_liveSkyInterval;
    m_savedLiveSkyConditions = m_liveSkyConditions;
    m_savedAgentDetectionMode = m_agentDetectionMode;
    m_savedAgentStatusEnabled = m_agentStatusEnabled;
    m_savedAgentPromptTimeout = m_agentPromptTimeout;
    m_savedAgentPromptTimeoutAction = m_agentPromptTimeoutAction;
    m_savedPhoneEnabled = m_phoneEnabled;
    m_savedBobosEnabled = m_bobosEnabled;
    m_savedBobosActivationDelay = m_bobosActivationDelay;
    m_savedShowWifiAnimation = m_showWifiAnimation;
    m_savedPerformanceMode = m_performanceMode;
    m_savedReduceMotion = m_reduceMotion;
    m_savedBurnInProtection = m_burnInProtection;
    checkModified();
}

void ScreenBotKcm::writeSettings(QSettings &cfg) const {
    cfg.setValue(QStringLiteral("Screensaver/theme"), m_theme);
    cfg.setValue(QStringLiteral("Screensaver/photo_folder"), m_photoFolder);
    cfg.setValue(QStringLiteral("Screensaver/photo_include_subfolders"), m_photoIncludeSubfolders);
    cfg.setValue(QStringLiteral("Screensaver/photo_interval_seconds"), m_photoInterval);
    cfg.setValue(QStringLiteral("Screensaver/photo_order"), m_photoOrder);
    cfg.setValue(QStringLiteral("Screensaver/photo_fit"), m_photoFit);
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
    cfg.setValue(QStringLiteral("Screensaver/bob_weather_enabled"), m_bobWeatherEnabled);
    cfg.setValue(QStringLiteral("Screensaver/bob_name"), m_bobName);
    cfg.setValue(QStringLiteral("Screensaver/bob_color_preset"), m_bobColorPreset);
    cfg.setValue(QStringLiteral("Screensaver/bob_custom_color"), m_bobCustomColor);
    cfg.setValue(QStringLiteral("Screensaver/bob_accessory"), m_bobAccessory);
    cfg.setValue(QStringLiteral("Screensaver/live_sky_enabled"), m_liveSkyEnabled);
    cfg.setValue(QStringLiteral("Screensaver/live_sky_location"), m_liveSkyLocation);
    for (const QString &field : {QStringLiteral("latitude"), QStringLiteral("longitude"), QStringLiteral("timezone")}) {
        const QString key = QStringLiteral("Screensaver/live_sky_") + field;
        if (m_liveSkyPlace.contains(field)) cfg.setValue(key, m_liveSkyPlace.value(field));
        else cfg.remove(key);
    }
    cfg.setValue(QStringLiteral("Screensaver/live_sky_units"), m_liveSkyUnits);
    cfg.setValue(QStringLiteral("Screensaver/live_sky_interval"), m_liveSkyInterval);
    cfg.setValue(QStringLiteral("Screensaver/live_sky_conditions"), m_liveSkyConditions);
    cfg.setValue(QStringLiteral("Screensaver/agent_detection_mode"), m_agentDetectionMode);
    cfg.setValue(QStringLiteral("Screensaver/agent_status_enabled"), m_agentStatusEnabled);
    cfg.setValue(QStringLiteral("Screensaver/agent_prompt_timeout_seconds"), m_agentPromptTimeout);
    cfg.setValue(QStringLiteral("Screensaver/agent_prompt_timeout_action"), m_agentPromptTimeoutAction);
    cfg.setValue(QStringLiteral("Screensaver/bob_phone_enabled"), m_phoneEnabled);
    cfg.setValue(QStringLiteral("Screensaver/bobos_enabled"), m_bobosEnabled);
    cfg.setValue(QStringLiteral("Screensaver/bobos_activation_delay"), m_bobosActivationDelay);
    cfg.setValue(QStringLiteral("Screensaver/show_wifi_animation"), m_showWifiAnimation);
    cfg.setValue(QStringLiteral("Screensaver/performance_mode"), m_performanceMode);
    cfg.setValue(QStringLiteral("Screensaver/reduce_motion"), m_reduceMotion);
    cfg.setValue(QStringLiteral("Screensaver/burn_in_protection"), m_burnInProtection);
}

void ScreenBotKcm::save() {
    QSettings cfg(configFile(), QSettings::IniFormat);
    writeSettings(cfg);
    cfg.sync();
    if (cfg.status() != QSettings::NoError) {
        qWarning("Could not write ScreenBot settings.");
        return;
    }
    m_savedTheme = m_theme;
    m_savedPhotoFolder = m_photoFolder;
    m_savedPhotoIncludeSubfolders = m_photoIncludeSubfolders;
    m_savedPhotoInterval = m_photoInterval;
    m_savedPhotoOrder = m_photoOrder;
    m_savedPhotoFit = m_photoFit;
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
    m_savedBobWeatherEnabled = m_bobWeatherEnabled;
    m_savedBobName = m_bobName;
    m_savedBobColorPreset = m_bobColorPreset;
    m_savedBobCustomColor = m_bobCustomColor;
    m_savedBobAccessory = m_bobAccessory;
    m_savedLiveSkyEnabled = m_liveSkyEnabled;
    m_savedLiveSkyLocation = m_liveSkyLocation;
    m_savedLiveSkyPlace = m_liveSkyPlace;
    m_savedLiveSkyUnits = m_liveSkyUnits;
    m_savedLiveSkyInterval = m_liveSkyInterval;
    m_savedLiveSkyConditions = m_liveSkyConditions;
    m_savedAgentDetectionMode = m_agentDetectionMode;
    m_savedAgentStatusEnabled = m_agentStatusEnabled;
    m_savedAgentPromptTimeout = m_agentPromptTimeout;
    m_savedAgentPromptTimeoutAction = m_agentPromptTimeoutAction;
    m_savedPhoneEnabled = m_phoneEnabled;
    m_savedBobosEnabled = m_bobosEnabled;
    m_savedBobosActivationDelay = m_bobosActivationDelay;
    m_savedShowWifiAnimation = m_showWifiAnimation;
    m_savedPerformanceMode = m_performanceMode;
    m_savedReduceMotion = m_reduceMotion;
    m_savedBurnInProtection = m_burnInProtection;
    checkModified();
}

void ScreenBotKcm::setTheme(const QString &value) {
    if (value != QLatin1String("space") && value != QLatin1String("mountains") && value != QLatin1String("random") && value != QLatin1String("snow") && value != QLatin1String("forest") && value != QLatin1String("city") && value != QLatin1String("aurora") && value != QLatin1String("ocean") && value != QLatin1String("desert") && value != QLatin1String("underwater") && value != QLatin1String("photos")) return;
    if (value == m_theme) return;
    m_theme = value;
    Q_EMIT themeChanged();
    checkModified();
}

void ScreenBotKcm::setPhotoFolder(const QString &value) {
    const QString folder = value.trimmed().isEmpty()
        ? QDir::homePath() + QStringLiteral("/Pictures") : QDir::cleanPath(value.trimmed());
    if (folder == m_photoFolder) return;
    m_photoFolder = folder;
    Q_EMIT photoFolderChanged();
    checkModified();
}

void ScreenBotKcm::setPhotoFolderUrl(const QUrl &url) {
    if (!url.isLocalFile()) return;
    const QString path = url.toLocalFile();
    if (!path.isEmpty()) setPhotoFolder(path);
}

void ScreenBotKcm::setPhotoIncludeSubfolders(bool value) {
    if (value == m_photoIncludeSubfolders) return;
    m_photoIncludeSubfolders = value;
    Q_EMIT photoIncludeSubfoldersChanged();
    checkModified();
}

void ScreenBotKcm::setPhotoInterval(int value) {
    value = qBound(5, value, 120);
    if (value == m_photoInterval) return;
    m_photoInterval = value;
    Q_EMIT photoIntervalChanged();
    checkModified();
}

void ScreenBotKcm::setPhotoOrder(const QString &value) {
    if (value != QLatin1String("name") && value != QLatin1String("date")
        && value != QLatin1String("random")) return;
    if (value == m_photoOrder) return;
    m_photoOrder = value;
    Q_EMIT photoOrderChanged();
    checkModified();
}

void ScreenBotKcm::setPhotoFit(const QString &value) {
    if (value != QLatin1String("fill") && value != QLatin1String("fit-blur")) return;
    if (value == m_photoFit) return;
    m_photoFit = value;
    Q_EMIT photoFitChanged();
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

void ScreenBotKcm::setBobWeatherEnabled(bool value) {
    if (value == m_bobWeatherEnabled) return;
    m_bobWeatherEnabled = value;
    Q_EMIT bobWeatherEnabledChanged();
    checkModified();
}

void ScreenBotKcm::setBobName(const QString &value) {
    const QString safe = sanitizedBobName(value);
    if (safe == m_bobName) return;
    m_bobName = safe;
    Q_EMIT bobNameChanged();
    checkModified();
}

void ScreenBotKcm::setBobColorPreset(const QString &value) {
    const QString normalized = value.toLower();
    if (normalized != QLatin1String("cyan") && normalized != QLatin1String("green")
        && normalized != QLatin1String("purple") && normalized != QLatin1String("orange")
        && normalized != QLatin1String("pink") && normalized != QLatin1String("gold")
        && normalized != QLatin1String("custom")) return;
    if (normalized == m_bobColorPreset) return;
    m_bobColorPreset = normalized;
    Q_EMIT bobColorPresetChanged();
    checkModified();
}

void ScreenBotKcm::setBobCustomColor(const QString &value) {
    const QString normalized = value.toLower();
    if (!validBobColor(normalized) || normalized == m_bobCustomColor) return;
    m_bobCustomColor = normalized;
    Q_EMIT bobCustomColorChanged();
    checkModified();
}

void ScreenBotKcm::setBobAccessory(const QString &value) {
    const QString normalized = value.toLower();
    if (!validBobAccessory(normalized) || normalized == m_bobAccessory) return;
    m_bobAccessory = normalized;
    Q_EMIT bobAccessoryChanged();
    checkModified();
}

void ScreenBotKcm::setLiveSkyEnabled(bool value) {
    if (value == m_liveSkyEnabled) return;
    m_liveSkyEnabled = value;
    m_locationSearch.setEnabled(value);
    Q_EMIT liveSkyEnabledChanged();
    checkModified();
}

void ScreenBotKcm::setLiveSkyLocation(const QString &value) {
    if (!value.isEmpty() && !m_liveSkyLocations.contains(value)) return;
    if (value == m_liveSkyLocation) return;
    m_liveSkyLocation = value;
    m_liveSkyPlace.clear();
    Q_EMIT liveSkyLocationChanged();
    checkModified();
}

void ScreenBotKcm::selectLiveSkyPlace(int index) {
    const auto results = m_locationSearch.results();
    if (index < 0 || index >= results.size()) return;
    const auto place = results.at(index).toMap();
    m_liveSkyLocation = place.value(QStringLiteral("display")).toString();
    m_liveSkyPlace.clear();
    if (place.contains(QStringLiteral("latitude"))) {
        for (const QString &field : {QStringLiteral("latitude"), QStringLiteral("longitude"), QStringLiteral("timezone")})
            m_liveSkyPlace.insert(field, place.value(field));
    }
    m_locationSearch.search(QString());
    Q_EMIT liveSkyLocationChanged();
    checkModified();
}

void ScreenBotKcm::setLiveSkyUnits(const QString &value) {
    if (value != QLatin1String("c") && value != QLatin1String("f")) return;
    if (value == m_liveSkyUnits) return;
    m_liveSkyUnits = value;
    Q_EMIT liveSkyUnitsChanged();
    checkModified();
}

void ScreenBotKcm::setLiveSkyInterval(int value) {
    if (value != 15 && value != 30 && value != 60) return;
    if (value == m_liveSkyInterval) return;
    m_liveSkyInterval = value;
    Q_EMIT liveSkyIntervalChanged();
    checkModified();
}

void ScreenBotKcm::setLiveSkyConditions(bool value) {
    if (value == m_liveSkyConditions) return;
    m_liveSkyConditions = value;
    Q_EMIT liveSkyConditionsChanged();
    checkModified();
}

void ScreenBotKcm::setAgentDetectionMode(const QString &value) {
    if (value != QLatin1String("ask") && value != QLatin1String("start") && value != QLatin1String("block")) return;
    if (value == m_agentDetectionMode) return;
    m_agentDetectionMode = value;
    Q_EMIT agentDetectionModeChanged();
    checkModified();
}

void ScreenBotKcm::setAgentStatusEnabled(bool value) {
    if (value == m_agentStatusEnabled) return;
    m_agentStatusEnabled = value;
    Q_EMIT agentStatusEnabledChanged();
    checkModified();
}

void ScreenBotKcm::setAgentPromptTimeout(int value) {
    value = value == 0 ? 0 : qBound(5, value, 120);
    if (value == m_agentPromptTimeout) return;
    m_agentPromptTimeout = value;
    Q_EMIT agentPromptTimeoutChanged();
    checkModified();
}

void ScreenBotKcm::setAgentPromptTimeoutAction(const QString &value) {
    const QString action = value == QLatin1String("cancel") ? value : QStringLiteral("start");
    if (action == m_agentPromptTimeoutAction) return;
    m_agentPromptTimeoutAction = action;
    Q_EMIT agentPromptTimeoutActionChanged();
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

void ScreenBotKcm::setPerformanceMode(const QString &value) {
    if (value != QLatin1String("smooth") && value != QLatin1String("balanced")
        && value != QLatin1String("battery-saver")) return;
    if (value == m_performanceMode) return;
    m_performanceMode = value;
    Q_EMIT performanceModeChanged();
    checkModified();
}

void ScreenBotKcm::setReduceMotion(bool value) {
    if (value == m_reduceMotion) return;
    m_reduceMotion = value;
    Q_EMIT reduceMotionChanged();
    checkModified();
}

void ScreenBotKcm::setBurnInProtection(const QString &value) {
    if (value != QLatin1String("off") && value != QLatin1String("standard")
        && value != QLatin1String("strong")) return;
    if (value == m_burnInProtection) return;
    m_burnInProtection = value;
    Q_EMIT burnInProtectionChanged();
    checkModified();
}

void ScreenBotKcm::previewBobOS(bool showWifiAnimation) {
    startPreview(true, showWifiAnimation);
}

void ScreenBotKcm::previewTheme(QQuickItem *source) {
    startPreview(false, m_showWifiAnimation, source);
}

void ScreenBotKcm::startPreview(bool bobos, bool wifiAnimation, QQuickItem *source) {
    if (m_previewProcess) return;
    m_previewError.clear();
    Q_EMIT previewErrorChanged();
    const QString script = QDir::homePath() + QStringLiteral("/ScreenBot/screensaver/start.sh");
    const QString bash = QStandardPaths::findExecutable(QStringLiteral("bash"));
    if (!QFile::exists(script) || bash.isEmpty()) {
        m_previewError = i18n("Preview unavailable. Install ScreenBot in ~/ScreenBot/screensaver and ensure Bash is available on PATH.");
        Q_EMIT previewErrorChanged();
        return;
    }
    auto *process = new QProcess(this);
    auto *temporary = new QTemporaryFile(QDir::tempPath() + QStringLiteral("/screenbot-preview-XXXXXX.ini"), process);
    if (!temporary->open()) {
        m_previewError = i18n("Could not create temporary preview settings.");
        Q_EMIT previewErrorChanged();
        delete process;
        return;
    }
    const QString path = temporary->fileName();
    temporary->close();
    QSettings cfg(path, QSettings::IniFormat);
    writeSettings(cfg);
    cfg.sync();
    if (cfg.status() != QSettings::NoError) {
        m_previewError = i18n("Could not write temporary preview settings.");
        Q_EMIT previewErrorChanged();
        delete process;
        return;
    }
    QStringList arguments{script, bobos ? QStringLiteral("--preview-bobos") : QStringLiteral("--preview"),
                          QStringLiteral("--config"), path};
    if (bobos) arguments.append(wifiAnimation ? QStringLiteral("--wifi-animation") : QStringLiteral("--no-wifi-animation"));
    if (source && source->window() && source->window()->screen())
        arguments.append({QStringLiteral("--screen"), source->window()->screen()->name()});
    auto cleanup = [this, process]() {
        if (m_previewProcess != process) return;
        m_previewProcess = nullptr;
        Q_EMIT previewRunningChanged();
        process->deleteLater();
    };
    connect(process, &QProcess::errorOccurred, this, [this, cleanup](QProcess::ProcessError error) {
        m_previewError = i18n("Could not start the preview. Check the ScreenBot installation and Python 3 dependencies.");
        Q_EMIT previewErrorChanged();
        if (error == QProcess::FailedToStart) cleanup();
    });
    connect(process, &QProcess::finished, this, [this, process, cleanup](int exitCode, QProcess::ExitStatus status) {
        if (exitCode != 0 || status != QProcess::NormalExit) {
            m_previewError = i18n("The preview stopped unexpectedly. Check the ScreenBot installation and Python 3 dependencies.");
            const QString detail = QString::fromUtf8(process->readAllStandardError()).trimmed();
            if (!detail.isEmpty()) m_previewError += QStringLiteral("\n") + detail.left(1000);
            Q_EMIT previewErrorChanged();
        }
        cleanup();
    });
    m_previewProcess = process;
    Q_EMIT previewRunningChanged();
    process->setWorkingDirectory(QDir::homePath() + QStringLiteral("/ScreenBot/screensaver"));
    process->start(bash, arguments);
}

#include "screenbotkcm.moc"
