#include "screenbotkcm.h"
#include <KPluginMetaData>
#include <QApplication>
#include <QDir>
#include <QFile>
#include <QPalette>
#include <QQmlContext>
#include <QQuickItem>
#include <QQuickView>
#include <KLocalizedContext>
#include <QSettings>
#include <QStandardPaths>
#include <QTemporaryDir>
#include <QTest>

class AgentPromptTest : public QObject {
    Q_OBJECT
    QString configPath() const {
        return QStandardPaths::writableLocation(QStandardPaths::ConfigLocation)
            + QStringLiteral("/screenbot-screensaver.ini");
    }
    QByteArray savedBytes() const {
        QFile file(configPath());
        if (!file.open(QIODevice::ReadOnly)) return {};
        return file.readAll();
    }
private Q_SLOTS:
    void init() {
        QFile::remove(configPath());
    }
    void defaultsApplyDiscardAndReopen() {
        ScreenBotKcm kcm(nullptr, KPluginMetaData());
        QCOMPARE(kcm.agentPromptTimeout(), 10);
        QCOMPARE(kcm.agentPromptTimeoutAction(), QStringLiteral("start"));
        kcm.setPasswordLock(true);
        kcm.save();
        const auto before = savedBytes();
        QVERIFY(!before.isEmpty());

        kcm.setAgentPromptTimeout(37);
        kcm.setAgentPromptTimeoutAction(QStringLiteral("cancel"));

        QVERIFY(kcm.needsSave());
        QCOMPARE(kcm.modifiedSections(), QStringList{QStringLiteral("agents")});
        QCOMPARE(savedBytes(), before);
        kcm.load();
        QCOMPARE(kcm.agentPromptTimeout(), 10);
        QCOMPARE(kcm.agentPromptTimeoutAction(), QStringLiteral("start"));
        QVERIFY(!kcm.needsSave());
        kcm.setAgentPromptTimeout(37);
        kcm.setAgentPromptTimeoutAction(QStringLiteral("cancel"));
        kcm.save();
        QVERIFY(!kcm.needsSave());
        ScreenBotKcm reopened(nullptr, KPluginMetaData());
        QCOMPARE(reopened.agentPromptTimeout(), 37);
        QCOMPARE(reopened.agentPromptTimeoutAction(), QStringLiteral("cancel"));
        QVERIFY(reopened.passwordLock());
        QSettings persisted(configPath(), QSettings::IniFormat);
        QCOMPARE(persisted.value(QStringLiteral("Screensaver/agent_prompt_timeout_seconds")).toInt(), 37);
        QCOMPARE(persisted.value(QStringLiteral("Screensaver/agent_prompt_timeout_action")).toString(), QStringLiteral("cancel"));
        const QString evidence = qEnvironmentVariable("SCREENBOT_EVIDENCE_DIR");
        if (!evidence.isEmpty()) {
            QVERIFY(QDir().mkpath(evidence));
            const QString snapshot = evidence + QStringLiteral("/applied-settings.ini");
            QFile::remove(snapshot);
            QVERIFY(QFile::copy(configPath(), snapshot));
        }
    }
    void neverPersistsWithoutChangingAction() {
        ScreenBotKcm kcm(nullptr, KPluginMetaData());
        kcm.setAgentPromptTimeoutAction(QStringLiteral("cancel"));
        kcm.setAgentPromptTimeout(0);

        kcm.save();

        ScreenBotKcm reopened(nullptr, KPluginMetaData());
        QCOMPARE(reopened.agentPromptTimeout(), 0);
        QCOMPARE(reopened.agentPromptTimeoutAction(), QStringLiteral("cancel"));
    }
    void statusBadgePreferenceAppliesAndDiscards() {
        ScreenBotKcm kcm(nullptr, KPluginMetaData());
        QVERIFY(kcm.agentStatusEnabled());
        kcm.setAgentStatusEnabled(false);
        QVERIFY(kcm.needsSave());
        QCOMPARE(kcm.modifiedSections(), QStringList{QStringLiteral("agents")});
        kcm.load();
        QVERIFY(kcm.agentStatusEnabled());
        QVERIFY(!kcm.needsSave());

        kcm.setAgentStatusEnabled(false);
        kcm.save();
        ScreenBotKcm reopened(nullptr, KPluginMetaData());
        QVERIFY(!reopened.agentStatusEnabled());
        QSettings persisted(configPath(), QSettings::IniFormat);
        QVERIFY(!persisted.value(QStringLiteral("Screensaver/agent_status_enabled")).toBool());
    }
    void invalidSettings_data() {
        QTest::addColumn<QVariant>("input");
        QTest::addColumn<int>("expected");
        QTest::newRow("malformed") << QVariant(QStringLiteral("bad")) << 10;
        QTest::newRow("below-range") << QVariant(-1) << 5;
        QTest::newRow("above-range") << QVariant(500) << 120;
        QTest::newRow("never") << QVariant(0) << 0;
    }
    void invalidSettings() {
        QFETCH(QVariant, input);
        QFETCH(int, expected);
        QSettings config(configPath(), QSettings::IniFormat);
        config.setValue(QStringLiteral("Screensaver/agent_prompt_timeout_seconds"), input);
        config.setValue(QStringLiteral("Screensaver/agent_prompt_timeout_action"), QStringLiteral("invalid"));
        config.sync();

        ScreenBotKcm kcm(nullptr, KPluginMetaData());

        QCOMPARE(kcm.agentPromptTimeout(), expected);
        QCOMPARE(kcm.agentPromptTimeoutAction(), QStringLiteral("start"));
        QVERIFY(!kcm.needsSave());
    }
    void nativeControlsAndCaptures() {
        ScreenBotKcm kcm(nullptr, KPluginMetaData());
        kcm.save();
        const auto before = savedBytes();
        kcm.setSectionExpanded(QStringLiteral("theme"), false);
        kcm.setSectionExpanded(QStringLiteral("agents"), true);
        kcm.setAdvancedView(true);
        QQuickView view;
        auto *translations = new KLocalizedContext(&view);
        translations->setTranslationDomain(QStringLiteral("kcm_screenbot_screensaver"));
        view.rootContext()->setContextObject(translations);
        view.rootContext()->setContextProperty(QStringLiteral("kcm"), &kcm);
        view.setSource(QUrl::fromLocalFile(QStringLiteral(SCREENBOT_SOURCE_DIR "/kcm/ui/main.qml")));
        QCOMPARE(view.status(), QQuickView::Ready);
        view.setResizeMode(QQuickView::SizeRootObjectToView);
        view.setColor(QApplication::palette().window().color());
        view.resize(1000, 1000);
        view.show();
        QVERIFY(QTest::qWaitForWindowExposed(&view));
        const auto item = [&](const char *name) { return view.rootObject()->findChild<QQuickItem *>(QString::fromLatin1(name)); };
        auto *timeout = item("agentPromptTimeout");
        auto *action = item("agentPromptTimeoutAction");
        auto *never = item("agentPromptNever");
        auto *status = item("agentStatusEnabled");
        QVERIFY(timeout && action && never && status);
        QVERIFY(timeout->isVisible() && action->isVisible() && never->isVisible());
        QVERIFY(status->isVisible());
        QVERIFY(status->property("checked").toBool());

        timeout->forceActiveFocus();
        QTest::keyClick(&view, Qt::Key_Up);
        QCOMPARE(kcm.agentPromptTimeout(), 11);
        action->forceActiveFocus();
        QTest::keyClick(&view, Qt::Key_Down);
        QCOMPARE(kcm.agentPromptTimeoutAction(), QStringLiteral("cancel"));
        QVERIFY(item("agentsSection")->property("modified").toBool());
        QCOMPARE(savedBytes(), before);
        kcm.save();
        ScreenBotKcm reopened(nullptr, KPluginMetaData());
        QCOMPARE(reopened.agentPromptTimeout(), 11);
        QCOMPARE(reopened.agentPromptTimeoutAction(), QStringLiteral("cancel"));

        never->forceActiveFocus();
        QTest::keyClick(&view, Qt::Key_Space);
        QCOMPARE(kcm.agentPromptTimeout(), 0);
        QVERIFY(!timeout->isEnabled() && !action->isEnabled());
        kcm.load();
        QCOMPARE(kcm.agentPromptTimeout(), 11);
        QVERIFY(timeout->isEnabled() && action->isEnabled());
        QVERIFY(!never->property("checked").toBool());
        kcm.setAgentDetectionMode(QStringLiteral("block"));
        QVERIFY(!timeout->isVisible() && !action->isVisible() && !never->isVisible());
        kcm.load();
        QVERIFY(timeout->isVisible() && action->isVisible() && never->isVisible());

        const QString evidence = qEnvironmentVariable("SCREENBOT_EVIDENCE_DIR");
        if (evidence.isEmpty()) return;
        QVERIFY(QDir().mkpath(evidence));
        for (const int width : {390, 768, 1440}) {
            view.resize(width, 1000);
            for (const QString &state : {QStringLiteral("yes"), QStringLiteral("no"), QStringLiteral("never"), QStringLiteral("hidden")}) {
                kcm.setAgentDetectionMode(state == QLatin1String("hidden") ? QStringLiteral("start") : QStringLiteral("ask"));
                kcm.setAgentPromptTimeout(state == QLatin1String("never") ? 0 : 10);
                kcm.setAgentPromptTimeoutAction(state == QLatin1String("no") ? QStringLiteral("cancel") : QStringLiteral("start"));
                QTest::qWait(300);
                QVERIFY(view.grabWindow().save(evidence + QStringLiteral("/agents-%1-%2.png").arg(state).arg(width)));
                QVERIFY(timeout->width() <= width);
            }
        }
    }
};

int main(int argc, char **argv) {
    QTemporaryDir config;
    qputenv("HOME", config.path().toUtf8());
    qputenv("XDG_CONFIG_HOME", config.path().toUtf8());
    if (qEnvironmentVariableIsSet("SCREENBOT_TEST_DARK"))
        QFile::copy(QStringLiteral("/usr/share/color-schemes/BreezeDark.colors"), config.path() + QStringLiteral("/kdeglobals"));
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
    AgentPromptTest test;
    return QTest::qExec(&test, argc, argv);
}
#include "agentprompt_test.moc"
