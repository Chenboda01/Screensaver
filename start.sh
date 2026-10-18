#!/usr/bin/env bash
# Plasma Power Management can invoke this launcher after a period of inactivity.
set -euo pipefail
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/screenbot"
LOG="$LOG_DIR/screenbot.log"
if [[ -z "${QT_QPA_PLATFORM:-}" ]]; then
    if [[ "${XDG_SESSION_TYPE:-}" == x11 || ( -z "${WAYLAND_DISPLAY:-}" && -n "${DISPLAY:-}" ) ]]; then
        export QT_QPA_PLATFORM=xcb
    else
        export QT_QPA_PLATFORM=wayland
    fi
fi

# Never persist arbitrary stderr: settings values, exception messages and Qt
# diagnostics can contain locations, photo paths, media titles or agent text.
sanitize_stderr() {
    LC_ALL=C awk '
        NF && count < 32 {
            message = "Diagnostic details omitted for privacy."
            if ($0 ~ /^ScreenBot: agent status is uncertain;/)
                message = "ScreenBot: agent status is uncertain; keeping the desktop visible."
            else if ($0 ~ /^ScreenBot: could not show the agent prompt:/)
                message = "ScreenBot: could not show the agent prompt (details omitted)."
            else if ($0 ~ /^ScreenBot: could not save the remembered agent choice\./)
                message = "ScreenBot: could not save the remembered agent choice."
            else if ($0 ~ /^(ScreenBot: )?Could not read ScreenBot settings:/)
                message = "Could not read ScreenBot settings (details omitted)."
            else if ($0 ~ /^ScreenBot: empty interpreter file /)
                message = "ScreenBot: empty interpreter file; rerun install.sh."
            else if ($0 ~ /^ScreenBot: Python 3 interpreter .* is unavailable\./)
                message = "ScreenBot: Python 3 interpreter is unavailable; rerun install.sh."
            else if ($0 ~ /^ScreenBot: .* is not a working Python 3 interpreter\./)
                message = "ScreenBot: not a working Python 3 interpreter; rerun install.sh."
            else if ($0 ~ /^ScreenBot: PyQt6 is missing from /)
                message = "ScreenBot: PyQt6 is missing; install PyQt6 for the saved interpreter."
            else if ($0 ~ /^Traceback \(most recent call last\):$/)
                message = "Traceback (most recent call last; details omitted)."
            else if ($0 ~ /^(RuntimeError|ValueError|TypeError|ImportError|ModuleNotFoundError|OSError|PermissionError|FileNotFoundError|AttributeError|KeyError|IndexError|ZeroDivisionError):/)
                { split($0, parts, ":"); message = parts[1] ": details omitted for privacy." }
            print message
            count++
        }'
}

run_logged() {
    local temporary stderr_fd sanitizer
    temporary="$(mktemp)" || return 1
    # Only the sanitizer writes to disk; raw diagnostics stay in the pipe.
    exec {stderr_fd}> >(sanitize_stderr > "$temporary")
    sanitizer=$!
    if "$@" >/dev/null 2>&"$stderr_fd"; then STATUS=0; else STATUS=$?; fi
    exec {stderr_fd}>&-
    wait "$sanitizer"
    DIAGNOSTICS="$(cat "$temporary")"
    rm -f -- "$temporary"
}

record_result() (
    umask 077
    # A separate lock survives atomic replacement of the bounded log. Logging
    # also works for the missing-flock failure, before any saver can run.
    [[ ! -L "$LOG_DIR" && ! -L "$LOG" && ! -L "$LOG_DIR/log.lock" ]] || exit 0
    mkdir -p -- "$LOG_DIR" || exit 0
    chmod 700 "$LOG_DIR" || exit 0
    exec 8>"$LOG_DIR/log.lock" || exit 0
    if command -v flock >/dev/null; then flock -x 8 || exit 0; fi
    local temporary
    temporary="$(mktemp "$LOG_DIR/.log-XXXXXX")" || exit 0
    trap 'rm -f -- "$temporary"' EXIT
    {
        if [[ -f "$LOG" ]]; then tail -c 48000 -- "$LOG" | tail -n 160; fi
        if [[ -n "${DIAGNOSTICS:-}" ]]; then
            while IFS= read -r line; do printf 'stderr (%s): %s\n' "$COMPONENT" "$line"; done <<< "$DIAGNOSTICS"
        fi
        printf '%s mode=idle outcome=%s exit=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$1" "$2"
    } | tail -c 64000 | tail -n 200 > "$temporary"
    chmod 600 "$temporary"
    mv -f -- "$temporary" "$LOG"
)

if [[ "${1:-}" == --check ]]; then
    exec bash "$(dirname -- "${BASH_SOURCE[0]}")/idle-trigger.sh" --check
fi
# Manual launches and previews keep terminal output and bypass automatic policy.
case "${1:-}" in
    --manual|--preview|--preview-bobos)
        cd "$HOME/ScreenBot/screensaver"
        source ./python-runtime.sh
        screenbot_select_python ./python-path
        [[ "$1" != --manual ]] || shift
        exec "$SCREENBOT_PYTHON" screensaver.py "$@"
        ;;
esac
if ! cd "$HOME/ScreenBot/screensaver" 2>/dev/null; then
    record_result 'failed: installation directory is unavailable' 1
    exit 1
fi
COMPONENT=runtime
select_runtime() {
    source ./python-runtime.sh || return
    screenbot_select_python ./python-path
}
run_logged select_runtime
if ((STATUS != 0)); then
    record_result "failed: ${DIAGNOSTICS%%$'\n'*}" "$STATUS"
    exit "$STATUS"
fi
if ! command -v flock >/dev/null; then
    record_result 'failed: install flock (util-linux) to enable automatic launches' 1
    exit 1
fi
if ! { exec 9>"${XDG_RUNTIME_DIR:-/tmp}/screenbot-screensaver-${UID}.lock"; } 2>/dev/null; then
    record_result 'failed: launch lock is unavailable' 1
    exit 1
fi
if flock -n 9 2>/dev/null; then :
else
    status=$?
    if ((status == 1)); then record_result 'skipped: already running' 0; exit 0; fi
    record_result 'failed: could not acquire launch lock' "$status"
    exit "$status"
fi
COMPONENT=agent_prompt
run_logged "$SCREENBOT_PYTHON" agent_prompt.py
if ((STATUS != 0)); then
    if [[ "$DIAGNOSTICS" == *'ScreenBot: agent status is uncertain;'* ]]; then
        record_result 'skipped: agent status unknown' "$STATUS"
    elif ((STATUS == 1)) && [[ "$DIAGNOSTICS" != *'could not show the agent prompt'* &&
            "$DIAGNOSTICS" != *'Traceback ('* && "$DIAGNOSTICS" != *'Error:'* ]]; then
        record_result 'skipped: user answered No (or saved/timeout policy)' "$STATUS"
    else
        FIRST_ERROR="${DIAGNOSTICS%%$'\n'*}"
        record_result "failed: ${FIRST_ERROR:-agent prompt exited without a diagnostic}" "$STATUS"
        exit "$STATUS"
    fi
    exit 0
fi
# Preserve safe prompt diagnostics even when the saver subsequently succeeds.
PROMPT_DIAGNOSTICS="$DIAGNOSTICS"
COMPONENT=screensaver
run_logged "$SCREENBOT_PYTHON" screensaver.py
FIRST_ERROR="${DIAGNOSTICS%%$'\n'*}"
DIAGNOSTICS="${PROMPT_DIAGNOSTICS:+$PROMPT_DIAGNOSTICS$'\n'}$DIAGNOSTICS"
COMPONENT=agent_prompt/screensaver
if ((STATUS == 0)); then record_result started 0
else record_result "failed: ${FIRST_ERROR:-screensaver exited without a diagnostic}" "$STATUS"; fi
exit "$STATUS"
