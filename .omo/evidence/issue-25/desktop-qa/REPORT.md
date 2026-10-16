# Issue 25 — private desktop QA completion

Worktree: `/home/boda/Downloads/Screensaver/.omo/teams/team-c16bce69/worktrees/Z`.
Integrated main (including #11 and #22) via merge `106a20f` before these changes.

## Reproduced finding and fix

The earlier `verified-2/variants-200/clock-bottom-right-700.png` showed Bob
covering the title/icon. A first placement-only attempt (`final/`) moved the
card away from Bob but exposed caption/hint overlap at top-clock positions.
Neither directory is acceptance evidence. The final placement reserves Bob's
full motion envelope, the clock's text rectangle, captions and exit hint.
It first keeps the normal anchor, then tries clear corners. When no full-size
slot fits, only the supplemental media card is hidden. Bob and existing clock,
caption and hint rendering are unchanged. README documents this constrained
layout behavior. No playback or privacy behavior changes.

## Invocations

```sh
bash tests/test_media_desktop.sh .omo/evidence/issue-25/desktop-qa/verified-final
QT_QPA_PLATFORM=offscreen .omo/evidence/issue-25/venv/bin/python -m pytest \
 tests/test_mpris.py tests/test_mpris_dbus.py tests/test_now_playing.py \
 tests/test_now_playing_session.py tests/test_preview.py tests/test_agent_status.py \
 tests/test_multimonitor.py tests/test_render_goldens.py -q \
 --basetemp=.omo/evidence/issue-25/desktop-qa/focused-final \
 --junitxml=.omo/evidence/issue-25/desktop-qa/focused-final.xml
bash kcm/tests/check-translations.sh .omo/evidence/issue-25/desktop-qa/kcm
```

All artifact references below are relative to this report. `manifest.json`
records sizes and SHA-256 for the acceptance screenshots, logs and receipts.

| Scenario | Binary observable | Artifact |
|---|---|---|
| Real keyboard traversal | OS XTest Tab×5 from expanded Clock reaches media switch; Space changes pending value; Shift-Tab returns to position combo, Tab returns to media | `verified-final/actions.json`, `focus-1.png` through `focus-5.png`, `reverse-focus.png`, `return-focus.png`, `media-on-pending.png` (all within `verified-final/`) |
| Settled disabled switch | 750 ms delay before each capture; two switch crops compare pixel-identical; false persisted | `verified-final/off-applied.png`, `off-settled-repeat.png`, matching `.ini`, `shell-receipts.json` |
| Shell Apply | Before Apply config absent; after clicking actual shell Apply, now_playing_enabled=true | `verified-final/media-on-pending.ini`, `media-applied.ini`, matching PNGs |
| Shell navigation/Discard | Changing to off then navigating to Colors opens real Apply Settings modal; Discard navigates, returning shows enabled and saved true | `verified-final/navigate-unsaved.png`, `discarded-to-colors.png`, `returned-after-discard.png`, matching `.ini` and `-windows.json` |
| Installed native desktop | Installer succeeds under private HOME; actual installed KCM loaded by kcmshell6 | `verified-final/install.log`, `session.log`, `shell-receipts.json` |
| Layout variants | 9 clock positions plus no clock at two sizes per scale, recorded physical dimensions/DPR/card bounds; constrained layouts hide only card | `verified-final/variants-100/`, `verified-final/variants-200/`, each `receipts.json` |
| Reduced motion | Visible card at opacity 1 before grace ends, hidden at opacity 0 after deadline | Both variant directories: `reduced-motion-before-hide.png`, `reduced-motion-hidden.png` |
| Interrupted fade | Partial opacity, resumed title at opacity 1, remains 1 after old hide deadline | Both variant directories: `interrupt-before-resume.png`, `interrupt-resumed.png`, `interrupt-after-old-deadline.png` |
| Regression grid and related behavior | 369 tests pass, including 250 grid combinations over 5 widths × 5 heights × 9 positions/no clock; no overlap with reserved areas and bounded or empty card | `focused-final.log`, `focused-final.xml`, `focused-final/test_scaled_card*/layout.txt` |
| KCM/locales and artifact separation | EN/ES/fallback × light/dark installed checks pass; 4/4 other CTests pass; zz-dark receipt remains true/forest, independent ctest receipt false/random | `kcm-run.log`, `kcm/ctest.log`, `kcm/zz-dark/applied-settings.ini`, `kcm/ctest-evidence/applied-settings.ini` |

## Isolation and scope

`tests/test_media_desktop.sh` is the exact launcher. It installs into
`verified-final/home`, sets private HOME/XDG_CONFIG_HOME/cache/data/runtime, unsets
inherited display endpoints, and creates a private D-Bus with no activation
directories. Even DBUS_SYSTEM_BUS_ADDRESS points at this private bus. A virtual
KWin creates its own Xwayland DISPLAY. XTest authorization and Screenshot2
permission bypass exist only inside this compositor; no active desktop is driven.
KCM captures are full composed desktop screenshots from its Screenshot2 API.
Saver captures use visible installed production widgets on private Wayland.

The scripted shell is the real KDE KCM shell with Screensaver + Colors modules;
there is no call to module load/save and no forced QML control focus. Coordinates
are a fixture for the fixed native English shell. Unexpected changes fail persisted
setting assertions. Synthetic metadata drives render variants; the separate focused
suite covers mock MPRIS D-Bus track/pause/unavailable-bus behavior.

Pre-existing narrow-clock clipping and Bob crossing a center clock remain visible
in captures and are not claimed fixed. Card geometry avoids both; large scale can
hide the card where no clear full-size slot remains. Earlier discovery/failed runs
are retained for provenance but excluded from the acceptance manifest.

## Recorded outcome

PASS: real Tab/Shift-Tab/Space traversal, settled off state, actual shell
Apply/Discard/navigation, rendered reduced motion/interrupted fade, and clock
position/no-clock/200% variants. The 200% top-left/top-center/top-right at 390×422
and top-center at 700×460 deliberately hide media; all 100% matrix cards fit.
The 50 variant frames plus 19 shell captures are enumerated in the manifest.
The final gate remains the independent reviewer's decision. No issue was closed.
