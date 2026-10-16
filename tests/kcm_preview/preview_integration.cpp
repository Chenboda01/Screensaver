#include <KPluginFactory>
#include <KQuickConfigModule>
#include <QGuiApplication>
#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QQuickView>
#include <QQuickItem>
#include <QScreen>
#include <QQmlContext>
#include <QSettings>
#include <QTemporaryDir>
#include <QTest>
#include <QElapsedTimer>
#include <iostream>

#define REQUIRE(condition) do { if (!(condition)) { std::cerr << "FAIL " << #condition << '\n'; return 1; } } while (false)

int main(int argc, char **argv) {
    QTemporaryDir home;
    qputenv("HOME", home.path().toUtf8());
    qputenv("XDG_CONFIG_HOME", (home.path() + "/.config").toUtf8());
    QDir().mkpath(home.path() + "/tmp");
    qputenv("TMPDIR", (home.path() + "/tmp").toUtf8());
    QGuiApplication app(argc, argv);
    const QString source = qEnvironmentVariable("SCREENBOT_SOURCE");
    const QString evidence = qEnvironmentVariable("SCREENBOT_PREVIEW_EVIDENCE");
    const QString configPath = home.path() + "/.config/screenbot-screensaver.ini";
    {
        QSettings config(configPath, QSettings::IniFormat);
        config.setValue("Screensaver/theme", "space");
        config.sync();
    }
    QFile saved(configPath);
    REQUIRE(saved.open(QIODevice::ReadOnly));
    const QByteArray before = saved.readAll();
    saved.close();
    const auto loaded = KPluginFactory::instantiatePlugin<KQuickConfigModule>(KPluginMetaData(QString::fromLocal8Bit(argv[1])));
    REQUIRE(loaded.plugin);
    auto *kcm = loaded.plugin;
    REQUIRE(QMetaObject::invokeMethod(kcm, "previewTheme", Q_ARG(QQuickItem *, nullptr)));
    REQUIRE(!kcm->property("previewError").toString().isEmpty());
    REQUIRE(!kcm->property("previewRunning").toBool());
    std::cout << "PASS missing installation reports an error\n";

    const QString install = home.path() + "/ScreenBot/screensaver";
    REQUIRE(QDir().mkpath(install));
    REQUIRE(QFile::copy(source + "/tests/kcm_preview/preview_probe.py", install + "/screensaver.py"));
    kcm->setProperty("theme", "forest");
    kcm->setProperty("clockPosition", "bottom-right");
    kcm->setProperty("clockFontSize", 24);
    kcm->setProperty("showDate", true);
    kcm->setProperty("rainEnabled", true);
    kcm->setProperty("liveSkyEnabled", true);
    kcm->setProperty("passwordLock", true);
    kcm->setProperty("showTimer", true);
    REQUIRE(kcm->needsSave());
    QQuickView view;
    view.setResizeMode(QQuickView::SizeRootObjectToView);
    view.rootContext()->setContextProperty("kcm", kcm);
    view.setSource(QUrl::fromLocalFile(source + "/kcm/ui/main.qml"));
    REQUIRE(view.status() == QQuickView::Ready);
    view.resize(1000, 900);
    view.show();
    QTest::qWait(200);
    REQUIRE(view.grabWindow().save(evidence + "/settings-preview-error.png"));
    QElapsedTimer deadline;
    deadline.start();
    auto *button = view.rootObject()->findChild<QQuickItem *>("themePreviewButton");
    REQUIRE(button);
    QTest::mouseClick(&view, Qt::LeftButton, Qt::NoModifier,
                     button->mapToScene(QPointF(button->width()/2, button->height()/2)).toPoint());
    REQUIRE(kcm->property("previewRunning").toBool());
    REQUIRE(kcm->property("previewError").toString().isEmpty());
    REQUIRE(QMetaObject::invokeMethod(kcm, "previewTheme", Q_ARG(QQuickItem *, nullptr)));
    while (kcm->property("previewRunning").toBool() && deadline.elapsed() < 10000) QTest::qWait(10);
    REQUIRE(!kcm->property("previewRunning").toBool());
    REQUIRE(kcm->property("previewError").toString().isEmpty());
    REQUIRE(deadline.elapsed() < 1500);
    std::cout << "button_to_frame_and_close_ms=" << deadline.elapsed() << '\n';
    REQUIRE(kcm->needsSave());
    QFile receipt(evidence + "/launches.jsonl");
    REQUIRE(receipt.open(QIODevice::ReadOnly));
    const auto lines = receipt.readAll().trimmed().split('\n');
    REQUIRE(lines.size() == 1);
    const auto result = QJsonDocument::fromJson(lines.first()).object();
    REQUIRE(result["full_screen"].toBool());
    REQUIRE(result["screen_name"].toString() == view.screen()->name());
    REQUIRE(result["theme"].toString() == "forest");
    REQUIRE(result["clock_position"].toString() == "bottom-right");
    REQUIRE(result["live_sky_enabled"].toBool());
    REQUIRE(!result["password_lock"].toBool());
    REQUIRE(!result["show_timer"].toBool());
    REQUIRE(!result["bobos_enabled"].toBool());
    REQUIRE(result["first_frame_seconds"].toDouble() < 1.0);
    REQUIRE(!QFile::exists(result["temporary_path"].toString()));
    REQUIRE(saved.open(QIODevice::ReadOnly));
    REQUIRE(saved.readAll() == before);
    std::cout << "PASS staged values, full screen under one second, input exit, singleton, no lock/countdown/BobOS, unchanged saved config, temporary cleanup\n";
    kcm->load();
    REQUIRE(kcm->property("theme").toString() == "space");
    REQUIRE(!kcm->needsSave());
    std::cout << "PASS discard restores saved values\n";
    QTest::qWait(50);
    REQUIRE(view.grabWindow().save(evidence + "/settings-preview-button.png"));
    REQUIRE(QMetaObject::invokeMethod(kcm, "previewBobOS", Q_ARG(bool, false)));
    deadline.restart();
    while (kcm->property("previewRunning").toBool() && deadline.elapsed() < 10000) QTest::qWait(10);
    REQUIRE(!kcm->property("previewRunning").toBool());
    REQUIRE(kcm->property("previewError").toString().isEmpty());
    receipt.seek(0);
    const auto adventures = receipt.readAll().trimmed().split('\n');
    REQUIRE(adventures.size() == 2);
    const auto adventure = QJsonDocument::fromJson(adventures.last()).object();
    REQUIRE(adventure["bobos_enabled"].toBool());
    REQUIRE(!adventure["password_lock"].toBool());
    REQUIRE(!QFile::exists(adventure["temporary_path"].toString()));
    std::cout << "PASS full BobOS preview still starts without locking\n";
    kcm->setProperty("theme", "city");
    kcm->save();
    REQUIRE(!kcm->needsSave());
    QSettings applied(configPath, QSettings::IniFormat);
    REQUIRE(applied.value("Screensaver/theme").toString() == "city");
    std::cout << "PASS explicit Apply persists changes\n";
    QFile broken(install + "/screensaver.py");
    REQUIRE(broken.open(QIODevice::WriteOnly | QIODevice::Truncate));
    broken.write("raise SystemExit(1)\n");
    broken.close();
    REQUIRE(QMetaObject::invokeMethod(kcm, "previewTheme", Q_ARG(QQuickItem *, nullptr)));
    deadline.restart();
    while (kcm->property("previewRunning").toBool() && deadline.elapsed() < 10000) QTest::qWait(10);
    REQUIRE(!kcm->property("previewRunning").toBool());
    REQUIRE(!kcm->property("previewError").toString().isEmpty());
    QTest::qWait(50);
    REQUIRE(QDir(home.path() + "/tmp").entryList({"screenbot-preview-*"}, QDir::Files).isEmpty());
    std::cout << "PASS early process failure reports an error and removes temporary config\n";
    delete kcm;
    return 0;
}
