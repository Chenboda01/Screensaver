#!/usr/bin/env bash
set -euo pipefail
IDLE=ask
MINUTES=5
while (($#)); do
 case "$1" in
  --help|-h)
   cat <<'EOF'
Usage: bash install.sh [--idle-minutes N | --no-idle]
Install ScreenBot and its KDE settings module into your account, without sudo.
  --idle-minutes N  Enable Plasma's idle trigger after 1-120 minutes (explicit consent).
  --no-idle         Leave idle configuration unchanged and print manual setup steps.
  --help           Show this help without building or modifying files.
Without an option, ask whether to enable idle start (default 5 minutes).
Non-interactive input defaults to leaving idle configuration unchanged.
SCREENBOT_PYTHON selects the Python 3 interpreter with PyQt6.
The three newest installation backups are kept in ~/ScreenBot/.
Uninstall with: bash ~/ScreenBot/screensaver/uninstall.sh
EOF
   exit 0 ;;
  --idle-minutes)
   [[ $# -ge 2 && "$2" =~ ^[0-9]{1,3}$ ]] && ((10#$2 >= 1 && 10#$2 <= 120)) || { echo 'Expected --idle-minutes 1-120.' >&2; exit 2; }
   IDLE=yes; MINUTES="$2"; shift 2 ;;
  --no-idle) IDLE=no; shift ;;
  *) echo "Unknown option: $1. See install.sh --help." >&2; exit 2 ;;
 esac
done
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/ScreenBot/screensaver"
PREFIX="$HOME/.local"
BUILD="$ROOT/build-user-local"
if [[ "$ROOT" == "$DEST" ]]; then
 echo 'Extract the ZIP outside ~/ScreenBot/screensaver, then run install.sh.' >&2
 exit 1
fi
source "$ROOT/python-runtime.sh"
screenbot_select_python
for tool in cmake c++ make bash flock; do
 command -v "$tool" >/dev/null || { echo "Missing $tool; install CMake and build tools first." >&2; exit 1; }
done
mapfile -d '' RUNTIME_MODULES < <(find "$ROOT/screenbot" -type f -name '*.py' -print0)
"$SCREENBOT_PYTHON" -m py_compile "$ROOT/screensaver.py" "$ROOT/screen_session.py" "$ROOT/agent_prompt.py" "$ROOT/bobos.py" "$ROOT/live_sky.py" "$ROOT/live_sky_network.py" "$ROOT/live_sky_render.py" "${RUNTIME_MODULES[@]}"
echo 'Building ScreenBot KDE Settings module...'
cmake -S "$ROOT/kcm" -B "$BUILD" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX" -DBUILD_TESTING=OFF
cmake --build "$BUILD" --parallel 2
# Only change working screensaver after the full build succeeds.
mkdir -p "$HOME/ScreenBot"
if [[ -d "$DEST" ]]; then
 BACKUP="$HOME/ScreenBot/screensaver-backup-$(date +%Y%m%d-%H%M%S)-$$"
 cp -a "$DEST" "$BACKUP"
 echo "Backup saved: $BACKUP"
fi
mkdir -p "$DEST"
install -m 644 "$ROOT/screensaver.py" "$DEST/screensaver.py"
install -m 644 "$ROOT/screen_session.py" "$DEST/screen_session.py"
install -m 644 "$ROOT/agent_prompt.py" "$DEST/agent_prompt.py"
install -m 644 "$ROOT/bobos.py" "$DEST/bobos.py"
install -m 644 "$ROOT/live_sky.py" "$DEST/live_sky.py"
install -m 644 "$ROOT/live_sky_network.py" "$DEST/live_sky_network.py"
install -m 644 "$ROOT/live_sky_render.py" "$DEST/live_sky_render.py"
while IFS= read -r -d '' MODULE; do
 RELATIVE_PATH="${MODULE#"$ROOT"/}"
 install -D -m 644 "$MODULE" "$DEST/$RELATIVE_PATH"
done < <(find "$ROOT/screenbot" -type f -name '*.py' -print0)
install -m 644 "$ROOT/countries_and_cities.txt" "$DEST/countries_and_cities.txt"
install -m 755 "$ROOT/start.sh" "$DEST/start.sh"
install -m 755 "$ROOT/idle-trigger.sh" "$DEST/idle-trigger.sh"
install -m 755 "$ROOT/uninstall.sh" "$DEST/uninstall.sh"
install -m 644 "$ROOT/python-runtime.sh" "$DEST/python-runtime.sh"
printf '%s\n' "$SCREENBOT_PYTHON" > "$DEST/python-path"
echo "Using Python 3: $SCREENBOT_PYTHON"
LOCATION_DATA="$PREFIX/share/screenbot-screensaver"
mkdir -p "$LOCATION_DATA"
install -m 644 "$ROOT/countries_and_cities.txt" "$LOCATION_DATA/countries_and_cities.txt"
echo 'Installing KDE Settings module to the user-local prefix...'
cmake --install "$BUILD"
MANIFEST="$HOME/ScreenBot/install_manifest.txt"
{ [[ ! -f "$MANIFEST" ]] || cat "$MANIFEST"; cat "$BUILD/install_manifest.txt"; printf '\n'; } | sort -u > "$MANIFEST.new"
mv "$MANIFEST.new" "$MANIFEST"
ENV_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/plasma-workspace/env"
ENV_FILE="$ENV_DIR/screenbot-kcm.sh"
mkdir -p "$ENV_DIR"
install -m 755 "$ROOT/plasma-session-env.sh" "$ENV_FILE"
mapfile -t BACKUPS < <(find "$HOME/ScreenBot" -mindepth 1 -maxdepth 1 -type d -name 'screensaver-backup-*' -printf '%f\n' | sort -r)
for BACKUP in "${BACKUPS[@]:3}"; do
 rm -rf -- "$HOME/ScreenBot/$BACKUP"
 echo "Removed old installation backup: $BACKUP"
done
if [[ "$IDLE" == ask ]]; then
 read -r -p 'Start ScreenBot automatically when idle? [Y/n] ' ANSWER || ANSWER=n
 case "$ANSWER" in
  ''|y|Y|yes|Yes)
   IDLE=yes
   read -r -p 'Minutes of inactivity [5]: ' MINUTES || MINUTES=5
   MINUTES="${MINUTES:-5}" ;;
  *) IDLE=no ;;
 esac
fi
if [[ "$IDLE" == yes ]]; then
 bash "$DEST/idle-trigger.sh" --setup "$MINUTES" || {
  echo 'ScreenBot is installed; automatic idle setup did not complete.'
  bash "$DEST/idle-trigger.sh" --instructions
 }
else
 bash "$DEST/idle-trigger.sh" --instructions
fi
echo 'Installed without sudo. Log out and back in for Plasma to load the user-local KDE Settings module.'
