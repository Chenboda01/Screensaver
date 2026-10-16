#!/usr/bin/env bash
# Plasma Power Management can invoke this launcher after a period of inactivity.
set -euo pipefail
cd "$HOME/ScreenBot/screensaver"
source ./python-runtime.sh
screenbot_select_python ./python-path
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-wayland}"
# Manual launches and previews never consult or change the automatic agent policy.
case "${1:-}" in
    --manual)
        shift
        exec "$SCREENBOT_PYTHON" screensaver.py "$@"
        ;;
    --preview|--preview-bobos)
        exec "$SCREENBOT_PYTHON" screensaver.py "$@"
        ;;
esac
# Only allow one prompt or saver, even if PowerDevil triggers on multiple profiles.
FLOCK="$(command -v flock)" || { echo 'ScreenBot: install flock (util-linux) to enable automatic launches.' >&2; exit 1; }
BASH_EXEC="$(command -v bash)" || { echo 'ScreenBot: Bash is missing from PATH.' >&2; exit 1; }
exec "$FLOCK" -n "${XDG_RUNTIME_DIR:-/tmp}/screenbot-screensaver-${UID}.lock" "$BASH_EXEC" -c '
    if "$SCREENBOT_PYTHON" agent_prompt.py; then
        exec "$SCREENBOT_PYTHON" screensaver.py
    fi
    exit 0
'
