# Collapsible settings regression check

`sections_test` loads the real KCM and QML in an isolated HOME/config directory.
It checks all seven headers, first-visit expansion, pending summaries and dirty
markers, settings Apply/Discard, persistent UI state, Tab/Space/Enter/arrow keys,
Qt accessibility expandable state, the reset action, and the real BobOS preview
button. The preview uses the existing capture probe and exits through Qt input;
it never changes the user's config or activates the screen locker.

Build and capture the native Plasma surface (Qt 6, KDE Frameworks 6, PyQt6):

```sh
cmake -S kcm -B build/kcm -DBUILD_TESTING=ON
cmake --build build/kcm
mkdir -p .omo/evidence/sections/light .omo/evidence/sections/dark
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
QT_QUICK_CONTROLS_STYLE=org.kde.desktop QT_QPA_PLATFORMTHEME=kde \
SCREENBOT_EVIDENCE_DIR="$PWD/.omo/evidence/sections/light" \
build/kcm/bin/sections_test
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
QT_QUICK_CONTROLS_STYLE=org.kde.desktop QT_QPA_PLATFORMTHEME=kde \
SCREENBOT_TEST_DARK=1 SCREENBOT_EVIDENCE_DIR="$PWD/.omo/evidence/sections/dark" \
build/kcm/bin/sections_test
```

Each run captures all sections at 390, 768, and 1440 px wide, an overview, the
scrolled end with every section open, an unapplied Clock change, and a real
BobOS preview frame/receipt. The dark run reads the installed Breeze Dark palette.
Without KDE's platform theme and desktop control style, an offscreen fallback
can fail to reproduce the desktop palette; do not label those captures as native
Plasma light/dark evidence.

`ctest --test-dir build/kcm -R '^sections$' --output-on-failure` also runs the
functional checks and writes captures to `build/kcm/section-captures`.
