#!/usr/bin/env bash
# Build, stage-install and exercise the real KCM with English and Spanish catalogs.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
output=${1:?Usage: kcm/tests/check-translations.sh ABSOLUTE_OUTPUT_DIRECTORY}
mkdir -p -- "$output"
output=$(cd -- "$output" && pwd)
podir="$output/extracted" "$repo/kcm/Messages.sh" > "$output/extraction.log" 2>&1
msgfmt --check --statistics "$repo/kcm/po/es/kcm_screenbot_screensaver.po" -o "$output/es.mo" >> "$output/extraction.log" 2>&1
cmake -S "$repo/kcm" -B "$output/build" -DCMAKE_BUILD_TYPE=Debug \
    -DCMAKE_INSTALL_PREFIX="$output/install" > "$output/configure.log" 2>&1
cmake --build "$output/build" --parallel 2 > "$output/build.log" 2>&1
cmake --install "$output/build" > "$output/install.log" 2>&1
plugin=$(find "$output/install" -name kcm_screenbot_screensaver.so -print -quit)
export QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software
export QT_QPA_PLATFORMTHEME=kde QT_QUICK_CONTROLS_STYLE=org.kde.desktop
export XDG_DATA_HOME="$output/data"
mkdir -p -- "$XDG_DATA_HOME"
export XDG_DATA_DIRS="$output/install/share:/usr/share"
export SCREENBOT_TEST_PLUGIN="$plugin"
# LANGUAGE is KDE's ordered UI-language preference. C disables gettext translations.
export LC_ALL=en_US.UTF-8
for language in en_US es zz; do
    for palette in light dark; do
        export LANGUAGE="$language" SCREENBOT_EVIDENCE_DIR="$output/$language-$palette"
        if [[ $palette == dark ]]; then export SCREENBOT_TEST_DARK=1; else unset SCREENBOT_TEST_DARK; fi
        "$output/build/bin/i18n_test" > "$output/$language-$palette.log" 2>&1
    done
done
unset SCREENBOT_TEST_DARK
export SCREENBOT_EVIDENCE_DIR="$output/ctest-evidence"
mkdir -p -- "$SCREENBOT_EVIDENCE_DIR"
LANGUAGE=en_US ctest --test-dir "$output/build" --exclude-regex '^i18n_' --output-on-failure > "$output/ctest.log" 2>&1
printf 'Installed locale and Apply/Discard checks passed: %s\n' "$output"
