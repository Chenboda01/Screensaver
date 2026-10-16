#!/usr/bin/env bash
# Shared by installation and every launcher, including KDE Settings previews.
screenbot_select_python() {
    local saved_path="${1:-}" candidate="" resolved=""
    if [[ -n "${SCREENBOT_PYTHON:-}" ]]; then
        candidate="$SCREENBOT_PYTHON"
    elif [[ -n "$saved_path" && -f "$saved_path" ]]; then
        IFS= read -r candidate < "$saved_path" || true
        if [[ -z "$candidate" ]]; then
            echo "ScreenBot: empty interpreter file $saved_path; rerun install.sh or set SCREENBOT_PYTHON." >&2
            return 1
        fi
    else
        candidate="$(command -v python3 || command -v python || true)"
    fi
    resolved="$(command -v -- "$candidate" || true)"
    if [[ -z "$resolved" || ! -x "$resolved" ]]; then
        echo "ScreenBot: Python 3 interpreter '${candidate:-not found}' is unavailable. Install Python 3 or set SCREENBOT_PYTHON to its executable and rerun install.sh." >&2
        return 1
    fi
    # Keep the venv executable path, rather than resolving its symlink to system Python.
    resolved="$(cd -- "$(dirname -- "$resolved")" && pwd)/$(basename -- "$resolved")"
    if ! "$resolved" -c 'import sys; raise SystemExit(sys.version_info.major != 3)' 2>/dev/null; then
        echo "ScreenBot: $resolved is not a working Python 3 interpreter. Set SCREENBOT_PYTHON to Python 3 and rerun install.sh." >&2
        return 1
    fi
    if ! "$resolved" -c 'import PyQt6' 2>/dev/null; then
        echo "ScreenBot: PyQt6 is missing from $resolved. Install python3-pyqt6 (Debian/Ubuntu/KDE neon), python-pyqt6 (Arch/CachyOS), or python3-qt6 (Fedora); for a virtual environment, run its Python with -m pip install PyQt6." >&2
        return 1
    fi
    export SCREENBOT_PYTHON="$resolved"
}
