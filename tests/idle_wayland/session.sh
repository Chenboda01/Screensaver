#!/usr/bin/env bash
# Runs only inside the private bus and virtual compositor created by the test.
set -euo pipefail
[[ "$DBUS_SYSTEM_BUS_ADDRESS" == "$DBUS_SESSION_BUS_ADDRESS" ]]
[[ "$XDG_RUNTIME_DIR" == /tmp/screenbot-idle-* ]]
POWER_PID=
stop_powerdevil() {
 if [[ -n "$POWER_PID" ]]; then
  kill "$POWER_PID" 2>/dev/null || true
  wait "$POWER_PID" 2>/dev/null || true
  POWER_PID=
 fi
}
MOCK_PIDS=()
cleanup() {
 stop_powerdevil
 for pid in "${MOCK_PIDS[@]}"; do kill "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true; done
}
trap cleanup EXIT
# Only hardware services are mocked; KWin and PowerDevil dispatch the real idle event.
for template in upower logind; do
 "$SCREENBOT_PYTHON" -m dbusmock --system -t "$template" > "$SCREENBOT_IDLE_EVIDENCE/mock-$template.log" 2>&1 &
 MOCK_PIDS+=("$!")
done
for service in org.freedesktop.UPower org.freedesktop.login1; do
 ready=false
 for attempt in {1..100}; do
  if [[ "$(qdbus6 org.freedesktop.DBus / org.freedesktop.DBus.NameHasOwner "$service")" == true ]]; then ready=true; break; fi
  sleep .1
 done
 "$ready" || { echo "FAIL private power service unavailable: $service" >&2; exit 1; }
done
start_powerdevil() {
 "$SCREENBOT_POWERDEVIL" > "$SCREENBOT_IDLE_EVIDENCE/powerdevil-$1.log" 2>&1 &
 POWER_PID=$!
 for attempt in {1..100}; do
  if [[ "$(qdbus6 org.kde.Solid.PowerManagement /org/kde/Solid/PowerManagement org.kde.Solid.PowerManagement.currentProfile 2>/dev/null || true)" == AC ]]; then return; fi
  sleep .1
 done
 echo 'FAIL private PowerDevil did not initialize its AC profile.' >&2
 exit 1
}
start_powerdevil before
DEST="$HOME/ScreenBot/screensaver"
cut -d' ' -f1 /proc/uptime > "$SCREENBOT_IDLE_EVIDENCE/setup-monotonic.txt"
bash "$DEST/idle-trigger.sh" --setup 1 > "$SCREENBOT_IDLE_EVIDENCE/setup.log"
for ((attempt=0; attempt<SCREENBOT_IDLE_MAX_SECONDS; attempt++)); do
 if [[ -s "$SCREENBOT_IDLE_EVIDENCE/frames.jsonl" ]]; then break; fi
 sleep 1
done
"$SCREENBOT_PYTHON" - <<'PY'
import json
import os
from pathlib import Path
root = Path(os.environ['SCREENBOT_IDLE_EVIDENCE'])
assert (root/'action-monotonic.txt').exists(), 'PowerDevil did not execute the configured idle action'
assert (root/'frames.jsonl').exists(), 'ScreenBot did not render after its idle action'
started = float((root/'setup-monotonic.txt').read_text())
fired = float((root/'action-monotonic.txt').read_text())
frames = [json.loads(line) for line in (root/'frames.jsonl').read_text().splitlines()]
assert 55 <= fired-started <= int(os.environ["SCREENBOT_IDLE_MAX_SECONDS"]), (started, fired)
assert len(frames) == 1 and frames[0]['fullscreen'] and not frames[0]['preview'], frames
assert not frames[0]['password_lock'], frames
(root/'timing.json').write_text(json.dumps({'setup_monotonic': started, 'action_monotonic': fired, 'elapsed_seconds': fired-started, 'frame': frames[0]}, indent=2)+'\n')
print(f'PASS real Wayland idle action launched full-screen ScreenBot after {fired-started:.2f} seconds')
PY
bash "$DEST/uninstall.sh" --yes --keep-settings > "$SCREENBOT_IDLE_EVIDENCE/uninstall.log"
[[ ! -e "$DEST/start.sh" ]]
stop_powerdevil
start_powerdevil after
# A new PowerDevil instance models the next login after uninstall.
sleep 65
[[ "$(wc -l < "$SCREENBOT_IDLE_EVIDENCE/action-monotonic.txt")" == 1 ]]
[[ "$(wc -l < "$SCREENBOT_IDLE_EVIDENCE/frames.jsonl")" == 1 ]]
for profile in AC Battery LowBattery; do
 [[ -z "$(kreadconfig6 --file "$XDG_CONFIG_HOME/powerdevilrc" --group "$profile" --group RunScript --key IdleTimeoutCommand)" ]]
done
echo 'PASS uninstall and fresh PowerDevil startup produce no ScreenBot launch during the next 65 seconds'
