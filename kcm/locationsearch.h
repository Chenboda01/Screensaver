#pragma once
#include <QCache>
#include <QNetworkAccessManager>
#include <QPointer>
#include <QTimer>
#include <QVariantList>

class LocationSearch : public QObject {
    Q_OBJECT
    Q_PROPERTY(QVariantList results READ results NOTIFY changed)
    Q_PROPERTY(QString status READ status NOTIFY changed)
public:
    explicit LocationSearch(QObject *parent = nullptr,
        const QUrl &endpoint = QUrl(QStringLiteral("https://geocoding-api.open-meteo.com/v1/search")));
    QVariantList results() const { return m_results; }
    QString status() const { return m_status; }
    void setEnabled(bool enabled);
    void setCatalog(const QStringList &catalog) { m_catalog = catalog; }
    Q_INVOKABLE void search(const QString &query);
    static QVariantList offlineMatches(const QStringList &catalog, const QString &query);
    static QVariantList parseResults(const QByteArray &json, const QString &query);
    static QVariantList ranked(QVariantList places, const QString &query);
Q_SIGNALS:
    void changed();
private:
    void request(const QString &query, bool broadened = false);
    void cancel();
    QUrl m_endpoint;
    QNetworkAccessManager m_manager;
    QPointer<QNetworkReply> m_reply;
    QTimer m_debounce;
    QCache<QString, QVariantList> m_cache{32};
    QStringList m_catalog;
    QVariantList m_results;
    QString m_query;
    QString m_status;
    bool m_enabled = false;
    quint64 m_generation = 0;
};
