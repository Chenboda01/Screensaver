#!/usr/bin/env bash
set -euo pipefail
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
"$SCREENBOT_PYTHON" -m py_compile "$ROOT/screensaver.py" "$ROOT/screen_session.py" "$ROOT/agent_prompt.py" "$ROOT/bobos.py" "$ROOT/live_sky.py" "$ROOT/live_sky_network.py" "$ROOT/live_sky_render.py"
echo 'Building ScreenBot KDE Settings module...'
cmake -S "$ROOT/kcm" -B "$BUILD" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX"
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
install -m 644 "$ROOT/countries_and_cities.txt" "$DEST/countries_and_cities.txt"
install -m 755 "$ROOT/start.sh" "$DEST/start.sh"
install -m 644 "$ROOT/python-runtime.sh" "$DEST/python-runtime.sh"
printf '%s\n' "$SCREENBOT_PYTHON" > "$DEST/python-path"
echo "Using Python 3: $SCREENBOT_PYTHON"
LOCATION_DATA="$PREFIX/share/screenbot-screensaver"
mkdir -p "$LOCATION_DATA"
install -m 644 "$ROOT/countries_and_cities.txt" "$LOCATION_DATA/countries_and_cities.txt"
echo 'Installing KDE Settings module to the user-local prefix...'
cmake --install "$BUILD"
ENV_DIR="$HOME/.config/plasma-workspace/env"
ENV_FILE="$ENV_DIR/screenbot-kcm.sh"
mkdir -p "$ENV_DIR"
install -m 755 "$ROOT/plasma-session-env.sh" "$ENV_FILE"
echo 'Installed without sudo. Log out and back in for Plasma to load the user-local KDE Settings module.'
