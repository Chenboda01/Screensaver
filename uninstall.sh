#!/usr/bin/env bash
# Remove only ScreenBot-owned installation files; preserve personal data by default.
set -euo pipefail
YES=false
KEEP_SETTINGS=false
PURGE_SETTINGS=false
PURGE_CACHE=false
PURGE_BACKUPS=false
for option in "$@"; do
 case "$option" in
  --yes) YES=true ;;
  --keep-settings) KEEP_SETTINGS=true ;;
  --purge-settings) PURGE_SETTINGS=true ;;
  --purge-cache) PURGE_CACHE=true ;;
  --purge-backups) PURGE_BACKUPS=true ;;
  --help|-h)
   cat <<'EOF'
Usage: bash uninstall.sh [--yes] [--keep-settings] [--purge-settings] [--purge-cache] [--purge-backups]
Remove the ScreenBot application, KDE module, city list, Plasma environment hook,
and its idle trigger. No running agents or other applications are stopped.
  --yes             Skip the removal confirmation and retain personal data by default.
  --keep-settings   Keep settings without asking (also overrides --purge-settings).
  --purge-settings  Explicitly delete saved ScreenBot preferences.
  --purge-cache     Explicitly delete the Live Sky cache.
  --purge-backups   Explicitly delete previous installation backups.
Interactive removal asks separately about settings, cache, and backups; default No.
EOF
   exit 0 ;;
  *) echo "Unknown option: $option. See uninstall.sh --help." >&2; exit 2 ;;
 esac
done
confirm() {
 local answer
 read -r -p "$1 [y/N] " answer || return 1
 [[ "$answer" == y || "$answer" == Y || "$answer" == yes ]]
}
if ! $YES && ! confirm 'Remove ScreenBot from this account?'; then echo 'Uninstall canceled.'; exit 0; fi
BASE="$HOME/ScreenBot"
DEST="$BASE/screensaver"
PREFIX="$HOME/.local"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$DEST/idle-trigger.sh" ]]; then IDLE_HELPER="$DEST/idle-trigger.sh"
else IDLE_HELPER="$ROOT/idle-trigger.sh"; fi
bash "$IDLE_HELPER" --remove
MANIFEST="$BASE/install_manifest.txt"
if [[ -f "$MANIFEST" ]]; then
 entries=()
 while IFS= read -r entry || [[ -n "$entry" ]]; do
  [[ -n "$entry" ]] || continue
  canonical="$(realpath -m -- "$entry")"
  case "$canonical" in
   "$PREFIX"/lib*/plugins/plasma/kcms/systemsettings/kcm_screenbot_screensaver.so|\
   "$PREFIX"/share/applications/kcm_screenbot_screensaver.desktop|\
   "$PREFIX"/share/locale/*/LC_MESSAGES/kcm_screenbot_screensaver.mo)
    entries+=("$entry") ;;
   *) echo "Unsafe or unrecognized manifest entry; preserved: $entry. Review $MANIFEST before retrying." >&2; exit 1 ;;
  esac
 done < "$MANIFEST"
 for entry in "${entries[@]}"; do rm -f -- "$entry"; echo "Removed: $entry"; done
 rm -f -- "$MANIFEST"
else
 echo 'No install manifest found; removing known legacy ScreenBot module paths.'
 for entry in "$PREFIX"/lib/plugins/plasma/kcms/systemsettings/kcm_screenbot_screensaver.so \
              "$PREFIX"/lib/qt6/plugins/plasma/kcms/systemsettings/kcm_screenbot_screensaver.so \
              "$PREFIX"/lib64/qt6/plugins/plasma/kcms/systemsettings/kcm_screenbot_screensaver.so \
              "$PREFIX"/share/applications/kcm_screenbot_screensaver.desktop; do
  rm -f -- "$entry"
 done
fi
rm -f -- "$PREFIX/share/screenbot-screensaver/countries_and_cities.txt" "$CONFIG_HOME/plasma-workspace/env/screenbot-kcm.sh"
echo 'Removed the city list and Plasma environment hook.'
if ! $YES; then
 if ! $KEEP_SETTINGS && ! $PURGE_SETTINGS && confirm 'Delete saved ScreenBot settings?'; then PURGE_SETTINGS=true; fi
 if ! $PURGE_CACHE && confirm 'Delete the Live Sky cache?'; then PURGE_CACHE=true; fi
 if ! $PURGE_BACKUPS && confirm 'Delete all previous ScreenBot installation backups?'; then PURGE_BACKUPS=true; fi
fi
if $PURGE_SETTINGS && ! $KEEP_SETTINGS; then
 rm -f -- "$CONFIG_HOME/screenbot-screensaver.ini" "$CONFIG_HOME/screenbot-kcm-state.ini"
 echo 'Removed saved ScreenBot settings.'
else echo 'Kept saved ScreenBot settings.'; fi
if $PURGE_CACHE; then
 rm -rf -- "${XDG_CACHE_HOME:-$HOME/.cache}/screenbot"
 echo 'Removed Live Sky cache.'
else echo 'Kept Live Sky cache.'; fi
if $PURGE_BACKUPS; then
 if [[ -d "$BASE" ]]; then
  find "$BASE" -mindepth 1 -maxdepth 1 -type d -name 'screensaver-backup-*' -exec rm -rf -- {} +
 fi
 echo 'Removed previous installation backups.'
else echo 'Kept previous installation backups.'; fi
rm -rf -- "$DEST"
echo "Removed: $DEST"
echo 'ScreenBot is uninstalled. Log out and back in to remove its page from System Settings.'
