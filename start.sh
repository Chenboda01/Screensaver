#!/usr/bin/env bash
# Plasma Power Management can invoke this launcher after a period of inactivity.
set -euo pipefail
cd "$HOME/ScreenBot/screensaver"
export QT_QPA_PLATFORM=wayland
# Only allow one saver, even if PowerDevil triggers on multiple power profiles.
exec /usr/bin/flock -n "${XDG_RUNTIME_DIR:-/tmp}/screenbot-screensaver-${UID}.lock" /usr/bin/python screensaver.py
