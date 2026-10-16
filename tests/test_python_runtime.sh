#!/usr/bin/env bash
# Run: bash tests/test_python_runtime.sh [evidence-directory]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE="${1:-$ROOT/.omo/evidence/python-runtime}"
mkdir -p "$EVIDENCE"
EVIDENCE="$(cd "$EVIDENCE" && pwd)"
WORK="$(mktemp -d "$EVIDENCE/fixtures-XXXXXX")"
PYTHON="$(command -v python3)"
BASH_EXEC="$(command -v bash)"
mkdir -p "$WORK/bin"
ln -s "$(command -v dirname)" "$WORK/bin/dirname"
ln -s "$(command -v basename)" "$WORK/bin/basename"
expect_failure() {
    local scenario="$1" expected="$2"
    shift 2
    if "$@" > "$EVIDENCE/$scenario.log" 2>&1; then
        echo "FAIL $scenario unexpectedly succeeded" >&2
        exit 1
    fi
    grep -F "$expected" "$EVIDENCE/$scenario.log" >/dev/null
    echo "PASS $scenario rejected with actionable diagnostic"
}
# Given no interpreter on PATH, installation must stop before writing anything.
expect_failure missing-python 'Python 3' env -u SCREENBOT_PYTHON PATH="$WORK/bin" "$BASH_EXEC" "$ROOT/install.sh"
# Given an invalid explicit choice, do not silently use a different interpreter.
expect_failure invalid-override 'SCREENBOT_PYTHON' env SCREENBOT_PYTHON="$WORK/missing" "$BASH_EXEC" "$ROOT/install.sh"
# A real isolated virtual environment supplies Python 3 but no PyQt6.
"$PYTHON" -m venv "$WORK/no-qt"
expect_failure missing-pyqt6 'python3-pyqt6' env SCREENBOT_PYTHON="$WORK/no-qt/bin/python" "$BASH_EXEC" "$ROOT/install.sh"
# Given only python on PATH, accept it when it really is Python 3.
ln -s "$PYTHON" "$WORK/bin/python"
env -u SCREENBOT_PYTHON PATH="$WORK/bin" "$BASH_EXEC" -c 'source "$1/python-runtime.sh"; screenbot_select_python; [[ "$SCREENBOT_PYTHON" == "$2/bin/python" ]]' _ "$ROOT" "$WORK"
echo 'PASS Python 3 named python accepted as fallback'
# Simulate an old Python executable rejecting the version check.
rm "$WORK/bin/python"
printf '#!%s\nexit 1\n' "$BASH_EXEC" > "$WORK/bin/python"
chmod +x "$WORK/bin/python"
expect_failure python2-fallback 'Python 3' env -u SCREENBOT_PYTHON PATH="$WORK/bin" "$BASH_EXEC" -c 'source "$1/python-runtime.sh"; screenbot_select_python' _ "$ROOT"
# A selected venv path containing spaces must remain intact for future launches.
"$PYTHON" -m venv --system-site-packages "$WORK/with qt"
env SCREENBOT_PYTHON="$WORK/with qt/bin/python" "$BASH_EXEC" -c 'source "$1/python-runtime.sh"; screenbot_select_python; [[ "$SCREENBOT_PYTHON" == "$2/with qt/bin/python" ]]; printf "%s\n" "$SCREENBOT_PYTHON" > "$2/python-path"' _ "$ROOT" "$WORK"
env -u SCREENBOT_PYTHON "$BASH_EXEC" -c 'source "$1/python-runtime.sh"; screenbot_select_python "$2/python-path"; [[ "$SCREENBOT_PYTHON" == "$2/with qt/bin/python" ]]' _ "$ROOT" "$WORK"
echo 'PASS saved venv path with spaces and PyQt6 preserved'
printf '%s\n' "$WORK/missing" > "$WORK/python-path"
expect_failure stale-interpreter 'rerun install.sh' env -u SCREENBOT_PYTHON "$BASH_EXEC" -c 'source "$1/python-runtime.sh"; screenbot_select_python "$2/python-path"' _ "$ROOT" "$WORK"
echo 'PASS interpreter selection scenarios completed'
