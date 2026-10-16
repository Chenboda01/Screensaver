#!/usr/bin/env bash
# Run the real build/install/remove lifecycle in an isolated user home.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE="${1:-$ROOT/.omo/evidence/installer}"
mkdir -p "$EVIDENCE"
EVIDENCE="$(cd "$EVIDENCE" && pwd)"
SANDBOX="$(mktemp -d "$EVIDENCE/home with spaces-XXXXXX")"
mkdir -p "$SANDBOX/bin" "$SANDBOX/.config" "$SANDBOX/.cache/screenbot"
# Only the D-Bus service boundary is substituted; native KDE config tools and CMake run.
cat > "$SANDBOX/bin/qdbus6" <<'EOF'
#!/usr/bin/env bash
if [[ "${SCREENBOT_TEST_NO_POWERDEVIL:-}" == 1 ]]; then exit 1; fi
case "$*" in
 *isActionSupported*) echo true ;;
 *reparseConfiguration*) printf 'reload\n' >> "$HOME/reloads.log" ;;
 *) exit 1 ;;
esac
EOF
chmod +x "$SANDBOX/bin/qdbus6"
run_home() {
 env HOME="$SANDBOX" XDG_CONFIG_HOME="$SANDBOX/.config" XDG_CACHE_HOME="$SANDBOX/.cache" \
     PATH="$SANDBOX/bin:$PATH" "$@"
}
read_key() { kreadconfig6 --file "$SANDBOX/.config/powerdevilrc" --group "$1" --group RunScript --key "$2" --default "${3:-}"; }
write_key() { kwriteconfig6 --file "$SANDBOX/.config/powerdevilrc" --group "$1" --group RunScript --key "$2" "$3"; }
run_home env SCREENBOT_PYTHON=/missing bash "$ROOT/install.sh" --help > "$EVIDENCE/help.log"
run_home bash "$ROOT/uninstall.sh" --help > "$EVIDENCE/uninstall-help.log"
run_home bash "$ROOT/install.sh" --no-idle > "$EVIDENCE/install-declined.log" 2>&1
[[ -f "$SANDBOX/ScreenBot/screensaver/uninstall.sh" && -s "$SANDBOX/ScreenBot/install_manifest.txt" ]]
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
echo 'PASS interactive uninstall removes every installed artifact and trigger, restores old timeout, retains personal data'
run_home bash "$ROOT/install.sh" --no-idle > "$EVIDENCE/install-after-uninstall.log" 2>&1
[[ -f "$SANDBOX/ScreenBot/screensaver/screensaver.py" ]]
cp "$SANDBOX/ScreenBot/install_manifest.txt" "$EVIDENCE/clean-manifest.txt"
printf '%s\n' "$SANDBOX/.local/keep-me" >> "$SANDBOX/ScreenBot/install_manifest.txt"
if run_home bash "$ROOT/uninstall.sh" --yes > "$EVIDENCE/unsafe-manifest.log" 2>&1; then exit 1; fi
[[ -f "$SANDBOX/.local/keep-me" && -f "$SANDBOX/ScreenBot/install_manifest.txt" ]]
cp "$EVIDENCE/clean-manifest.txt" "$SANDBOX/ScreenBot/install_manifest.txt"
run_home bash "$ROOT/uninstall.sh" --yes --keep-settings --purge-settings --purge-cache --purge-backups > "$EVIDENCE/uninstall-scripted.log"
[[ -f "$SANDBOX/.config/screenbot-screensaver.ini" && ! -e "$SANDBOX/.cache/screenbot" ]]
[[ "$(find "$SANDBOX/ScreenBot" -maxdepth 1 -type d -name 'screensaver-backup-*' | wc -l)" == 0 ]]
run_home bash "$ROOT/uninstall.sh" --yes --purge-settings > "$EVIDENCE/uninstall-idempotent.log"
[[ ! -e "$SANDBOX/.config/screenbot-screensaver.ini" && ! -e "$SANDBOX/.config/screenbot-kcm-state.ini" ]]
[[ -f "$SANDBOX/.local/keep-me" ]]
echo 'PASS reinstall, manifest safety, explicit data purges, keep-settings precedence, and repeated removal'
printf '%s\n' "$SANDBOX" > "$EVIDENCE/sandbox-path.txt"
