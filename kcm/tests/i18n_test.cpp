#include <KPluginMetaData>
#include <KQuickConfigModule>
#include <KQuickConfigModuleLoader>
#include <QApplication>
#include <QAccessible>
#include <QDir>
#include <QFile>
#include <QQuickItem>
#include <QQuickWindow>
#include <QSettings>
#include <QTemporaryDir>
#include <QTest>

class I18nTest : public QObject {
    Q_OBJECT
private Q_SLOTS:
    void installedLocaleAndSettings() {
        const QString plugin = qEnvironmentVariable("SCREENBOT_TEST_PLUGIN");
        const QString evidence = qEnvironmentVariable("SCREENBOT_EVIDENCE_DIR");
        QVERIFY2(!plugin.isEmpty(), "Set SCREENBOT_TEST_PLUGIN to the installed KCM .so");
        QVERIFY(!evidence.isEmpty());
        QVERIFY(QDir().mkpath(evidence));
        const auto result = KQuickConfigModuleLoader::loadModule(KPluginMetaData(plugin));
        QVERIFY2(result, qPrintable(result.errorString));
        std::unique_ptr<KQuickConfigModule> kcm(result.plugin);
        kcm->setProperty("advancedView", true);
        auto *root = kcm->mainUi();
        QVERIFY2(root, qPrintable(kcm->errorString()));
        QQuickWindow window;
        root->setParentItem(window.contentItem());
        const bool spanish = qEnvironmentVariable("LANGUAGE") == QLatin1String("es");
        const auto item = [&](const char *name) { return root->findChild<QQuickItem *>(QLatin1String(name)); };
        QCOMPARE(item("themeSection")->property("title").toString(), spanish ? QStringLiteral("Tema") : QStringLiteral("Theme"));
        QCOMPARE(item("clockSection")->property("title").toString(), spanish ? QStringLiteral("Reloj") : QStringLiteral("Clock"));
        QCOMPARE(item("factsSection")->property("title").toString(), spanish ? QStringLiteral("¿Sabías que?") : QStringLiteral("Did you know?"));
        QCOMPARE(item("appearanceSection")->property("title").toString(),
                 spanish ? QStringLiteral("Personalizar Bob") : QStringLiteral("Customize Bob"));
        QCOMPARE(item("themePreviewButton")->property("text").toString(), spanish ? QStringLiteral("Vista previa") : QStringLiteral("Preview"));
        auto *delay = item("bobosDelay");
        QVERIFY(delay);
        kcm->setProperty("bobosActivationDelay", 1);
        QCOMPARE(delay->property("displayText").toString(), spanish ? QStringLiteral("1 minuto") : QStringLiteral("1 minute"));
        kcm->setProperty("bobosActivationDelay", 3);
        QCOMPARE(delay->property("displayText").toString(), spanish ? QStringLiteral("3 minutos") : QStringLiteral("3 minutes"));
        kcm->save();
        const QString config = qEnvironmentVariable("XDG_CONFIG_HOME") + QStringLiteral("/screenbot-screensaver.ini");
        const auto saved = [&]() { QFile file(config); if (!file.open(QIODevice::ReadOnly)) return QByteArray(); return file.readAll(); };
        auto *media = item("nowPlayingEnabled");
        QVERIFY(media);
        QCOMPARE(kcm->property("nowPlayingEnabled").toBool(), false);
        const QByteArray mediaBefore = saved();
        media->setProperty("checked", true);
        QVERIFY(QMetaObject::invokeMethod(media, "toggled"));
        QVERIFY(kcm->needsSave());
        QVERIFY(kcm->property("modifiedSections").toStringList().contains(QStringLiteral("clock")));
        QCOMPARE(saved(), mediaBefore);
        QCOMPARE(media->property("text").toString(), spanish ? QStringLiteral("Mostrar el título y el artista") : QStringLiteral("Show media title and artist"));
        kcm->load();
        QVERIFY(!kcm->property("nowPlayingEnabled").toBool());
        QVERIFY(!kcm->needsSave());
        media->setProperty("checked", true);
        QVERIFY(QMetaObject::invokeMethod(media, "toggled"));
        kcm->save();
        kcm->load();
        QVERIFY(kcm->property("nowPlayingEnabled").toBool());
        QVERIFY(!kcm->needsSave());
        QSettings mediaSettings(config, QSettings::IniFormat);
        QVERIFY(mediaSettings.value(QStringLiteral("Screensaver/now_playing_enabled")).toBool());
        const QByteArray before = saved();
        QVERIFY(!before.isEmpty());
        auto *theme = item("themeChoice");
        QVERIFY(theme);
        QCOMPARE(theme->property("count").toInt(), 11);
        theme->setProperty("currentIndex", 4);
        QVERIFY(QMetaObject::invokeMethod(theme, "activated", Q_ARG(int, 4)));
        QVERIFY(kcm->needsSave());
        QCOMPARE(kcm->property("theme").toString(), QStringLiteral("forest"));
        QCOMPARE(saved(), before);
        kcm->load();
        QVERIFY(!kcm->needsSave());
        QCOMPARE(kcm->property("theme").toString(), QStringLiteral("random"));
        theme->setProperty("currentIndex", 4);
        QVERIFY(QMetaObject::invokeMethod(theme, "activated", Q_ARG(int, 4)));
        kcm->save();
        QVERIFY(!kcm->needsSave());
        QSettings persisted(config, QSettings::IniFormat);
        QCOMPARE(persisted.value(QStringLiteral("Screensaver/theme")).toString(), QStringLiteral("forest"));
        const QStringList newThemes{QStringLiteral("aurora"), QStringLiteral("ocean"), QStringLiteral("desert"), QStringLiteral("underwater")};
        for (qsizetype index = 0; index < newThemes.size(); ++index) {
            const int comboIndex = 6 + static_cast<int>(index);
            theme->setProperty("currentIndex", comboIndex);
            QVERIFY(QMetaObject::invokeMethod(theme, "activated", Q_ARG(int, comboIndex)));
            QVERIFY(kcm->needsSave());
            QCOMPARE(kcm->property("theme").toString(), newThemes.at(index));
            kcm->load();
            QCOMPARE(kcm->property("theme").toString(), QStringLiteral("forest"));
            QVERIFY(!kcm->needsSave());
        }
        theme->setProperty("currentIndex", 10);
        QVERIFY(QMetaObject::invokeMethod(theme, "activated", Q_ARG(int, 10)));
        QCOMPARE(kcm->property("theme").toString(), QStringLiteral("photos"));
        QVERIFY(kcm->needsSave());
        kcm->load();
        QCOMPARE(kcm->property("theme").toString(), QStringLiteral("forest"));
        QVERIFY(!kcm->needsSave());
        const QStringList keys{QStringLiteral("theme"), QStringLiteral("appearance"), QStringLiteral("clock"), QStringLiteral("weather"), QStringLiteral("facts"), QStringLiteral("liveSky"), QStringLiteral("agents"), QStringLiteral("bobos"), QStringLiteral("performance"), QStringLiteral("lock")};
        window.setColor(QApplication::palette().window().color());
        window.show();
        QVERIFY(QTest::qWaitForWindowExposed(&window));
        for (const int width : {390, 1440}) {
            window.resize(width, 900);
            root->setWidth(width);
            root->setHeight(900);
            for (const QString &key : keys) {
                for (const QString &other : keys) root->findChild<QQuickItem *>(other + QStringLiteral("Section"))->setProperty("expanded", other == key);
                auto *flickable = root->property("flickable").value<QObject *>();
                QVERIFY(flickable);
                flickable->setProperty("contentY", 0);
                QTest::qWait(300);
                if (key == QLatin1String("clock")) {
                    media->forceActiveFocus();
                    QVERIFY(media->hasActiveFocus());
                    auto *accessible = QAccessible::queryAccessibleInterface(media);
                    QVERIFY(accessible);
                    QCOMPARE(accessible->text(QAccessible::Name), spanish ? QStringLiteral("Mostrar lo que se está reproduciendo") : QStringLiteral("Show what's playing"));
                    QTest::keyClick(&window, Qt::Key_Space);
                    QVERIFY(!kcm->property("nowPlayingEnabled").toBool());
                    QVERIFY(kcm->needsSave());
                    QTest::qWait(50);
                    QVERIFY(window.grabWindow().save(evidence + QStringLiteral("/clock-media-off-%1.png").arg(width)));
                    QTest::keyClick(&window, Qt::Key_Space);
                    QVERIFY(kcm->property("nowPlayingEnabled").toBool());
                    QVERIFY(!kcm->needsSave());
                    QTest::qWait(50);
                }
                QVERIFY(window.grabWindow().save(evidence + QStringLiteral("/%1-%2.png").arg(key).arg(width)));
                flickable->setProperty("contentY", qMax(0.0, flickable->property("contentHeight").toDouble() - flickable->property("height").toDouble()));
                QTest::qWait(100);
                QVERIFY(window.grabWindow().save(evidence + QStringLiteral("/%1-%2-end.png").arg(key).arg(width)));
            }
        }
        QFile artifact(evidence + QStringLiteral("/applied-settings.ini"));
        QVERIFY(artifact.open(QIODevice::WriteOnly));
        const auto contents = saved();
        QCOMPARE(artifact.write(contents), contents.size());
        root->setParentItem(nullptr);
    }
};

int main(int argc, char **argv) {
    QTemporaryDir config;
    qputenv("XDG_CONFIG_HOME", config.path().toUtf8());
    if (qEnvironmentVariableIsSet("SCREENBOT_TEST_DARK"))
        QFile::copy(QStringLiteral("/usr/share/color-schemes/BreezeDark.colors"), config.path() + QStringLiteral("/kdeglobals"));
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
    I18nTest test;
    return QTest::qExec(&test, argc, argv);
}
#include "i18n_test.moc"
