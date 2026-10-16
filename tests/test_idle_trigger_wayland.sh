#!/usr/bin/env bash
# Optional real-compositor integration test; requires KWin, PowerDevil, and build deps.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE="${1:-$ROOT/.omo/evidence/idle-wayland-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$EVIDENCE"
EVIDENCE="$(cd "$EVIDENCE" && pwd)"
[[ ! -e "$EVIDENCE/home" ]] || { echo 'Use a fresh evidence directory.' >&2; exit 2; }
for tool in kwin_wayland dbus-run-session qdbus6 kreadconfig6 kwriteconfig6 timeout; do command -v "$tool" >/dev/null; done
POWERDEVIL="${SCREENBOT_POWERDEVIL:-/usr/lib/org_kde_powerdevil}"
[[ -x "$POWERDEVIL" ]] || { echo 'Set SCREENBOT_POWERDEVIL to the PowerDevil executable.' >&2; exit 2; }
source "$ROOT/python-runtime.sh"
screenbot_select_python
TEST_HOME="$EVIDENCE/home"
mkdir -p "$TEST_HOME/.config"
RUNTIME="$(mktemp -d /tmp/screenbot-idle-XXXXXX)"
cleanup() {
 if [[ -f "$RUNTIME/screenbot-screensaver-${UID}.lock" ]]; then
  unlink "$RUNTIME/screenbot-screensaver-${UID}.lock"
 fi
 rmdir "$RUNTIME" 2>/dev/null || true
}
trap cleanup EXIT
export SCREENBOT_IDLE_EVIDENCE="$EVIDENCE" SCREENBOT_POWERDEVIL="$POWERDEVIL"
export SCREENBOT_PYTHON
COMMON=("HOME=$TEST_HOME" "XDG_CONFIG_HOME=$TEST_HOME/.config" "XDG_CACHE_HOME=$TEST_HOME/.cache" "XDG_RUNTIME_DIR=$RUNTIME")
env "${COMMON[@]}" bash "$ROOT/install.sh" --no-idle > "$EVIDENCE/install.log" 2>&1
DEST="$TEST_HOME/ScreenBot/screensaver"
# The two observers only record entry/frame timing and inject a close key.
mv "$DEST/screensaver.py" "$DEST/screenbot_real_entry.py"
install -m 644 "$ROOT/tests/idle_wayland/capture.py" "$DEST/screensaver.py"
mv "$DEST/start.sh" "$DEST/start-real.sh"
cat > "$DEST/start.sh" <<'EOF'
#!/usr/bin/env bash
cut -d' ' -f1 /proc/uptime >> "$SCREENBOT_IDLE_EVIDENCE/action-monotonic.txt"
exec bash "$HOME/ScreenBot/screensaver/start-real.sh" "$@"
EOF
chmod +x "$DEST/start.sh"
cat > "$TEST_HOME/.config/screenbot-screensaver.ini" <<'EOF'
[Screensaver]
theme=forest
password_lock=false
bobos_enabled=false
live_sky_enabled=false
agent_detection_mode=start
show_agent_status=false
EOF
# No services may auto-activate; both bus endpoints are private, including system bus.
env "${COMMON[@]}" WAYLAND_DISPLAY=sb-idle QT_QPA_PLATFORM=wayland LIBGL_ALWAYS_SOFTWARE=1 KDE_DEBUG=1 \
 timeout --foreground 180 dbus-run-session --config-file="$ROOT/tests/idle_wayland/private-bus.conf" -- \
 bash -c 'export DBUS_SYSTEM_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS"; exec kwin_wayland --virtual --no-lockscreen --no-global-shortcuts --no-kactivities --socket sb-idle --exit-with-session "$1"' \
 _ "$ROOT/tests/idle_wayland/session.sh" > "$EVIDENCE/session.log" 2>&1
cat "$EVIDENCE/session.log"
