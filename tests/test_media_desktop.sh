#!/usr/bin/env bash
# Native KCM shell QA on private KWin/Xwayland; never connects to the active desktop.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE="${1:?Provide a fresh evidence directory}"
mkdir -p "$EVIDENCE"
EVIDENCE="$(cd "$EVIDENCE" && pwd)"
[[ ! -e "$EVIDENCE/home" ]] || { echo 'Use a fresh evidence directory.' >&2; exit 2; }
cp "$ROOT/tests/media_desktop/actions.json" "$EVIDENCE/actions.json"
source "$ROOT/python-runtime.sh"
screenbot_select_python
TEST_HOME="$EVIDENCE/home"
RUNTIME="$(mktemp -d /tmp/screenbot-media-XXXXXX)"
trap 'rm -rf -- "$RUNTIME"' EXIT
mkdir -p "$TEST_HOME/.config"
# Permit XTest only within this disposable compositor's private configuration.
cat > "$TEST_HOME/.config/kwinrc" <<'CONFIG'
[Xwayland]
XwaylandEisNoPrompt=true
CONFIG
COMMON=("HOME=$TEST_HOME" "XDG_CONFIG_HOME=$TEST_HOME/.config" "XDG_CACHE_HOME=$TEST_HOME/.cache" "XDG_DATA_HOME=$TEST_HOME/.local/share" "XDG_RUNTIME_DIR=$RUNTIME")
env "${COMMON[@]}" bash "$ROOT/install.sh" --no-idle > "$EVIDENCE/install.log" 2>&1
export SCREENBOT_ROOT="$ROOT" SCREENBOT_MEDIA_EVIDENCE="$EVIDENCE" SCREENBOT_MEDIA_SANDBOX=1 SCREENBOT_PYTHON
export QT_PLUGIN_PATH="$TEST_HOME/.local/lib/plugins:/usr/lib/qt6/plugins"
export XDG_DATA_DIRS="$TEST_HOME/.local/share:/usr/share"
# Unset inherited desktop endpoints; KWin supplies its own DISPLAY to the session.
env -u DISPLAY -u WAYLAND_DISPLAY "${COMMON[@]}" QT_QPA_PLATFORM=wayland LIBGL_ALWAYS_SOFTWARE=1 QT_QUICK_BACKEND=software KWIN_SCREENSHOT_NO_PERMISSION_CHECKS=1 KDE_DEBUG=1 \
 timeout --foreground 210 dbus-run-session --config-file="$ROOT/tests/idle_wayland/private-bus.conf" -- \
 bash -c 'export DBUS_SYSTEM_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS"; exec kwin_wayland --virtual --xwayland --width 1440 --height 1000 --no-lockscreen --no-global-shortcuts --no-kactivities --socket sb-media --exit-with-session "$1"' \
 _ "$ROOT/tests/media_desktop/session.sh" > "$EVIDENCE/session.log" 2>&1

printf "Private desktop QA passed: %s\n" "$EVIDENCE"
