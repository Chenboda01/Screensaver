#include "screenbotkcm.h"
#include <KPluginMetaData>
#include <KLocalizedContext>
#include <QAccessible>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPalette>
#include <QColor>
#include <QApplication>
#include <QFile>
#include <QSettings>
#include <QStandardPaths>
#include <QTemporaryDir>
#include <QMetaProperty>
#include <QQmlContext>
#include <QQuickView>
#include <QQuickItem>
#include <QTest>
#include <functional>

class PresetsTest : public QObject {
    Q_OBJECT
    QString path() const { return QStandardPaths::writableLocation(QStandardPaths::ConfigLocation) + QStringLiteral("/screenbot-screensaver.ini"); }
    QByteArray bytes() const { QFile f(path()); if (!f.open(QIODevice::ReadOnly)) return {}; return f.readAll(); }
    QVariantMap values(ScreenBotKcm &kcm) {
        QVariantMap result;
        const auto *meta = kcm.metaObject();
        for (int i = meta->propertyOffset(); i < meta->propertyCount(); ++i) {
            const auto property = meta->property(i);
            if (property.isWritable()) result.insert(QString::fromLatin1(property.name()), property.read(&kcm));
        }
        return result;
    }
private Q_SLOTS:
    void init() {
        QFile::remove(path());
        QFile::remove(QStandardPaths::writableLocation(QStandardPaths::ConfigLocation) + QStringLiteral("/screenbot-kcm-state.ini"));
    }
    void presetsPreservePrivateAndSafetySettings() {
        const QStringList allowed{QStringLiteral("theme"), QStringLiteral("liveSkyEnabled"), QStringLiteral("liveSkyConditions"),
            QStringLiteral("bobWeatherEnabled"), QStringLiteral("factsEnabled"), QStringLiteral("seasonalEnabled"),
            QStringLiteral("phoneEnabled"), QStringLiteral("bobosEnabled"), QStringLiteral("ambientSoundEnabled"),
            QStringLiteral("reduceMotion"), QStringLiteral("performanceMode"), QStringLiteral("rainEnabled"),
            QStringLiteral("snowEnabled"), QStringLiteral("thunderstormsEnabled"), QStringLiteral("fogEnabled"),
            QStringLiteral("shootingStarsEnabled"), QStringLiteral("clockVisible")};
        for (const auto &preset : {"calm", "fun", "live-sky", "photos", "battery-saver"}) {
            ScreenBotKcm kcm(nullptr, KPluginMetaData());
            kcm.setPasswordLock(true); kcm.setLockMinutes(17); kcm.setShowTimer(true);
            kcm.setAgentDetectionMode(QStringLiteral("block")); kcm.setAgentPromptTimeout(35);
            kcm.setAgentPromptTimeoutAction(QStringLiteral("cancel")); kcm.setAgentStatusEnabled(false);
            kcm.setLiveSkyLocation(QStringLiteral("Paris, France"));
            QCOMPARE(kcm.liveSkyLocation(), QStringLiteral("Paris, France"));
            kcm.setBobName(QStringLiteral("Pixel")); kcm.setPhotoFolder(QStringLiteral("/tmp/my-private-photos"));
            kcm.setSeasonalBirthdayDate(QStringLiteral("02-29")); kcm.setSeasonalBirthdayName(QStringLiteral("User"));
            kcm.setSeasonalBirthdayEnabled(true);
            kcm.save();
            const auto before = values(kcm); const auto persisted = bytes();
            kcm.applyPreset(QString::fromLatin1(preset));
            QCOMPARE(kcm.preset(), QString::fromLatin1(preset));
            const auto after = values(kcm);
            for (auto it = before.cbegin(); it != before.cend(); ++it)
                if (!allowed.contains(it.key())) QCOMPARE(after.value(it.key()), it.value());
            QCOMPARE(bytes(), persisted);
            QVERIFY(kcm.needsSave());
            kcm.save();
            ScreenBotKcm reopened(nullptr, KPluginMetaData());
            QCOMPARE(reopened.preset(), QString::fromLatin1(preset));
            QCOMPARE(values(reopened), after);
        }
    }
    void everyBooleanManualSettingMarksCustom() {
        ScreenBotKcm kcm(nullptr, KPluginMetaData());
        const auto *meta = kcm.metaObject();
        for (int i = meta->propertyOffset(); i < meta->propertyCount(); ++i) {
            const auto property = meta->property(i);
            if (!property.isWritable() || property.metaType().id() != QMetaType::Bool || QByteArray(property.name()) == "advancedView") continue;
            kcm.applyPreset(QStringLiteral("fun"));
            QVERIFY(property.write(&kcm, !property.read(&kcm).toBool()));
            QCOMPARE(kcm.preset(), QStringLiteral("custom"));
        }
    }
    void presetPreviewUsesStagedValues() {
        const QString evidence = qEnvironmentVariable("SCREENBOT_EVIDENCE_DIR");
        QVERIFY(QDir().mkpath(evidence));
        qputenv("SCREENBOT_SOURCE", SCREENBOT_SOURCE_DIR);
        qputenv("SCREENBOT_PREVIEW_EVIDENCE", evidence.toUtf8());
        const QString install = QDir::homePath() + QStringLiteral("/ScreenBot/screensaver");
        QVERIFY(QDir().mkpath(install));
        for (const QString &file : {QStringLiteral("start.sh"), QStringLiteral("python-runtime.sh")})
            QVERIFY(QFile::copy(QStringLiteral(SCREENBOT_SOURCE_DIR "/") + file, install + QLatin1Char('/') + file));
        QVERIFY(QFile::copy(QStringLiteral(SCREENBOT_SOURCE_DIR "/tests/kcm_preview/preview_probe.py"), install + QStringLiteral("/screensaver.py")));
        ScreenBotKcm kcm(nullptr, KPluginMetaData());
        kcm.setPasswordLock(true); kcm.save(); const auto saved = bytes();
        kcm.applyPreset(QStringLiteral("battery-saver")); kcm.previewTheme();
        QVERIFY(kcm.previewRunning()); QTRY_VERIFY_WITH_TIMEOUT(!kcm.previewRunning(), 10000);
        QVERIFY2(kcm.previewError().isEmpty(), qPrintable(kcm.previewError()));
        QFile receipt(evidence + QStringLiteral("/launches.jsonl")); QVERIFY(receipt.open(QIODevice::ReadOnly));
        const auto launch = QJsonDocument::fromJson(receipt.readAll().trimmed().split('\n').last()).object();
        const auto config = launch[QStringLiteral("config")].toObject();
        QCOMPARE(config[QStringLiteral("preset")].toString(), QStringLiteral("battery-saver"));
        QCOMPARE(config[QStringLiteral("performance_mode")].toString(), QStringLiteral("battery-saver"));
        QCOMPARE(config[QStringLiteral("reduce_motion")].toString(), QStringLiteral("true"));
        QVERIFY(!launch[QStringLiteral("password_lock")].toBool());
        QVERIFY(!QFile::exists(launch[QStringLiteral("temporary_path")].toString()));
        QCOMPARE(bytes(), saved); QVERIFY(kcm.passwordLock()); QVERIFY(kcm.needsSave());
    }
    void manualChangeAndResetDefaults() {
        ScreenBotKcm kcm(nullptr, KPluginMetaData());
        kcm.applyPreset(QStringLiteral("calm")); kcm.save();
        const auto saved = bytes();
        kcm.setClockVisible(false);
        QCOMPARE(kcm.preset(), QStringLiteral("custom"));
        QVERIFY(kcm.reduceMotion()); QVERIFY(!kcm.bobosEnabled());
        QCOMPARE(bytes(), saved);
        kcm.load(); QCOMPARE(kcm.preset(), QStringLiteral("calm")); QVERIFY(kcm.clockVisible()); QVERIFY(!kcm.needsSave());
        kcm.defaults(); QCOMPARE(kcm.preset(), QStringLiteral("custom")); QVERIFY(kcm.bobosEnabled()); QVERIFY(!kcm.reduceMotion());
        QCOMPARE(bytes(), saved); QVERIFY(kcm.needsSave());
        kcm.load(); QCOMPARE(kcm.preset(), QStringLiteral("calm"));
        kcm.applyPreset(QStringLiteral("fun")); kcm.setBobName(QStringLiteral("Manual"));
        QCOMPARE(kcm.preset(), QStringLiteral("custom"));
        kcm.applyPreset(QStringLiteral("fun")); kcm.setPasswordLock(!kcm.passwordLock());
        QCOMPARE(kcm.preset(), QStringLiteral("custom"));
    }
    void upgradeDoesNotWriteOrChangeExistingValues() {
        ScreenBotKcm original(nullptr, KPluginMetaData());
        original.setTheme(QStringLiteral("underwater")); original.setClockVisible(false);
        original.setAgentDetectionMode(QStringLiteral("block")); original.setAmbientSoundVolume(63);
        original.setBobName(QStringLiteral("Existing")); original.save();
        { QSettings cfg(path(), QSettings::IniFormat); cfg.remove(QStringLiteral("Screensaver/preset")); cfg.sync(); }
        QFile::remove(QStandardPaths::writableLocation(QStandardPaths::ConfigLocation) + QStringLiteral("/screenbot-kcm-state.ini"));
        const auto saved = bytes();
        const auto existing = values(original);
        ScreenBotKcm upgraded(nullptr, KPluginMetaData());
        auto upgradedValues = values(upgraded); upgradedValues.remove(QStringLiteral("advancedView"));
        auto expected = existing; expected.remove(QStringLiteral("advancedView"));
        QCOMPARE(upgradedValues, expected); QCOMPARE(bytes(), saved);
        QCOMPARE(upgraded.preset(), QStringLiteral("custom")); QVERIFY(upgraded.advancedView()); QVERIFY(!upgraded.needsSave());
    }
    void emptyActivationExposesAdvancedSearch() {
        ScreenBotKcm kcm(nullptr, KPluginMetaData());
        QVERIFY(!kcm.advancedView());
        kcm.activationRequested({});
        QVERIFY(kcm.advancedView()); QVERIFY(!kcm.needsSave());
        QVERIFY(kcm.requestedSection().isEmpty());
    }
    void initialSectionActivation() {
        ScreenBotKcm kcm(nullptr, KPluginMetaData(), {QStringLiteral("facts")});
        QVERIFY(kcm.advancedView()); QCOMPARE(kcm.requestedSection(), QStringLiteral("facts"));
        QVERIFY(kcm.sectionExpanded(QStringLiteral("facts"))); QVERIFY(!kcm.needsSave());
    }
    void simpleCardsKeyboardAndAdvancedNavigation() {
        ScreenBotKcm kcm(nullptr, KPluginMetaData());
        QVERIFY(!kcm.advancedView());
        QQuickView view;
        auto *translations = new KLocalizedContext(&view);
        translations->setTranslationDomain(QStringLiteral("kcm_screenbot_screensaver"));
        view.rootContext()->setContextObject(translations);
        view.rootContext()->setContextProperty(QStringLiteral("kcm"), &kcm);
        view.setSource(QUrl::fromLocalFile(QStringLiteral(SCREENBOT_SOURCE_DIR "/kcm/ui/main.qml")));
        QCOMPARE(view.status(), QQuickView::Ready);
        view.setResizeMode(QQuickView::SizeRootObjectToView); view.setColor(QApplication::palette().window().color()); view.resize(1000, 900); view.show();
        QVERIFY(QTest::qWaitForWindowExposed(&view));
        std::function<QQuickItem *(QQuickItem *, const QString &)> search;
        search = [&](QQuickItem *item, const QString &name) -> QQuickItem * {
            if (item->objectName() == name) return item;
            for (auto *child : item->childItems()) if (auto *found = search(child, name)) return found;
            return nullptr;
        };
        auto find = [&](const char *name) { return search(view.rootObject(), QString::fromLatin1(name)); };
        QVERIFY(find("simpleSettings")->isVisible()); QVERIFY(!find("weatherSection")->isVisible());
        for (const auto *name : {"calm", "fun", "live-sky", "photos", "battery-saver"}) {
            auto *card = find(qPrintable(QStringLiteral("preset-") + QString::fromLatin1(name)));
            QVERIFY(card); QVERIFY(card->isVisible());
            auto *accessible = QAccessible::queryAccessibleInterface(card);
            QVERIFY(accessible); QVERIFY(!accessible->text(QAccessible::Name).isEmpty());
        }
        auto *card = find("preset-fun"); card->forceActiveFocus(); QTest::keyClick(&view, Qt::Key_Space);
        QCOMPARE(kcm.preset(), QStringLiteral("fun")); QVERIFY(kcm.bobosEnabled());
        QVERIFY(find("simpleSettings")->isVisible());
        const auto evidence = qEnvironmentVariable("SCREENBOT_EVIDENCE_DIR"); QVERIFY(!evidence.isEmpty()); QDir().mkpath(evidence);
        QTest::qWait(300); QVERIFY(view.grabWindow().save(evidence + QStringLiteral("/simple.png")));
        view.resize(640, 900); QTest::qWait(300);
        QVERIFY(view.grabWindow().save(evidence + QStringLiteral("/simple-narrow.png")));
        view.resize(1000, 900);
        auto *searchField = find("settingsSearch"); QVERIFY(searchField); QVERIFY(searchField->isVisible());
        searchField->setProperty("text", QStringLiteral("Ambient")); QTest::qWait(100);
        auto *result = find("search-result-weather"); QVERIFY(result); QVERIFY(result->isVisible());
        result->forceActiveFocus(); QTest::keyClick(&view, Qt::Key_Space); QTest::qWait(300);
        QVERIFY(kcm.advancedView()); QVERIFY(find("weatherSection")->isVisible());
        auto *flickable = view.rootObject()->property("flickable").value<QObject *>();
        QVERIFY(flickable); QVERIFY(flickable->property("contentY").toReal() > 0);
        QVERIFY(find("weatherSection")->property("expanded").toBool()); QVERIFY(!find("simpleSettings")->isVisible());
        QVERIFY(view.grabWindow().save(evidence + QStringLiteral("/advanced-weather.png")));
        QCOMPARE(kcm.requestedSection(), QStringLiteral("weather"));
        searchField->setProperty("text", QString());
        kcm.setAdvancedView(false); card = find("preset-photos"); card->forceActiveFocus(); QTest::keyClick(&view, Qt::Key_Space);
        QVERIFY(kcm.advancedView()); QCOMPARE(kcm.theme(), QStringLiteral("photos"));
        QCOMPARE(kcm.requestedSection(), QStringLiteral("theme"));
        QVERIFY(find("presetInputGuidance")->isVisible());
        QTest::qWait(300); QVERIFY(view.grabWindow().save(evidence + QStringLiteral("/photo-guidance.png")));
        card = find("preset-live-sky"); card->forceActiveFocus(); QTest::keyClick(&view, Qt::Key_Space);
        QTest::qWait(300);
        QCOMPARE(kcm.requestedSection(), QStringLiteral("liveSky"));
        QVERIFY(kcm.liveSkyLocation().isEmpty());
        QVERIFY(find("liveSkySetupGuidance")->isVisible());
        QVERIFY(find("citySearch")->isVisible());
        QVERIFY(view.grabWindow().save(evidence + QStringLiteral("/city-guidance.png")));
    }
};

int main(int argc, char **argv) {
    QTemporaryDir home;
    qputenv("HOME", home.path().toUtf8()); qputenv("XDG_CONFIG_HOME", (home.path() + QStringLiteral("/config")).toUtf8());
    qputenv("XDG_DATA_HOME", (home.path() + QStringLiteral("/share")).toUtf8());
    QDir().mkpath(home.path() + QStringLiteral("/share/screenbot-screensaver"));
    QFile catalog(home.path() + QStringLiteral("/share/screenbot-screensaver/countries_and_cities.txt"));
    if (!catalog.open(QIODevice::WriteOnly)) return 1;
    catalog.write("France, Paris\n"); catalog.close();
    if (qEnvironmentVariableIsSet("SCREENBOT_TEST_DARK")) {
        QDir().mkpath(home.path() + QStringLiteral("/config"));
        QFile::copy(QStringLiteral("/usr/share/color-schemes/BreezeDark.colors"), home.path() + QStringLiteral("/config/kdeglobals"));
    }
    QApplication app(argc, argv);
    if (qEnvironmentVariableIsSet("SCREENBOT_TEST_DARK")) {
        QSettings colors(QStringLiteral("/usr/share/color-schemes/BreezeDark.colors"), QSettings::IniFormat);
        QPalette palette = app.palette();
        const auto color = [&](const QString &key) {
            const auto values = colors.value(key).toStringList();
            return QColor(values.value(0).toInt(), values.value(1).toInt(), values.value(2).toInt());
        };
        palette.setColor(QPalette::Window, color(QStringLiteral("Colors:Window/BackgroundNormal")));
        palette.setColor(QPalette::WindowText, color(QStringLiteral("Colors:Window/ForegroundNormal")));
        palette.setColor(QPalette::Base, color(QStringLiteral("Colors:View/BackgroundNormal")));
        palette.setColor(QPalette::Text, color(QStringLiteral("Colors:View/ForegroundNormal")));
        palette.setColor(QPalette::Button, color(QStringLiteral("Colors:Button/BackgroundNormal")));
        palette.setColor(QPalette::ButtonText, color(QStringLiteral("Colors:Button/ForegroundNormal")));
        app.setPalette(palette);
    }
    PresetsTest test; return QTest::qExec(&test, argc, argv);
}
#include "presets_test.moc"
