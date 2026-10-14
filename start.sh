#!/usr/bin/env bash
# Plasma Power Management can invoke this launcher after a period of inactivity.
set -euo pipefail
cd "$HOME/ScreenBot/screensaver"
export QT_QPA_PLATFORM=wayland
# A deliberate manual launch never consults or changes the automatic agent policy.
if [[ "${1:-}" == "--manual" ]]; then
    exec /usr/bin/python screensaver.py
fi
# Only allow one prompt or saver, even if PowerDevil triggers on multiple profiles.
exec /usr/bin/flock -n "${XDG_RUNTIME_DIR:-/tmp}/screenbot-screensaver-${UID}.lock" /usr/bin/bash -c '
    if /usr/bin/python agent_prompt.py; then
        exec /usr/bin/python screensaver.py
    fi
    exit 0
'
