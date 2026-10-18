#!/usr/bin/env bash
# Manage only ScreenBot's native Plasma 6 PowerDevil idle action.
set -euo pipefail
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/powerdevilrc"
STATE="$HOME/ScreenBot/idle-trigger"
LAUNCHER="$HOME/ScreenBot/screensaver/start.sh"
COMMAND="\"$LAUNCHER\""
PROFILES=(AC Battery LowBattery)
manual_steps() {
 cat <<EOF
Manual idle setup (Plasma 6):
  1. Open System Settings > Power Management > Energy Saving.
  2. Select the On AC Power profile (and repeat for On Battery and On Low Battery).
     On newer Plasma versions these profiles appear directly on Power Management.
  3. Under Other Settings > Run command or script, choose Choose run conditions > When inactive.
     Older Plasma 6 versions call this Run Script > When idle.
  4. Choose "$LAUNCHER" and set Run after to your preferred inactivity time
     (for example, 5 minutes), then Apply.
  5. Check with: bash "$LAUNCHER" --check
To undo, clear that ScreenBot command in each profile and Apply.
Keep KDE's Screen Locking settings independent; ScreenBot is not a secure locker.
EOF
}
read_key() { kreadconfig6 --file "$CONFIG" --group "$1" --group RunScript --key "$2" --default "${3:-}"; }
write_key() { kwriteconfig6 --file "$CONFIG" --group "$1" --group RunScript --key "$2" "$3"; }
remove_key() { kwriteconfig6 --file "$CONFIG" --group "$1" --group RunScript --key "$2" --delete; }
owned_command() { [[ "$1" == "$COMMAND" || "$1" == "$LAUNCHER" ]]; }
config_tools() {
 command -v kreadconfig6 >/dev/null && command -v kwriteconfig6 >/dev/null
}
reload_config() {
 if command -v qdbus6 >/dev/null && qdbus6 org.kde.Solid.PowerManagement /org/kde/Solid/PowerManagement org.kde.Solid.PowerManagement.refreshStatus >/dev/null 2>&1; then
  echo 'PowerDevil refreshed its power profiles and idle timers.'
 else
  echo 'Log out and back in to reload PowerDevil; its session service is unavailable.'
 fi
}
case "${1:-}" in
 --instructions) manual_steps ;;
 --check)
  log="${XDG_STATE_HOME:-$HOME/.local/state}/screenbot/screenbot.log"
  last=""
  if [[ -r "$log" ]]; then
   last="$(awk '/^[0-9][0-9][0-9][0-9]-.* mode=idle outcome=/ { result=$0 } END { print result }' "$log")"
  fi
  printf 'Last automatic start: %s\nLog: %s\n' "${last:-No automatic start recorded.}" "$log"
  if [[ -f "$HOME/ScreenBot/screensaver/install-mode" ]] &&
     [[ "$(cat "$HOME/ScreenBot/screensaver/install-mode")" == standalone ]]; then
   echo 'Installation: standalone; idle activation is managed by your window manager.'
   if ! command -v pgrep >/dev/null; then
    echo 'Cannot inspect idle hooks: install procps (pgrep).'; exit 2
   fi
   found=0
   for mechanism in xidlehook xss-lock; do
    while IFS= read -r pid; do
     [[ -r "/proc/$pid/cmdline" ]] || continue
     command_line="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null)" || continue
     if [[ "$command_line" == *"$LAUNCHER"* ]]; then
      echo "Idle mechanism: $mechanism running with the ScreenBot launcher (timer is configured externally)."
      found=1
     fi
    done < <(pgrep -u "$UID" -x "$mechanism" || true)
   done
   if ((found == 0)); then
    echo 'No running xidlehook/xss-lock process referencing ScreenBot was detected. See README.md for idle setup.'
   fi
   ((found == 1)); exit
  fi
  if ! config_tools; then echo 'Cannot check idle setup: install KDE kreadconfig6 and kwriteconfig6.'; exit 2; fi
  configured=0
  for profile in "${PROFILES[@]}"; do
   if owned_command "$(read_key "$profile" IdleTimeoutCommand)"; then
    echo "$profile: ScreenBot configured after $(read_key "$profile" RunScriptIdleTimeoutSec 600) seconds."
    configured=$((configured+1))
   else
    echo "$profile: ScreenBot is not configured to start on idle."
   fi
  done
  [[ "$configured" == 3 ]]
  ;;
 --setup)
  minutes="${2:-5}"
  if [[ ! "$minutes" =~ ^[0-9]{1,3}$ ]] || ((10#$minutes < 1 || 10#$minutes > 120)); then
   echo 'Idle minutes must be an integer from 1 to 120.' >&2; exit 2
  fi
  if ! config_tools || ! command -v qdbus6 >/dev/null ||
     [[ "$(qdbus6 org.kde.Solid.PowerManagement /org/kde/Solid/PowerManagement org.kde.Solid.PowerManagement.isActionSupported RunScript 2>/dev/null || true)" != true ]]; then
   echo 'Automatic setup is unavailable: Plasma 6 PowerDevil Run Script is not accessible.'
   manual_steps; exit 1
  fi
  if [[ "$LAUNCHER" == *'"'* || "$LAUNCHER" == *$'\n'* ]]; then
   echo 'Choose the script using Plasma Settings for this home-directory name.'; manual_steps; exit 1
  fi
  for profile in "${PROFILES[@]}"; do
   current="$(read_key "$profile" IdleTimeoutCommand)"
   if [[ -n "$current" ]] && ! owned_command "$current"; then
    echo "$profile already has another idle script. It has been preserved; automatic setup was skipped."
    manual_steps; exit 1
   fi
  done
  mkdir -p "$STATE"
  chmod 700 "$STATE"
  for profile in "${PROFILES[@]}"; do
   if [[ ! -f "$STATE/$profile.timeout" ]]; then
    read_key "$profile" RunScriptIdleTimeoutSec __SCREENBOT_ABSENT__ > "$STATE/$profile.timeout"
   fi
   write_key "$profile" IdleTimeoutCommand "$COMMAND"
   write_key "$profile" RunScriptIdleTimeoutSec "$((10#$minutes * 60))"
  done
  printf '%s\n' "$((10#$minutes * 60))" > "$STATE/installed-timeout"
  reload_config
  echo "ScreenBot will start after $minutes minutes of inactivity on all three power profiles."
  ;;
 --remove)
  if [[ ! -f "$CONFIG" && ! -d "$STATE" ]]; then
   echo 'No PowerDevil configuration or managed idle trigger exists.'; exit 0
  fi
  if ! config_tools; then
   echo 'Cannot remove idle setup without KDE config tools. Clear ScreenBot under Run Script in every Power Management profile, then retry.' >&2
   exit 1
  fi
  for profile in "${PROFILES[@]}"; do
   if owned_command "$(read_key "$profile" IdleTimeoutCommand)"; then
    remove_key "$profile" IdleTimeoutCommand
    if [[ -f "$STATE/$profile.timeout" && -f "$STATE/installed-timeout" ]] &&
       [[ "$(read_key "$profile" RunScriptIdleTimeoutSec)" == "$(cat "$STATE/installed-timeout")" ]]; then
     previous="$(cat "$STATE/$profile.timeout")"
     if [[ "$previous" == __SCREENBOT_ABSENT__ ]]; then remove_key "$profile" RunScriptIdleTimeoutSec
     else write_key "$profile" RunScriptIdleTimeoutSec "$previous"; fi
    fi
    echo "Removed ScreenBot idle trigger: $profile"
   fi
  done
  rm -rf -- "$STATE"
  reload_config
  ;;
 *) echo 'Usage: idle-trigger.sh --setup MINUTES | --check | --remove | --instructions' >&2; exit 2 ;;
esac
