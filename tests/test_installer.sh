#!/usr/bin/env bash
# Run the real build/install/remove lifecycle in an isolated user home.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE="${1:-$ROOT/.omo/evidence/installer}"
mkdir -p "$EVIDENCE"
EVIDENCE="$(cd "$EVIDENCE" && pwd)"
SANDBOX="$(mktemp -d "$EVIDENCE/home with spaces-XXXXXX")"
mkdir -p "$SANDBOX/bin" "$SANDBOX/.config" "$SANDBOX/.cache/screenbot" "$SANDBOX/runtime"
# Only the D-Bus service boundary is substituted; native KDE config tools and CMake run.
cat > "$SANDBOX/bin/qdbus6" <<'EOF'
#!/usr/bin/env bash
if [[ "${SCREENBOT_TEST_NO_POWERDEVIL:-}" == 1 ]]; then exit 1; fi
case "$*" in
 *isActionSupported*) echo true ;;
 *refreshStatus*) printf 'reload\n' >> "$HOME/reloads.log" ;;
 *) exit 1 ;;
esac
EOF
chmod +x "$SANDBOX/bin/qdbus6"
run_home() {
 env HOME="$SANDBOX" XDG_CONFIG_HOME="$SANDBOX/.config" XDG_CACHE_HOME="$SANDBOX/.cache" \
     XDG_STATE_HOME="$SANDBOX/.local/state" XDG_RUNTIME_DIR="$SANDBOX/runtime" \
     PATH="$SANDBOX/bin:$PATH" "$@"
}
read_key() { kreadconfig6 --file "$SANDBOX/.config/powerdevilrc" --group "$1" --group RunScript --key "$2" --default "${3:-}"; }
write_key() { kwriteconfig6 --file "$SANDBOX/.config/powerdevilrc" --group "$1" --group RunScript --key "$2" "$3"; }
run_home env SCREENBOT_PYTHON=/missing bash "$ROOT/install.sh" --help > "$EVIDENCE/help.log"
run_home bash "$ROOT/uninstall.sh" --help > "$EVIDENCE/uninstall-help.log"
run_home bash "$ROOT/install.sh" --no-idle > "$EVIDENCE/install-declined.log" 2>&1
[[ -f "$SANDBOX/ScreenBot/screensaver/uninstall.sh" && -s "$SANDBOX/ScreenBot/install_manifest.txt" ]]
[[ -f "$SANDBOX/ScreenBot/screensaver/screenbot/app.py" ]]
[[ -f "$SANDBOX/ScreenBot/screensaver/screenbot/themes/space.py" ]]
[[ -f "$SANDBOX/ScreenBot/screensaver/facts/facts.json" ]]
[[ -f "$SANDBOX/ScreenBot/screensaver/facts/quotes.json" ]]
[[ -f "$SANDBOX/ScreenBot/screensaver/facts/translations/es.json" ]]
[[ ! -e "$SANDBOX/.config/powerdevilrc" ]]
while IFS= read -r entry; do [[ -z "$entry" || -f "$entry" ]]; done < "$SANDBOX/ScreenBot/install_manifest.txt"
echo 'PASS actual user-prefix install, persisted manifest, no-idle leaves PowerDevil untouched'
if run_home bash "$SANDBOX/ScreenBot/screensaver/start.sh" --check > "$EVIDENCE/check-unconfigured.log"; then exit 1; fi
write_key AC IdleTimeoutCommand /existing/user-script
if run_home bash "$ROOT/idle-trigger.sh" --setup 2 > "$EVIDENCE/conflict.log"; then exit 1; fi
[[ "$(read_key AC IdleTimeoutCommand)" == /existing/user-script ]]
[[ "$(read_key Battery IdleTimeoutCommand)" == '' ]]
write_key AC IdleTimeoutCommand ''
write_key AC RunScriptIdleTimeoutSec 777
if run_home env SCREENBOT_TEST_NO_POWERDEVIL=1 bash "$ROOT/idle-trigger.sh" --setup 2 > "$EVIDENCE/unavailable.log"; then exit 1; fi
[[ "$(read_key AC IdleTimeoutCommand)" == '' ]]
echo 'PASS unrelated idle command and unavailable daemon leave profiles unchanged'
printf '[Screensaver]\ntheme=forest\n' > "$SANDBOX/.config/screenbot-screensaver.ini"
printf '[Sections]\nTheme=false\n' > "$SANDBOX/.config/screenbot-kcm-state.ini"
printf '{}\n' > "$SANDBOX/.cache/screenbot/live-sky.json"
printf 'y\n1\n' | run_home bash "$ROOT/install.sh" > "$EVIDENCE/install-enabled.log" 2>&1
run_home bash "$SANDBOX/ScreenBot/screensaver/start.sh" --check > "$EVIDENCE/check-configured.log"
for profile in AC Battery LowBattery; do
 [[ "$(read_key "$profile" IdleTimeoutCommand)" == "\"$SANDBOX/ScreenBot/screensaver/start.sh\"" ]]
 [[ "$(read_key "$profile" RunScriptIdleTimeoutSec)" == 60 ]]
done
[[ -s "$SANDBOX/reloads.log" ]]
for iteration in 1 2 3; do
 run_home bash "$ROOT/install.sh" --no-idle > "$EVIDENCE/reinstall-$iteration.log" 2>&1
done
[[ "$(find "$SANDBOX/ScreenBot" -maxdepth 1 -type d -name 'screensaver-backup-*' | wc -l)" == 3 ]]
echo 'PASS explicit setup configures all profiles and repeated installs retain three backups'
# Exercise the installed launcher with a deterministic interpreter boundary.
# Native bash, flock, filesystem permissions, KDE config tools and runtime
# selection remain real; no fullscreen saver or agent dialog is opened.
cat > "$SANDBOX/bin/test-python" <<'EOF_PYTHON'
#!/usr/bin/env bash
case "$1" in
 -c)
  [[ "$2" != 'import PyQt6' || "${TEST_OUTCOME:-}" != missing-qt ]]
  ;;
 agent_prompt.py)
  case "${TEST_OUTCOME:-}" in
   no) exit 1 ;;
   no-warning) echo 'Qt: /private/secret-photo Taipei 25.03,121.56 Secret Song AGENT_PROMPT_SECRET' >&2; exit 1 ;;
   unknown-warning)
    echo 'Qt: /private/secret-photo Taipei 25.03,121.56 Secret Song AGENT_PROMPT_SECRET' >&2
    echo 'ScreenBot: agent status is uncertain; keeping the desktop visible.' >&2; exit 1 ;;
   unknown) echo 'ScreenBot: agent status is uncertain; keeping the desktop visible.' >&2; exit 1 ;;
   prompt-error) echo 'ScreenBot: could not show the agent prompt: /private/secret-photo Taipei 25.03,121.56 Secret Song AGENT_PROMPT_SECRET' >&2; exit 1 ;;
  esac
  ;;
 screensaver.py)
  case "${TEST_OUTCOME:-}" in
   render-error)
    printf '%s\n' 'Traceback (most recent call last):' '  File "/private/secret-photo", line 5' 'ValueError: Taipei 25.03,121.56 Secret Song AGENT_PROMPT_SECRET' >&2
    exit 7 ;;
   settings-error) echo 'Could not read ScreenBot settings: /private/secret-photo Taipei 25.03,121.56 Secret Song AGENT_PROMPT_SECRET' >&2; exit 2 ;;
   noisy)
    for ((i=0; i<300; i++)); do printf '%s\n' 'Private Taipei 25.03,121.56 /private/secret-photo Secret Song AGENT_PROMPT_SECRET' >&2; done ;;
   *) echo 'manual stdout visible'; echo 'manual stderr visible' >&2 ;;
  esac
  ;;
 *) exit 3 ;;
esac
EOF_PYTHON
chmod +x "$SANDBOX/bin/test-python"
LOG="$SANDBOX/.local/state/screenbot/screenbot.log"
LAUNCHER="$SANDBOX/ScreenBot/screensaver/start.sh"
run_launch() {
 local name="$1" expected_status="$2" expected_result="$3" status=0 before=0 after
 shift 3
 [[ ! -f "$LOG" ]] || before="$(grep -c ' mode=idle outcome=' "$LOG" || true)"
 run_home env SCREENBOT_PYTHON="$SANDBOX/bin/test-python" "$@" bash "$LAUNCHER" > "$EVIDENCE/launch-$name.stdout" 2> "$EVIDENCE/launch-$name.stderr" || status=$?
 [[ "$status" == "$expected_status" ]]
 after="$(grep -c ' mode=idle outcome=' "$LOG")"
 [[ "$after" == "$((before+1))" ]]
 tail -n 1 "$LOG" | grep -F -- "$expected_result" > "$EVIDENCE/launch-$name.result"
 [[ "$(stat -c %a "$LOG")" == 600 ]]
 [[ "$(stat -c %a "$(dirname "$LOG")")" == 700 ]]
 [[ ! -s "$EVIDENCE/launch-$name.stdout" && ! -s "$EVIDENCE/launch-$name.stderr" ]]
 echo "PASS automatic $name: $expected_result"
}
run_launch success 0 'mode=idle outcome=started exit=0'
run_launch no 0 'outcome=skipped: user answered No (or saved/timeout policy) exit=1' TEST_OUTCOME=no
run_launch unknown 0 'outcome=skipped: agent status unknown exit=1' TEST_OUTCOME=unknown
run_launch no-warning 0 'outcome=skipped: user answered No (or saved/timeout policy) exit=1' TEST_OUTCOME=no-warning
run_launch unknown-warning 0 'outcome=skipped: agent status unknown exit=1' TEST_OUTCOME=unknown-warning
run_launch prompt-error 1 'outcome=failed: ScreenBot: could not show the agent prompt (details omitted). exit=1' TEST_OUTCOME=prompt-error
run_launch render-error 7 'outcome=failed: Traceback (most recent call last; details omitted). exit=7' TEST_OUTCOME=render-error
run_launch settings-error 2 'outcome=failed: Could not read ScreenBot settings (details omitted). exit=2' TEST_OUTCOME=settings-error
run_launch missing-qt 1 'outcome=failed: ScreenBot: PyQt6 is missing; install PyQt6 for the saved interpreter. exit=1' TEST_OUTCOME=missing-qt
run_launch missing-python 1 'outcome=failed: ScreenBot: Python 3 interpreter is unavailable; rerun install.sh. exit=1' SCREENBOT_PYTHON=/private/secret-photo
exec 7>"$SANDBOX/runtime/screenbot-screensaver-${UID}.lock"
flock -n 7
run_launch already-running 0 'outcome=skipped: already running exit=0'
flock -u 7
exec 7>&-
# A PATH without flock must still produce a useful private failure log.
mkdir "$SANDBOX/no-flock"
for utility in bash dirname basename mktemp cat rm awk mkdir chmod tail date mv; do
 ln -s "$(command -v "$utility")" "$SANDBOX/no-flock/$utility"
done
run_launch missing-flock 1 'outcome=failed: install flock (util-linux) to enable automatic launches exit=1' PATH="$SANDBOX/no-flock"
run_home bash "$LAUNCHER" --check > "$EVIDENCE/check-last-failure.log"
run_home bash "$SANDBOX/ScreenBot/screensaver/idle-trigger.sh" --check > "$EVIDENCE/check-idle-last-failure.log"
for check in "$EVIDENCE/check-last-failure.log" "$EVIDENCE/check-idle-last-failure.log"; do
 grep -F 'Last automatic start:' "$check" >/dev/null
 grep -F 'failed: install flock' "$check" >/dev/null
 grep -F "Log: $LOG" "$check" >/dev/null
done
if run_home env PATH="$SANDBOX/no-flock" bash "$LAUNCHER" --check > "$EVIDENCE/check-without-kde.log"; then exit 1; fi
grep -F 'failed: install flock' "$EVIDENCE/check-without-kde.log" >/dev/null
cp "$LOG" "$EVIDENCE/automatic-outcomes.log"
checksum="$(sha256sum "$LOG")"
for mode in --manual --preview --preview-bobos; do
 run_home env SCREENBOT_PYTHON="$SANDBOX/bin/test-python" TEST_OUTCOME=no bash "$LAUNCHER" "$mode" > "$EVIDENCE/$mode.stdout" 2> "$EVIDENCE/$mode.stderr"
 grep -Fx 'manual stdout visible' "$EVIDENCE/$mode.stdout" >/dev/null
 grep -Fx 'manual stderr visible' "$EVIDENCE/$mode.stderr" >/dev/null
done
[[ "$(sha256sum "$LOG")" == "$checksum" ]]
echo 'PASS manual/preview terminal output is retained without modifying the automatic log'
# XDG default and explicit state locations both work; unrelated state survives.
run_home env -u XDG_STATE_HOME SCREENBOT_PYTHON="$SANDBOX/bin/test-python" bash "$LAUNCHER"
CUSTOM_STATE="$SANDBOX/custom state"
run_home env XDG_STATE_HOME="$CUSTOM_STATE" SCREENBOT_PYTHON="$SANDBOX/bin/test-python" bash "$LAUNCHER"
[[ -s "$CUSTOM_STATE/screenbot/screenbot.log" && "$(stat -c %a "$CUSTOM_STATE/screenbot/screenbot.log")" == 600 ]]
cp "$CUSTOM_STATE/screenbot/screenbot.log" "$EVIDENCE/custom-state.log"
# Concurrent triggers must not lose outcomes while atomically trimming the log.
before="$(grep -c ' mode=idle outcome=' "$LOG")"
pids=()
for ((i=0; i<12; i++)); do
 run_home env SCREENBOT_PYTHON="$SANDBOX/bin/test-python" bash "$LAUNCHER" &
 pids+=("$!")
done
for pid in "${pids[@]}"; do wait "$pid"; done
[[ "$(grep -c ' mode=idle outcome=' "$LOG")" == "$((before+12))" ]]
cp "$LOG" "$EVIDENCE/concurrent-outcomes.log"
for ((i=0; i<210; i++)); do
 run_home env SCREENBOT_PYTHON="$SANDBOX/bin/test-python" TEST_OUTCOME=noisy bash "$LAUNCHER"
 [[ "$(wc -l < "$LOG")" -le 200 && "$(wc -c < "$LOG")" -le 64000 ]]
done
cp "$LOG" "$EVIDENCE/bounded-private.log"
if grep -E 'Taipei|25\.03|121\.56|secret-photo|Secret Song|AGENT_PROMPT_SECRET|/private' "$EVIDENCE/automatic-outcomes.log" "$EVIDENCE/bounded-private.log"; then exit 1; fi
# The first error line is retained as a safe summary, and exception type survives.
grep -F 'ValueError: details omitted for privacy.' "$EVIDENCE/automatic-outcomes.log" >/dev/null
printf 'mode=%s lines=%s bytes=%s\n' "$(stat -c %a "$LOG")" "$(wc -l < "$LOG")" "$(wc -c < "$LOG")" > "$EVIDENCE/log-bounds.txt"
echo 'PASS XDG state locations, concurrent outcomes, stderr redaction, 210 noisy launches and log bounds'
printf 'keep\n' > "$SANDBOX/.local/state/screenbot/unrelated"

printf 'unrelated\n' > "$SANDBOX/.local/keep-me"
cp "$SANDBOX/ScreenBot/install_manifest.txt" "$EVIDENCE/installed-files.txt"
write_key Battery IdleTimeoutCommand /later/user-script
printf 'y\nn\nn\nn\n' | run_home bash "$SANDBOX/ScreenBot/screensaver/uninstall.sh" > "$EVIDENCE/uninstall-default.log"
[[ ! -e "$SANDBOX/ScreenBot/screensaver" && ! -e "$SANDBOX/ScreenBot/install_manifest.txt" ]]
[[ ! -e "$SANDBOX/.config/plasma-workspace/env/screenbot-kcm.sh" ]]
[[ ! -e "$SANDBOX/.local/share/screenbot-screensaver/countries_and_cities.txt" ]]
while IFS= read -r entry; do [[ -z "$entry" || ! -e "$entry" ]]; done < "$EVIDENCE/installed-files.txt"
[[ -f "$SANDBOX/.config/screenbot-screensaver.ini" && -f "$SANDBOX/.cache/screenbot/live-sky.json" ]]
[[ -f "$SANDBOX/.config/screenbot-kcm-state.ini" && -f "$SANDBOX/.local/keep-me" ]]
[[ "$(read_key AC RunScriptIdleTimeoutSec)" == 777 ]]
for profile in AC LowBattery; do [[ -z "$(read_key "$profile" IdleTimeoutCommand)" ]]; done
[[ "$(read_key Battery IdleTimeoutCommand)" == /later/user-script ]]
[[ ! -e "$LOG" && ! -e "$SANDBOX/.local/state/screenbot/log.lock" ]]
[[ -f "$SANDBOX/.local/state/screenbot/unrelated" ]]
echo 'PASS automatic log removed by default while unrelated state is retained'
echo 'PASS interactive uninstall removes every installed artifact and trigger, restores old timeout, retains personal data'
run_home bash "$ROOT/install.sh" --no-idle > "$EVIDENCE/install-after-uninstall.log" 2>&1
[[ -f "$SANDBOX/ScreenBot/screensaver/screensaver.py" ]]
[[ -f "$SANDBOX/ScreenBot/screensaver/screenbot/phone/apps.py" ]]
[[ -f "$SANDBOX/ScreenBot/screensaver/facts/facts.json" && -f "$SANDBOX/ScreenBot/screensaver/facts/quotes.json" ]]
[[ -f "$SANDBOX/ScreenBot/screensaver/facts/translations/es.json" ]]
cp "$SANDBOX/ScreenBot/install_manifest.txt" "$EVIDENCE/clean-manifest.txt"
printf '%s\n' "$SANDBOX/.local/keep-me" >> "$SANDBOX/ScreenBot/install_manifest.txt"
if run_home bash "$ROOT/uninstall.sh" --yes > "$EVIDENCE/unsafe-manifest.log" 2>&1; then exit 1; fi
[[ -f "$SANDBOX/.local/keep-me" && -f "$SANDBOX/ScreenBot/install_manifest.txt" ]]
cp "$EVIDENCE/clean-manifest.txt" "$SANDBOX/ScreenBot/install_manifest.txt"
run_home bash "$ROOT/uninstall.sh" --yes --keep-settings --purge-settings --purge-cache --purge-backups > "$EVIDENCE/uninstall-scripted.log"
[[ -f "$SANDBOX/.config/screenbot-screensaver.ini" && ! -e "$SANDBOX/.cache/screenbot" ]]
[[ "$(find "$SANDBOX/ScreenBot" -maxdepth 1 -type d -name 'screensaver-backup-*' | wc -l)" == 0 ]]
run_home env XDG_STATE_HOME="$CUSTOM_STATE" bash "$ROOT/uninstall.sh" --yes --purge-settings > "$EVIDENCE/uninstall-idempotent.log"
[[ ! -e "$SANDBOX/.config/screenbot-screensaver.ini" && ! -e "$SANDBOX/.config/screenbot-kcm-state.ini" ]]
[[ -f "$SANDBOX/.local/keep-me" ]]
[[ ! -e "$CUSTOM_STATE/screenbot/screenbot.log" ]]
echo 'PASS explicit XDG state log removed on repeated uninstall'
echo 'PASS reinstall, manifest safety, explicit data purges, keep-settings precedence, and repeated removal'
printf '%s\n' "$SANDBOX" > "$EVIDENCE/sandbox-path.txt"
