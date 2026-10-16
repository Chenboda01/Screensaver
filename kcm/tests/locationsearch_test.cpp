#include "locationsearch.h"
#include "screenbotkcm.h"
#include <KPluginMetaData>
#include <KQuickConfigModule>
#include <KQuickConfigModuleLoader>
#include <QApplication>
#include <QFile>
#include <QElapsedTimer>
#include <QJsonDocument>
#include <QSettings>
#include <QStandardPaths>
#include <QTcpServer>
#include <QTcpSocket>
#include <QTemporaryDir>
#include <QTest>
#include <QQuickView>
#include <KLocalizedContext>
#include <QQuickItem>
#include <QQmlContext>
#include <QDir>

static QByteArray places() {
    return R"({"results":[
      {"name":"Springfield","admin1":"Illinois","country":"United States","country_code":"US","latitude":39.78,"longitude":-89.65,"timezone":"America/Chicago","population":114394},
      {"name":"Springfield","admin1":"Missouri","country":"United States","country_code":"US","latitude":37.21,"longitude":-93.29,"timezone":"America/Chicago","population":169176},
      {"name":"Seattle","admin1":"Washington","country":"United States","country_code":"US","latitude":47.61,"longitude":-122.33,"timezone":"America/Los_Angeles","population":737015}
    ]})";
}

class LocationSearchTest : public QObject {
    Q_OBJECT
private Q_SLOTS:
    void offlineCaseAccentsTyposAndAliases() {
        // Given: a representative offline catalog, including its English Munich spelling.
        const QStringList catalog{QStringLiteral("São Paulo, Brazil"), QStringLiteral("Munich, Germany"),
                                  QStringLiteral("Paris, France"), QStringLiteral("Seattle, United States")};
        for (const auto &query : {QStringLiteral("SAO PAULO"), QStringLiteral("munchen"), QStringLiteral("Pariss"), QStringLiteral("Seatle")}) {
            // When: the user types an accent-free name, alias, case variant, or typo.
            const auto result = LocationSearch::offlineMatches(catalog, query);
            // Then: exactly the intended city remains.
            QCOMPARE(result.size(), 1);
        }
    }
    void shippedCatalogWorksOffline() {
        // Given: the actual installed catalog source.
        QFile file(QStringLiteral(SCREENBOT_SOURCE_DIR "/countries_and_cities.txt"));
        QVERIFY(file.open(QIODevice::ReadOnly));
        QStringList catalog;
        while (!file.atEnd()) {
            const QString line = QString::fromUtf8(file.readLine()).trimmed();
            catalog.append(line.section(QLatin1Char(','), 1) + QStringLiteral(", ") + line.section(QLatin1Char(','), 0, 0));
        }
        // When: matching accent-free and local-language names without networking.
        const auto sao = LocationSearch::offlineMatches(catalog, QStringLiteral("sao paulo"));
        const auto munich = LocationSearch::offlineMatches(catalog, QStringLiteral("munchen"));
        // Then: the shipped cities are available.
        QVERIFY(!sao.isEmpty());
        QVERIFY(!munich.isEmpty());
        QCOMPARE(sao.first().toMap().value(QStringLiteral("display")).toString(), QStringLiteral("Sao Paulo, Brazil"));
        QCOMPARE(munich.first().toMap().value(QStringLiteral("display")).toString(), QStringLiteral("Munich, Germany"));
    }
    void rankingAndCountry() {
        // Given: prefix, contains, and fuzzy matches with conflicting population order.
        const QVariantList input{
            QVariantMap{{QStringLiteral("name"),QStringLiteral("Bostn")},{QStringLiteral("population"),9999999},{QStringLiteral("country"),QStringLiteral("United States")}},
            QVariantMap{{QStringLiteral("name"),QStringLiteral("East Boston")},{QStringLiteral("population"),99999},{QStringLiteral("country"),QStringLiteral("United States")}},
            QVariantMap{{QStringLiteral("name"),QStringLiteral("Boston")},{QStringLiteral("population"),1},{QStringLiteral("country"),QStringLiteral("United States")}},
            QVariantMap{{QStringLiteral("name"),QStringLiteral("Boston")},{QStringLiteral("population"),999},{QStringLiteral("country"),QStringLiteral("United Kingdom")}}};
        // When: search is restricted to the US.
        const auto result = LocationSearch::ranked(input, QStringLiteral("boston, us"));
        // Then: prefix outranks contains, which outranks typo, without the UK city.
        QCOMPARE(result.size(), 3);
        QCOMPARE(result[0].toMap()[QStringLiteral("name")].toString(), QStringLiteral("Boston"));
        QCOMPARE(result[1].toMap()[QStringLiteral("name")].toString(), QStringLiteral("East Boston"));
        QCOMPARE(result[2].toMap()[QStringLiteral("name")].toString(), QStringLiteral("Bostn"));
    }
    void parserPreservesSameNameIdentity() {
        // Given: distinct Springfields returned by the API.
        // When: parsing and population-ranking those results.
        const auto result = LocationSearch::parseResults(places(), QStringLiteral("springfield"));
        // Then: Missouri retains its own coordinates and zone.
        QCOMPARE(result.size(), 2);
        const auto selected = result.first().toMap();
        QCOMPARE(selected[QStringLiteral("display")].toString(), QStringLiteral("Springfield, Missouri, United States"));
        QCOMPARE(selected[QStringLiteral("latitude")].toDouble(), 37.21);
        QCOMPARE(selected[QStringLiteral("longitude")].toDouble(), -93.29);
        QCOMPARE(selected[QStringLiteral("timezone")].toString(), QStringLiteral("America/Chicago"));
    }
    void parserRejectsInvalidCoordinates() {
        // Given: malformed and out-of-range coordinates.
        const QByteArray input = R"({"results":[{"name":"Paris","country":"France","latitude":91,"longitude":2,"timezone":"Europe/Paris"},{"name":"Paris","country":"France","latitude":"48","longitude":2,"timezone":"Europe/Paris"}]})";
        // When: parsing boundary data.
        const auto result = LocationSearch::parseResults(input, QStringLiteral("Paris"));
        // Then: neither invalid place can be selected.
        QVERIFY(result.isEmpty());
    }
    void debounceCancellationAndCache() {
        // Given: a real local HTTP server and an enabled asynchronous search service.
        QTcpServer server;
        QVERIFY(server.listen(QHostAddress::LocalHost));
        LocationSearch search(nullptr, QUrl(QStringLiteral("http://127.0.0.1:%1/search").arg(server.serverPort())));
        search.setEnabled(true);
        int requests = 0;
        connect(&server, &QTcpServer::newConnection, this, [&] {
            auto socket = server.nextPendingConnection();
            connect(socket, &QTcpSocket::readyRead, socket, [&, socket] {
                socket->readAll(); ++requests;
                const auto body = places();
                socket->write("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: " + QByteArray::number(body.size()) + "\r\nConnection: close\r\n\r\n" + body);
                socket->disconnectFromHost();
            });
            connect(socket, &QTcpSocket::disconnected, socket, &QObject::deleteLater);
        });
        // When: typing a burst, awaiting a result, then repeating the query.
        search.search(QStringLiteral("spr"));
        search.search(QStringLiteral("spring"));
        search.search(QStringLiteral("springfield"));
        QCOMPARE(requests, 0);
        QTRY_COMPARE_WITH_TIMEOUT(search.results().size(), 2, 1500);
        QTRY_VERIFY_WITH_TIMEOUT(search.status().isEmpty(), 1500);
        QCOMPARE(requests, 2);
        search.search(QStringLiteral("springfield"));
        QCOMPARE(search.results().size(), 2);
        search.search(QStringLiteral("seattle"));
        search.setEnabled(false);
        QTest::qWait(400);
        // Then: one HTTP request total, and disabled search has no pending results.
        QCOMPARE(requests, 2);
        QVERIFY(search.results().isEmpty());
    }
    void offlineFailure() {
        // Given: an unreachable endpoint and the shipped-catalog format.
        LocationSearch search(nullptr, QUrl(QStringLiteral("http://127.0.0.1:1/search")));
        search.setCatalog({QStringLiteral("São Paulo, Brazil")});
        search.setEnabled(true);
        // When: an online request fails.
        search.search(QStringLiteral("sao paulo"));
        QTRY_VERIFY_WITH_TIMEOUT(search.status().contains(QStringLiteral("unavailable")), 4000);
        // Then: offline matching remains usable.
        QCOMPARE(search.results().size(), 1);
        QCOMPARE(search.results()[0].toMap()[QStringLiteral("display")].toString(), QStringLiteral("São Paulo, Brazil"));
    }
    void applyDiscardAndLegacyLoad() {
        // Given: an isolated V22 config and a temporary catalog.
        QSettings cfg(QStandardPaths::writableLocation(QStandardPaths::ConfigLocation) + QStringLiteral("/screenbot-screensaver.ini"), QSettings::IniFormat);
        cfg.clear();
        cfg.setValue("Screensaver/live_sky_location", QStringLiteral("Paris, France"));
        cfg.setValue("Screensaver/live_sky_enabled", true);
        cfg.sync();
        ScreenBotKcm kcm(nullptr, KPluginMetaData());
        QCOMPARE(kcm.liveSkyLocation(), QStringLiteral("Paris, France"));
        kcm.locationSearch()->setCatalog({QStringLiteral("Munich, Germany")});
        // When: selecting, discarding, selecting and applying an offline city.
        kcm.locationSearch()->search(QStringLiteral("munchen"));
        kcm.selectLiveSkyPlace(0);
        cfg.sync();
        QCOMPARE(cfg.value("Screensaver/live_sky_location").toString(), QStringLiteral("Paris, France"));
        QVERIFY(kcm.needsSave());
        kcm.load();
        QCOMPARE(kcm.liveSkyLocation(), QStringLiteral("Paris, France"));
        QVERIFY(!kcm.needsSave());
        kcm.locationSearch()->search(QStringLiteral("munchen"));
        kcm.selectLiveSkyPlace(0);
        kcm.save();
        // Then: only Apply persists the selected city, and another instance reloads it.
        ScreenBotKcm restored(nullptr, KPluginMetaData());
        QCOMPARE(restored.liveSkyLocation(), QStringLiteral("Munich, Germany"));
        QVERIFY(!restored.needsSave());
    }
    void uiKeyboardAndMouse() {
        // Given: the actual native city search control with two offline candidates.
        ScreenBotKcm kcm(nullptr, KPluginMetaData());
        kcm.setLiveSkyEnabled(true);
        kcm.locationSearch()->setCatalog({QStringLiteral("Paris, France"), QStringLiteral("Paris, United States")});
        QQuickView view;
        auto *translations = new KLocalizedContext(&view);
        translations->setTranslationDomain(QStringLiteral("kcm_screenbot_screensaver"));
        view.rootContext()->setContextObject(translations);
        view.rootContext()->setContextProperty(QStringLiteral("kcm"), &kcm);
        view.setSource(QUrl::fromLocalFile(QStringLiteral(SCREENBOT_SOURCE_DIR "/kcm/tests/location_ui.qml")));
        QCOMPARE(view.status(), QQuickView::Ready);
        view.setResizeMode(QQuickView::SizeRootObjectToView);
        view.resize(640, 480);
        view.show();
        QVERIFY(QTest::qWaitForWindowExposed(&view));
        auto field = view.rootObject()->findChild<QQuickItem *>(QStringLiteral("citySearch"));
        auto list = view.rootObject()->findChild<QQuickItem *>(QStringLiteral("citySuggestions"));
        QVERIFY(field);
        QVERIFY(list);
        field->forceActiveFocus();
        // When: typing and using Down + Enter before the network debounce expires.
        for (const auto key : {Qt::Key_P, Qt::Key_A, Qt::Key_R}) QTest::keyClick(&view, key);
        QCOMPARE(list->property("count").toInt(), 2);
        QTest::keyClick(&view, Qt::Key_Down);
        QTest::keyClick(&view, Qt::Key_Return);
        // Then: keyboard selection chooses the second city, with no settings write.
        QCOMPARE(kcm.liveSkyLocation(), QStringLiteral("Paris, United States"));
        QVERIFY(kcm.needsSave());
        for (const auto key : {Qt::Key_P, Qt::Key_A, Qt::Key_R}) QTest::keyClick(&view, key);
        const QString evidence = qEnvironmentVariable("SCREENBOT_EVIDENCE_DIR");
        if (!evidence.isEmpty()) {
            QDir().mkpath(evidence);
            for (const int width : {390, 1000}) {
                view.resize(width, 480);
                QTest::qWait(30);
                QVERIFY(view.grabWindow().save(evidence + QStringLiteral("/city-search-%1.png").arg(width)));
            }
        }
        // When: clicking the first native delegate.
        const QPoint firstRow = list->mapToScene(QPointF(30, 15)).toPoint();
        QTest::mouseClick(&view, Qt::LeftButton, Qt::NoModifier, firstRow);
        // Then: mouse selection chooses France and dismisses the list.
        QCOMPARE(kcm.liveSkyLocation(), QStringLiteral("Paris, France"));
        QVERIFY(!list->isVisible());
        kcm.setLiveSkyEnabled(false);
    }
    void fullSettingsQmlLoads() {
        // Load through KDE's real KCM loader so SimpleKCM supplies the same
        // context and configuration object as System Settings. Loading main.qml
        // into a bare QQuickView leaves KCM properties undefined and creates
        // misleading warnings for otherwise valid settings bindings.
        const QString plugin = qEnvironmentVariable("SCREENBOT_TEST_PLUGIN");
        QVERIFY2(!plugin.isEmpty(), "Set SCREENBOT_TEST_PLUGIN to the built KCM plugin");
        QTest::failOnWarning(QRegularExpression(QStringLiteral("kf\\.i18n:|QML Connections:|Unable to assign ")));
        const auto result = KQuickConfigModuleLoader::loadModule(KPluginMetaData(plugin));
        QVERIFY2(result, qPrintable(result.errorString));
        std::unique_ptr<KQuickConfigModule> module(result.plugin);
        auto *root = module->mainUi();
        QVERIFY2(root, qPrintable(module->errorString()));
        QVERIFY(root->findChild<QQuickItem *>(QStringLiteral("bobNameField")));
        QVERIFY(root->findChild<QQuickItem *>(QStringLiteral("bobColorPreset")));
        QVERIFY(root->findChild<QQuickItem *>(QStringLiteral("bobCustomColorButton")));
        QVERIFY(root->findChild<QObject *>(QStringLiteral("bobColorDialog")));
        const auto appearanceSection = root->findChild<QQuickItem *>(QStringLiteral("appearanceSection"));
        QVERIFY(appearanceSection);
        QCOMPARE(appearanceSection->property("title").toString(), QStringLiteral("Customize Bob"));
    }
    void onlineCoordinateApplyDiscard() {
        if (!qEnvironmentVariableIsSet("SCREENBOT_TEST_ONLINE")) QSKIP("Live API scenario requires SCREENBOT_TEST_ONLINE=1");
        // Given: a real search result list with several Springfields.
        ScreenBotKcm kcm(nullptr, KPluginMetaData());
        kcm.setLiveSkyEnabled(true);
        kcm.locationSearch()->search(QStringLiteral("springfield, us"));
        QTRY_VERIFY_WITH_TIMEOUT(kcm.locationSearch()->status() != QStringLiteral("Searching online…"), 8000);
        int index = -1;
        const auto results = kcm.locationSearch()->results();
        for (int i = 0; i < results.size(); ++i)
            if (results[i].toMap().value(QStringLiteral("admin1")).toString() == QStringLiteral("Missouri")) index = i;
        QVERIFY(index >= 0);
        // When: selecting Missouri and applying its complete place bundle.
        kcm.selectLiveSkyPlace(index);
        kcm.save();
        ScreenBotKcm restored(nullptr, KPluginMetaData());
        // Then: reloading retains Missouri's coordinates and time zone.
        QCOMPARE(restored.liveSkyLocation(), QStringLiteral("Springfield, Missouri, United States"));
        QVERIFY(qAbs(restored.liveSkyPlace().value(QStringLiteral("latitude")).toDouble() - 37.21533) < .01);
        QVERIFY(qAbs(restored.liveSkyPlace().value(QStringLiteral("longitude")).toDouble() + 93.29824) < .01);
        QCOMPARE(restored.liveSkyPlace().value(QStringLiteral("timezone")).toString(), QStringLiteral("America/Chicago"));
        restored.setLiveSkyLocation(QStringLiteral("Paris, France"));
        restored.load();
        QCOMPARE(restored.liveSkyPlace(), kcm.liveSkyPlace());
    }
    void onlineQueries() {
        if (!qEnvironmentVariableIsSet("SCREENBOT_TEST_ONLINE")) QSKIP("Run explicitly with SCREENBOT_TEST_ONLINE=1 for the live API probe");
        for (const QString &query : {QStringLiteral("bost"), QStringLiteral("sao paulo"), QStringLiteral("munchen"), QStringLiteral("Seatle"), QStringLiteral("paris, us")}) {
            LocationSearch search;
            search.setEnabled(true);
            QElapsedTimer elapsed;
            elapsed.start();
            search.search(query);
            QTRY_VERIFY_WITH_TIMEOUT(search.status() != QStringLiteral("Searching online…"), 8000);
            QStringList names;
            for (const auto &place : search.results()) names.append(place.toMap().value(QStringLiteral("display")).toString());
            qInfo() << query << elapsed.elapsed() << "ms" << names;
            QVERIFY2(!search.results().isEmpty(), qPrintable(query));
            const QString expected = query == QStringLiteral("bost") ? QStringLiteral("Boston")
                : query == QStringLiteral("sao paulo") ? QStringLiteral("São Paulo")
                : query == QStringLiteral("munchen") ? QStringLiteral("Munich")
                : query == QStringLiteral("Seatle") ? QStringLiteral("Seattle") : QStringLiteral("Paris");
            bool found = false;
            for (const auto &place : search.results()) found |= place.toMap().value(QStringLiteral("name")).toString() == expected;
            QVERIFY2(found, qPrintable(expected));
        }
    }
};

int main(int argc, char **argv) {
    QTemporaryDir config;
    qputenv("XDG_CONFIG_HOME", config.path().toUtf8());
    if (qEnvironmentVariableIsSet("SCREENBOT_TEST_DARK"))
        QFile::copy(QStringLiteral("/usr/share/color-schemes/BreezeDark.colors"), config.path() + QStringLiteral("/kdeglobals"));
    QApplication app(argc, argv);
    LocationSearchTest test;
    return QTest::qExec(&test, argc, argv);
}
#include "locationsearch_test.moc"
