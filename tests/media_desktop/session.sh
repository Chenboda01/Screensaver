#!/usr/bin/env bash
set -euo pipefail
[[ "$XDG_RUNTIME_DIR" == /tmp/screenbot-media-* ]]
[[ "$DBUS_SYSTEM_BUS_ADDRESS" == "$DBUS_SESSION_BUS_ADDRESS" ]]
QT_QPA_PLATFORM=xcb "$SCREENBOT_PYTHON" "$SCREENBOT_ROOT/tests/media_desktop/drive.py"
export PYTHONPATH="$HOME/ScreenBot/screensaver"
QT_QPA_PLATFORM=wayland QT_SCALE_FACTOR=1 "$SCREENBOT_PYTHON" "$SCREENBOT_ROOT/tests/media_desktop/variants.py"
QT_QPA_PLATFORM=wayland QT_SCALE_FACTOR=2 "$SCREENBOT_PYTHON" "$SCREENBOT_ROOT/tests/media_desktop/variants.py"
