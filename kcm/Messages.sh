#!/usr/bin/env bash
# Extract both QML and C++ messages into the catalog used by this KCM.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
catalog_dir=${podir:-po}
mkdir -p -- "$catalog_dir"
"${XGETTEXT:-xgettext}" --from-code=UTF-8 --language=C++ --kde \
    --keyword=i18n:1 --keyword=i18nc:1c,2 --keyword=i18np:1,2 \
    --keyword=i18ncp:1c,2,3 --flag=i18n:1:kde-format --flag=i18nc:2:kde-format \
    --flag=i18np:1:kde-format --flag=i18np:2:kde-format \
    --flag=i18ncp:2:kde-format --flag=i18ncp:3:kde-format --add-comments=TRANSLATORS \
    --package-name=ScreenBot --package-version=22 \
    --copyright-holder='ScreenBot contributors' \
    --msgid-bugs-address='https://github.com/Chenboda01/Screensaver/issues' \
    --output="$catalog_dir/kcm_screenbot_screensaver.pot" \
    ui/*.qml ./*.cpp
printf 'Extracted %s\n' "$catalog_dir/kcm_screenbot_screensaver.pot"
