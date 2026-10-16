#include "locationsearch.h"
#include <KLocalizedString>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QTimeZone>
#include <QUrlQuery>
#include <algorithm>
#include <cmath>
#include <numeric>

static QString folded(const QString &text) {
    QString result;
    for (const QChar c : text.normalized(QString::NormalizationForm_KD).toCaseFolded())
        if (c.category() != QChar::Mark_NonSpacing) result.append(c);
    result = result.simplified();
    if (result == QLatin1String("munchen")) return QStringLiteral("munich");
    return result;
}

static int distance(const QString &a, const QString &b) {
    QList<int> row(b.size() + 1);
    std::iota(row.begin(), row.end(), 0);
    for (qsizetype i = 0; i < a.size(); ++i) {
        int diagonal = row[0];
        row[0] = i + 1;
        for (qsizetype j = 0; j < b.size(); ++j) {
            const int old = row[j + 1];
            row[j + 1] = std::min({row[j] + 1, old + 1, diagonal + (a[i] != b[j])});
            diagonal = old;
        }
    }
    return row.last();
}

static int score(const QVariantMap &place, const QString &query) {
    const QString name = folded(place.value(QStringLiteral("name")).toString());
    const QString needle = folded(query.section(QLatin1Char(','), 0, 0));
    const QString country = folded(query.section(QLatin1Char(','), 1).trimmed());
    const QString candidateCountry = folded(place.value(QStringLiteral("country")).toString());
    const QString code = folded(place.value(QStringLiteral("country_code")).toString());
    const bool us = (country == QLatin1String("us") || country == QLatin1String("usa"))
        && (candidateCountry == QLatin1String("united states") || candidateCountry == QLatin1String("united states of america"));
    if (!country.isEmpty() && candidateCountry != country && code != country && !us) return 100;
    if (name.startsWith(needle)) return 0;
    if (name.contains(needle)) return 1;
    return distance(name, needle) <= std::max(1, int(needle.size() / 5)) ? 2 : 100;
}

QVariantList LocationSearch::ranked(QVariantList places, const QString &query) {
    places.erase(std::remove_if(places.begin(), places.end(), [&](const QVariant &p) {
        return score(p.toMap(), query) == 100;
    }), places.end());
    std::stable_sort(places.begin(), places.end(), [&](const QVariant &a, const QVariant &b) {
        const auto left = a.toMap(), right = b.toMap();
        const int l = score(left, query), r = score(right, query);
        if (l != r) return l < r;
        return left.value(QStringLiteral("population")).toLongLong() > right.value(QStringLiteral("population")).toLongLong();
    });
    return places.mid(0, 10);
}

QVariantList LocationSearch::offlineMatches(const QStringList &catalog, const QString &query) {
    QVariantList places;
    for (const QString &entry : catalog) {
        const QString name = entry.section(QStringLiteral(", "), 0, -2);
        places.append(QVariantMap{{QStringLiteral("name"), name},
            {QStringLiteral("display"), entry}, {QStringLiteral("country"), entry.section(QStringLiteral(", "), -1)}});
    }
    return ranked(places, query);
}

QVariantList LocationSearch::parseResults(const QByteArray &json, const QString &query) {
    QVariantList places;
    const auto results = QJsonDocument::fromJson(json).object().value(QStringLiteral("results")).toArray();
    for (const auto &item : results) {
        const auto value = item.toObject();
        const auto lat = value.value(QStringLiteral("latitude")), lon = value.value(QStringLiteral("longitude"));
        const QString name = value.value(QStringLiteral("name")).toString();
        const QString country = value.value(QStringLiteral("country")).toString();
        const QString zone = value.value(QStringLiteral("timezone")).toString();
        if (name.isEmpty() || country.isEmpty() || !lat.isDouble() || !lon.isDouble()
            || !std::isfinite(lat.toDouble()) || !std::isfinite(lon.toDouble())
            || std::abs(lat.toDouble()) > 90 || std::abs(lon.toDouble()) > 180
            || !QTimeZone::isTimeZoneIdAvailable(zone.toUtf8())) continue;
        auto place = value.toVariantMap();
        QStringList label{name};
        const QString region = value.value(QStringLiteral("admin1")).toString();
        if (!region.isEmpty() && region != name) label.append(region);
        label.append(country);
        place.insert(QStringLiteral("display"), label.join(QStringLiteral(", ")));
        places.append(place);
    }
    return ranked(places, query);
}

LocationSearch::LocationSearch(QObject *parent, const QUrl &endpoint) : QObject(parent), m_endpoint(endpoint) {
    m_debounce.setSingleShot(true);
    m_debounce.setInterval(300);
    connect(&m_debounce, &QTimer::timeout, this, [this] { request(m_query); });
}

void LocationSearch::cancel() {
    ++m_generation;
    m_debounce.stop();
    if (m_reply) m_reply->abort();
    m_reply = nullptr;
}

void LocationSearch::setEnabled(bool enabled) {
    m_enabled = enabled;
    if (!enabled) { cancel(); m_results.clear(); m_status.clear(); Q_EMIT changed(); }
}

void LocationSearch::search(const QString &query) {
    cancel();
    m_query = query.trimmed().left(128);
    m_results.clear();
    m_status.clear();
    if (m_enabled && m_query.section(QLatin1Char(','), 0, 0).size() >= 3) {
        if (const auto cached = m_cache.object(m_query.toCaseFolded())) {
            m_results = *cached;
        } else {
            m_results = offlineMatches(m_catalog, m_query);
            m_status = i18n("Searching online…");
            m_debounce.start();
        }
    }
    Q_EMIT changed();
}

void LocationSearch::request(const QString &query, bool broadened) {
    if (!m_enabled) return;
    QUrl url(m_endpoint);
    QUrlQuery args;
    QString name = query.section(QLatin1Char(','), 0, 0).trimmed();
    if (broadened) name = name.left(3);
    const QString country = query.section(QLatin1Char(','), 1).trimmed();
    args.addQueryItem(QStringLiteral("name"), country.size() == 2 || country.isEmpty() ? name : name + QStringLiteral(", ") + country);
    if (country.size() == 2) args.addQueryItem(QStringLiteral("countryCode"), country.toUpper());
    args.addQueryItem(QStringLiteral("count"), QStringLiteral("10"));
    args.addQueryItem(QStringLiteral("language"), QStringLiteral("en"));
    url.setQuery(args);
    QNetworkRequest request(url);
    request.setTransferTimeout(3000);
    auto reply = m_manager.get(request);
    m_reply = reply;
    const auto generation = m_generation;
    connect(reply, &QNetworkReply::downloadProgress, this, [reply](qint64 received, qint64) {
        if (received > 262144) reply->abort();
    });
    connect(reply, &QNetworkReply::finished, this, [this, reply, query, generation, broadened] {
        reply->deleteLater();
        if (generation != m_generation || !m_enabled) return;
        m_reply = nullptr;
        const QByteArray body = reply->readAll();
        const auto document = QJsonDocument::fromJson(body);
        if (reply->error() != QNetworkReply::NoError || !document.isObject()
            || document.object().value(QStringLiteral("error")).toBool()) {
            if (broadened && !m_results.isEmpty()) {
                m_status = i18n("Additional online matches unavailable. Showing the results already received.");
            } else {
                m_results = offlineMatches(m_catalog, query);
                m_status = i18n("Online search unavailable. Showing offline catalog matches.");
            }
        } else {
            auto found = parseResults(body, query);
            if (broadened) {
                for (const auto &place : m_results)
                    if (!found.contains(place)) found.append(place);
                found = ranked(found, query);
            }
            m_results = found;
            if (m_results.size() < 10 && !broadened && query.section(QLatin1Char(','), 0, 0).size() > 3) {
                Q_EMIT changed();
                this->request(query, true);
                return;
            }
            if (m_results.isEmpty()) m_results = offlineMatches(m_catalog, query);
            m_cache.insert(query.toCaseFolded(), new QVariantList(m_results));
            m_status = m_results.isEmpty() ? i18n("No matches. Check the spelling, or try a nearby larger town.") : QString();
        }
        Q_EMIT changed();
    });
}
