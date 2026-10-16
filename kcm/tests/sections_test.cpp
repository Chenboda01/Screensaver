#include "screenbotkcm.h"
#include <KPluginMetaData>
#include <QAccessible>
#include <QApplication>
#include <QDir>
#include <QFile>
#include <QMetaProperty>
#include <QJsonDocument>
#include <QJsonObject>
#include <QQmlContext>
#include <QQuickItem>
#include <QQuickView>
#include <KLocalizedContext>
#include <QSettings>
#include <QStandardPaths>
#include <QTemporaryDir>
#include <QTest>

class SectionsTest : public QObject {
    Q_OBJECT
    const QStringList keys{ QStringLiteral("theme"), QStringLiteral("appearance"), QStringLiteral("clock"), QStringLiteral("weather"), QStringLiteral("liveSky"), QStringLiteral("seasonal"), QStringLiteral("agents"), QStringLiteral("bobos"), QStringLiteral("performance"), QStringLiteral("lock") };
    QString configPath() const { return QStandardPaths::writableLocation(QStandardPaths::ConfigLocation); }
    QByteArray savedBytes() {
        QFile file(configPath() + QStringLiteral("/screenbot-screensaver.ini"));
        if (!file.open(QIODevice::ReadOnly)) return {};
        return file.readAll();
    }
private Q_SLOTS:
    void init() {
        QFile::remove(configPath() + QStringLiteral("/screenbot-screensaver.ini"));
        QFile::remove(configPath() + QStringLiteral("/screenbot-kcm-state.ini"));
    }
    void expansionDoesNotApplySettings() {
        ScreenBotKcm kcm(nullptr, KPluginMetaData());
        kcm.save();
        const auto before = savedBytes();
        QVERIFY(!before.isEmpty());
        for (const auto &key : keys) QCOMPARE(kcm.sectionExpanded(key), key == QStringLiteral("theme"));
        kcm.setClockFormat(QStringLiteral("24h"));
        for (const auto &key : keys) kcm.setSectionExpanded(key, key != QStringLiteral("theme"));
        QCOMPARE(savedBytes(), before);
        QVERIFY(kcm.needsSave());
        ScreenBotKcm reopened(nullptr, KPluginMetaData());
        for (const auto &key : keys) QCOMPARE(reopened.sectionExpanded(key), key != QStringLiteral("theme"));
        QCOMPARE(reopened.clockFormat(), QStringLiteral("12h"));
        kcm.load();
        QVERIFY(!kcm.needsSave());
        QVERIFY(kcm.sectionExpanded(QStringLiteral("clock")));
    }
    void allSettingsApplyDiscard() {
        ScreenBotKcm kcm(nullptr, KPluginMetaData());
        kcm.save();
        const auto before = savedBytes();
        const QVariantMap changes{
            {QStringLiteral("theme"), QStringLiteral("forest")}, {QStringLiteral("clockVisible"), false}, {QStringLiteral("clockFormat"), QStringLiteral("24h")}, {QStringLiteral("showDate"), true},
            {QStringLiteral("nowPlayingEnabled"), true}, {QStringLiteral("clockPosition"), QStringLiteral("bottom-right")}, {QStringLiteral("clockFontSize"), 24}, {QStringLiteral("rainEnabled"), true},
            {QStringLiteral("snowEnabled"), true}, {QStringLiteral("thunderstormsEnabled"), true}, {QStringLiteral("fogEnabled"), true}, {QStringLiteral("shootingStarsEnabled"), true},
            {QStringLiteral("bobWeatherEnabled"), false},
            {QStringLiteral("bobName"), QStringLiteral("Pixel👩‍🚀")},
            {QStringLiteral("bobColorPreset"), QStringLiteral("custom")},
            {QStringLiteral("bobCustomColor"), QStringLiteral("#a06cff")},
            {QStringLiteral("bobAccessory"), QStringLiteral("flower")},
            {QStringLiteral("liveSkyEnabled"), true}, {QStringLiteral("liveSkyUnits"), QStringLiteral("f")}, {QStringLiteral("liveSkyInterval"), 60}, {QStringLiteral("liveSkyConditions"), false},
            {QStringLiteral("seasonalEnabled"), false}, {QStringLiteral("seasonalNewYearEnabled"), false},
            {QStringLiteral("seasonalLunarNewYearEnabled"), true}, {QStringLiteral("seasonalValentinesEnabled"), true},
            {QStringLiteral("seasonalSpringEnabled"), true}, {QStringLiteral("seasonalHalloweenEnabled"), true},
            {QStringLiteral("seasonalWinterHolidaysEnabled"), true}, {QStringLiteral("seasonalBirthdayEnabled"), true},
            {QStringLiteral("seasonalBirthdayDate"), QStringLiteral("02-29")},
            {QStringLiteral("seasonalBirthdayName"), QStringLiteral("Pixel")},
            {QStringLiteral("agentDetectionMode"), QStringLiteral("block")}, {QStringLiteral("phoneEnabled"), false}, {QStringLiteral("bobosEnabled"), false},
            {QStringLiteral("bobosActivationDelay"), 7}, {QStringLiteral("showWifiAnimation"), false}, {QStringLiteral("passwordLock"), true},
            {QStringLiteral("lockMinutes"), 5}, {QStringLiteral("showTimer"), true},
            {QStringLiteral("performanceMode"), QStringLiteral("battery-saver")}, {QStringLiteral("reduceMotion"), true},
            {QStringLiteral("burnInProtection"), QStringLiteral("strong")}
        };
        QVariantMap defaults;
        for (auto it = changes.cbegin(); it != changes.cend(); ++it) {
            defaults.insert(it.key(), kcm.property(it.key().toUtf8().constData()));
            QVERIFY(kcm.setProperty(it.key().toUtf8().constData(), it.value()));
        }
        auto dirty = kcm.modifiedSections();
        for (const auto &key : keys) QVERIFY(dirty.contains(key));
        QCOMPARE(savedBytes(), before);
        kcm.load();
        for (auto it = defaults.cbegin(); it != defaults.cend(); ++it) QCOMPARE(kcm.property(it.key().toUtf8().constData()), it.value());
        QVERIFY(kcm.modifiedSections().isEmpty());
        for (auto it = changes.cbegin(); it != changes.cend(); ++it) QVERIFY(kcm.setProperty(it.key().toUtf8().constData(), it.value()));
        kcm.save();
        QVERIFY(kcm.modifiedSections().isEmpty());
        ScreenBotKcm reopened(nullptr, KPluginMetaData());
        for (auto it = changes.cbegin(); it != changes.cend(); ++it) QCOMPARE(reopened.property(it.key().toUtf8().constData()).toString(), it.value().toString());
    }
    void bobAppearanceNamesAndValuesAreValidated() {
        ScreenBotKcm kcm(nullptr, KPluginMetaData());
        kcm.setBobName(QStringLiteral("👩‍🚀").repeated(18));
        QCOMPARE(kcm.bobName(), QStringLiteral("👩‍🚀").repeated(16));
        kcm.setBobName(QString(QChar(0x202e)) + QStringLiteral("  "));
        QCOMPARE(kcm.bobName(), QStringLiteral("Bob"));
        kcm.setBobColorPreset(QStringLiteral("invalid"));
        QCOMPARE(kcm.bobColorPreset(), QStringLiteral("cyan"));
        kcm.setBobCustomColor(QStringLiteral("not-a-color"));
        QCOMPARE(kcm.bobCustomColor(), QStringLiteral("#6bf6ff"));
        kcm.setBobAccessory(QStringLiteral("runs-command"));
        QCOMPARE(kcm.bobAccessory(), QStringLiteral("none"));
    }
    void seasonalBirthdayInputIsValidatedAndLocalOnly() {
        ScreenBotKcm kcm(nullptr, KPluginMetaData());
        kcm.setSeasonalBirthdayDate(QStringLiteral("02-29"));
        QCOMPARE(kcm.seasonalBirthdayDate(), QStringLiteral("02-29"));
        kcm.setSeasonalBirthdayDate(QStringLiteral("02-30"));
        QCOMPARE(kcm.seasonalBirthdayDate(), QStringLiteral("02-29"));
        kcm.setSeasonalBirthdayName(QString(QChar(0x202e)) + QStringLiteral("  Pixel\n") + QStringLiteral("👩‍🚀").repeated(40));
        QVERIFY(!kcm.seasonalBirthdayName().contains(QChar(0x202e)));
        QVERIFY(!kcm.seasonalBirthdayName().contains(QLatin1Char('\n')));
        QVERIFY(kcm.seasonalBirthdayName().size() < 200);
        kcm.save();
        QVERIFY(savedBytes().contains("seasonal_birthday_name=Pixel"));
    }
    void bobosPreviewInsideSection() {
        const QString evidence = qEnvironmentVariable("SCREENBOT_EVIDENCE_DIR");
        QDir().mkpath(evidence);
        qputenv("SCREENBOT_SOURCE", SCREENBOT_SOURCE_DIR);
        qputenv("SCREENBOT_PREVIEW_EVIDENCE", evidence.toUtf8());
        const QString install = QDir::homePath() + QStringLiteral("/ScreenBot/screensaver");
        QVERIFY(QDir().mkpath(install));
        QVERIFY(QFile::copy(QStringLiteral(SCREENBOT_SOURCE_DIR "/tests/kcm_preview/preview_probe.py"), install + QStringLiteral("/screensaver.py")));
        QVERIFY(QFile::copy(QStringLiteral(SCREENBOT_SOURCE_DIR "/start.sh"), install + QStringLiteral("/start.sh")));
        QVERIFY(QFile::copy(QStringLiteral(SCREENBOT_SOURCE_DIR "/python-runtime.sh"), install + QStringLiteral("/python-runtime.sh")));
        ScreenBotKcm kcm(nullptr, KPluginMetaData());
        kcm.setBobName(QStringLiteral("Pixel"));
        kcm.setBobColorPreset(QStringLiteral("custom"));
        kcm.setBobCustomColor(QStringLiteral("#a06cff"));
        kcm.setBobAccessory(QStringLiteral("flower"));
        QQuickView view;
        auto *translations = new KLocalizedContext(&view);
        translations->setTranslationDomain(QStringLiteral("kcm_screenbot_screensaver"));
        view.rootContext()->setContextObject(translations);
        view.rootContext()->setContextProperty(QStringLiteral("kcm"), &kcm);
        view.setSource(QUrl::fromLocalFile(QStringLiteral(SCREENBOT_SOURCE_DIR "/kcm/ui/main.qml")));
        QCOMPARE(view.status(), QQuickView::Ready);
        view.setResizeMode(QQuickView::SizeRootObjectToView);
        view.resize(1000, 900);
        view.show();
        QVERIFY(QTest::qWaitForWindowExposed(&view));
        auto *section = view.rootObject()->findChild<QQuickItem *>(QStringLiteral("bobosSection"));
        auto *button = view.rootObject()->findChild<QQuickItem *>(QStringLiteral("bobosPreviewButton"));
        QVERIFY(section);
        QVERIFY(button);
        section->setProperty("expanded", true);
        QTest::qWait(300);
        QTest::mouseClick(&view, Qt::LeftButton, Qt::NoModifier,
            button->mapToScene(QPointF(button->width() / 2, button->height() / 2)).toPoint());
        QVERIFY(kcm.previewRunning());
        QTRY_VERIFY_WITH_TIMEOUT(!kcm.previewRunning(), 10000);
        QVERIFY2(kcm.previewError().isEmpty(), qPrintable(kcm.previewError()));
        QFile receipt(evidence + QStringLiteral("/launches.jsonl"));
        QVERIFY(receipt.open(QIODevice::ReadOnly));
        const auto result = QJsonDocument::fromJson(receipt.readAll().trimmed().split('\n').last()).object();
        QVERIFY(result[QStringLiteral("bobos_enabled")].toBool());
        const auto temporarySettings = result[QStringLiteral("config")].toObject();
        QCOMPARE(temporarySettings[QStringLiteral("bob_name")].toString(), QStringLiteral("Pixel"));
        QCOMPARE(temporarySettings[QStringLiteral("bob_color_preset")].toString(), QStringLiteral("custom"));
        QCOMPARE(temporarySettings[QStringLiteral("bob_custom_color")].toString(), QStringLiteral("#a06cff"));
        QCOMPARE(temporarySettings[QStringLiteral("bob_accessory")].toString(), QStringLiteral("flower"));
        QVERIFY(!result[QStringLiteral("password_lock")].toBool());
        QVERIFY(!result[QStringLiteral("show_timer")].toBool());
        QVERIFY(!QFile::exists(result[QStringLiteral("temporary_path")].toString()));
    }
    void nativeUiKeyboardAccessibilityAndCaptures() {
        ScreenBotKcm kcm(nullptr, KPluginMetaData());
        QQuickView view;
        auto *translations = new KLocalizedContext(&view);
        translations->setTranslationDomain(QStringLiteral("kcm_screenbot_screensaver"));
        view.rootContext()->setContextObject(translations);
        view.rootContext()->setContextProperty(QStringLiteral("kcm"), &kcm);
        view.setSource(QUrl::fromLocalFile(QStringLiteral(SCREENBOT_SOURCE_DIR "/kcm/ui/main.qml")));
        QCOMPARE(view.status(), QQuickView::Ready);
        view.setResizeMode(QQuickView::SizeRootObjectToView);
        view.setColor(QApplication::palette().window().color());
        view.resize(1000, 900);
        view.show();
        QVERIFY(QTest::qWaitForWindowExposed(&view));
        const auto item = [&](const QString &name) { return view.rootObject()->findChild<QQuickItem *>(name); };
        QVERIFY(item(QStringLiteral("bobNameField")));
        QVERIFY(item(QStringLiteral("bobColorPreset")));
        QVERIFY(item(QStringLiteral("bobCustomColorButton")));
        QVERIFY(item(QStringLiteral("bobAccessory")));
        QVERIFY(item(QStringLiteral("seasonalEnabledSwitch")));
        QVERIFY(item(QStringLiteral("seasonalHalloweenSwitch")));
        QVERIFY(item(QStringLiteral("seasonalBirthdayMonth")));
        QVERIFY(item(QStringLiteral("seasonalBirthdayDay")));
        auto *seasonalSection = item(QStringLiteral("seasonalSection"));
        QVERIFY(seasonalSection);
        seasonalSection->setProperty("expanded", true);
        auto *seasonalMaster = item(QStringLiteral("seasonalEnabledSwitch"));
        auto *halloweenSwitch = item(QStringLiteral("seasonalHalloweenSwitch"));
        auto *birthdayMonth = item(QStringLiteral("seasonalBirthdayMonth"));
        QVERIFY(seasonalMaster->property("checked").toBool());
        QVERIFY(halloweenSwitch->property("enabled").toBool());
        kcm.setSeasonalEnabled(false);
        QVERIFY(!halloweenSwitch->property("enabled").toBool());
        QVERIFY(!birthdayMonth->property("enabled").toBool());
        QVERIFY(seasonalSection->property("modified").toBool());
        kcm.load();
        QVERIFY(seasonalMaster->property("checked").toBool());
        QVERIFY(halloweenSwitch->property("enabled").toBool());
        seasonalSection->setProperty("expanded", false);
        QVERIFY(view.rootObject()->findChild<QObject *>(QStringLiteral("bobColorDialog")));
        for (const auto &key : keys) {
            auto *section = item(key + QStringLiteral("Section"));
            auto *header = item(key + QStringLiteral("Header"));
            QVERIFY(section);
            QVERIFY(header);
            QCOMPARE(section->property("expanded").toBool(), key == QStringLiteral("theme"));
            QVERIFY(!section->property("summary").toString().isEmpty());
            auto *accessible = QAccessible::queryAccessibleInterface(header);
            QVERIFY(accessible);
            QVERIFY(accessible->state().expandable);
            QCOMPARE(accessible->state().expanded, key == QStringLiteral("theme"));
            QVERIFY(!accessible->text(QAccessible::Name).isEmpty());
        }
        auto *clock = item(QStringLiteral("clockSection"));
        auto *header = item(QStringLiteral("clockHeader"));
        header->forceActiveFocus();
        QTest::keyClick(&view, Qt::Key_Space);
        QVERIFY(clock->property("expanded").toBool());
        QTest::keyClick(&view, Qt::Key_Return);
        QVERIFY(!clock->property("expanded").toBool());
        QTest::keyClick(&view, Qt::Key_Right);
        QVERIFY(clock->property("expanded").toBool());
        QTest::keyClick(&view, Qt::Key_Left);
        QVERIFY(!clock->property("expanded").toBool());
        QTest::keyClick(&view, Qt::Key_Tab);
        QVERIFY(item(QStringLiteral("weatherHeader"))->hasActiveFocus());
        item(QStringLiteral("weatherSection"))->setProperty("expanded", true);
        QTest::qWait(300);
        auto *bobWeather = item(QStringLiteral("bobWeatherEnabledSwitch"));
        QVERIFY(bobWeather);
        QVERIFY(!bobWeather->property("enabled").toBool());
        kcm.setTheme(QStringLiteral("forest"));
        kcm.setLiveSkyEnabled(true);
        QCoreApplication::processEvents();
        QCOMPARE(kcm.theme(), QStringLiteral("forest"));
        QVERIFY(kcm.liveSkyEnabled());
        QVERIFY(bobWeather->property("enabled").toBool());
        QVERIFY(bobWeather->property("checked").toBool());
        const QString weatherEvidence = qEnvironmentVariable("SCREENBOT_EVIDENCE_DIR");
        if (!weatherEvidence.isEmpty())
            QVERIFY(view.grabWindow().save(weatherEvidence + QStringLiteral("/weather-live-enabled.png")));
        kcm.setBobWeatherEnabled(false);
        QVERIFY(!bobWeather->property("checked").toBool());
        QVERIFY(item(QStringLiteral("weatherSection"))->property("modified").toBool());
        if (!weatherEvidence.isEmpty())
            QVERIFY(view.grabWindow().save(weatherEvidence + QStringLiteral("/weather-live-disabled.png")));
        kcm.load();
        QVERIFY(bobWeather->property("checked").toBool());
        QVERIFY(!item(QStringLiteral("weatherSection"))->property("modified").toBool());
        kcm.setTheme(QStringLiteral("space"));
        QCoreApplication::processEvents();
        QVERIFY(!bobWeather->property("enabled").toBool());
        QVERIFY(bobWeather->property("checked").toBool());
        kcm.load();
        kcm.setClockFormat(QStringLiteral("24h"));
        QVERIFY(clock->property("modified").toBool());
        QVERIFY(clock->property("summary").toString().contains(QStringLiteral("24-hour")));
        QTest::qWait(100);
        QVERIFY(view.grabWindow().save(qEnvironmentVariable("SCREENBOT_EVIDENCE_DIR") + QStringLiteral("/unapplied-clock.png")));
        kcm.load();
        QVERIFY(!clock->property("modified").toBool());
        item(QStringLiteral("agentsSection"))->setProperty("expanded", true);
        kcm.setAgentDetectionMode(QStringLiteral("block"));
        QVERIFY(item(QStringLiteral("resetAgentChoiceButton"))->isEnabled());
        QVERIFY(QMetaObject::invokeMethod(item(QStringLiteral("resetAgentChoiceButton")), "clicked"));
        QCOMPARE(kcm.agentDetectionMode(), QStringLiteral("ask"));
        item(QStringLiteral("agentsSection"))->setProperty("expanded", false);
        item(QStringLiteral("bobosSection"))->setProperty("expanded", true);
        QVERIFY(item(QStringLiteral("bobosPreviewButton"))->isEnabled());
        kcm.setPhoneEnabled(false);
        QVERIFY(!item(QStringLiteral("bobosPreviewButton"))->isEnabled());
        kcm.setPhoneEnabled(true);
        item(QStringLiteral("bobosSection"))->setProperty("expanded", false);
        item(QStringLiteral("performanceSection"))->setProperty("expanded", true);
        QVERIFY(item(QStringLiteral("performanceMode")));
        QVERIFY(item(QStringLiteral("reduceMotion")));
        auto *burnIn = item(QStringLiteral("burnInProtection"));
        QVERIFY(burnIn);
        QCOMPARE(burnIn->property("count").toInt(), 3);
        QCOMPARE(burnIn->property("currentIndex").toInt(), 1);
        kcm.setPerformanceMode(QStringLiteral("smooth"));
        kcm.setBurnInProtection(QStringLiteral("strong"));
        QVERIFY(item(QStringLiteral("performanceSection"))->property("modified").toBool());
        QCOMPARE(item(QStringLiteral("performanceSection"))->property("summary").toString(), QStringLiteral("Smooth"));
        kcm.load();
        QCOMPARE(kcm.performanceMode(), QStringLiteral("balanced"));
        QVERIFY(!kcm.reduceMotion());
        QCOMPARE(kcm.burnInProtection(), QStringLiteral("standard"));
        item(QStringLiteral("performanceSection"))->setProperty("expanded", false);
        const QString evidence = qEnvironmentVariable("SCREENBOT_EVIDENCE_DIR");
        QVERIFY(!evidence.isEmpty());
        QDir().mkpath(evidence);
        for (const int width : {390, 768, 1440}) {
            view.resize(width, 900);
            QTest::qWait(300);
            QVERIFY(view.grabWindow().save(evidence + QString(QStringLiteral("/overview-%1.png")).arg(width)));
            for (const auto &key : keys) {
                for (const auto &other : keys) item(other + QStringLiteral("Section"))->setProperty("expanded", other == key);
                QTest::qWait(300);
                QVERIFY(view.grabWindow().save(evidence + QString(QStringLiteral("/%1-%2.png")).arg(key).arg(width)));
                QVERIFY(item(key + QStringLiteral("Header"))->width() <= width);
            }
            for (const auto &key : keys) item(key + QStringLiteral("Section"))->setProperty("expanded", true);
            QTest::qWait(300);
            QObject *flickable = view.rootObject()->property("flickable").value<QObject *>();
            QVERIFY(flickable);
            QVERIFY(flickable->property("contentHeight").toReal() > flickable->property("height").toReal());
            flickable->setProperty("contentY", flickable->property("contentHeight").toReal() - flickable->property("height").toReal());
            QTest::qWait(100);
            QVERIFY(view.grabWindow().save(evidence + QString(QStringLiteral("/all-open-end-%1.png")).arg(width)));
            for (const auto &key : keys) item(key + QStringLiteral("Section"))->setProperty("expanded", key == QStringLiteral("theme"));
            flickable->setProperty("contentY", 0);
        }
    }
};
int main(int argc, char **argv) {
    QTemporaryDir config;
    qputenv("HOME", config.path().toUtf8());
    qputenv("XDG_CONFIG_HOME", config.path().toUtf8());
    if (qEnvironmentVariableIsSet("SCREENBOT_TEST_DARK"))
        QFile::copy(QStringLiteral("/usr/share/color-schemes/BreezeDark.colors"), config.path() + QStringLiteral("/kdeglobals"));
    const QString data = config.path() + QStringLiteral("/data");
    QDir().mkpath(data + QStringLiteral("/screenbot-screensaver"));
    QFile::copy(QStringLiteral(SCREENBOT_SOURCE_DIR "/countries_and_cities.txt"), data + QStringLiteral("/screenbot-screensaver/countries_and_cities.txt"));
    qputenv("XDG_DATA_HOME", data.toUtf8());
    QApplication app(argc, argv);
    if (qEnvironmentVariableIsSet("SCREENBOT_TEST_DARK")) {
        QSettings colors(QStringLiteral("/usr/share/color-schemes/BreezeDark.colors"), QSettings::IniFormat);
        QPalette palette = app.palette();
        const auto color = [&](const QString &key) {
            const auto channels = colors.value(key).toStringList();
            return QColor(channels.value(0).toInt(), channels.value(1).toInt(), channels.value(2).toInt());
        };
        palette.setColor(QPalette::Window, color(QStringLiteral("Colors:Window/BackgroundNormal")));
        palette.setColor(QPalette::WindowText, color(QStringLiteral("Colors:Window/ForegroundNormal")));
        palette.setColor(QPalette::Base, color(QStringLiteral("Colors:View/BackgroundNormal")));
        palette.setColor(QPalette::Text, color(QStringLiteral("Colors:View/ForegroundNormal")));
        palette.setColor(QPalette::Button, color(QStringLiteral("Colors:Button/BackgroundNormal")));
        palette.setColor(QPalette::ButtonText, color(QStringLiteral("Colors:Button/ForegroundNormal")));
        palette.setColor(QPalette::Highlight, color(QStringLiteral("Colors:Selection/BackgroundNormal")));
        palette.setColor(QPalette::HighlightedText, color(QStringLiteral("Colors:Selection/ForegroundNormal")));
        app.setPalette(palette);
    }
    SectionsTest test;
    return QTest::qExec(&test, argc, argv);
}
#include "sections_test.moc"
