# ScreenBot Screensaver

ScreenBot is a KDE Plasma 6 screensaver for Wayland. It shows an animated Bob with themed backgrounds, optional animated weather, and fictional BobOS adventures. V10 through V18 are available downloads; V1 through V9 are currently unavailable.

## Downloads

| Version | Download |
| --- | --- |
| V1 | Unavailable |
| V2 | Unavailable |
| V3 | Unavailable |
| V4 | Unavailable |
| V5 | Unavailable |
| V6 | Unavailable |
| V7 | Unavailable |
| V8 | Unavailable |
| V9 | Unavailable |
| V10 | [Download ScreenBot Screensaver V10 (.zip)](https://github.com/Chenboda01/Screensaver/raw/refs/heads/main/releases/ScreenBot-Screensaver-V10.zip) |
| V11 | [Download ScreenBot Screensaver V11 (.zip)](https://github.com/Chenboda01/Screensaver/raw/refs/heads/main/releases/ScreenBot-Screensaver-V11.zip) |
| V12 | [Download ScreenBot Screensaver V12 (.zip)](https://github.com/Chenboda01/Screensaver/raw/refs/heads/main/releases/ScreenBot-Screensaver-V12.zip) |
| V13 | [Download ScreenBot Screensaver V13 (.zip)](https://github.com/Chenboda01/Screensaver/raw/refs/heads/main/releases/ScreenBot-Screensaver-V13.zip) |
| V14 | [Download ScreenBot Screensaver V14 (.zip)](https://github.com/Chenboda01/Screensaver/raw/refs/heads/main/releases/ScreenBot-Screensaver-V14.zip) |
| V15 | [Download ScreenBot Screensaver V15 (.zip)](https://github.com/Chenboda01/Screensaver/raw/refs/heads/main/releases/ScreenBot-Screensaver-V15.zip) |
| V16 | [Download ScreenBot Screensaver V16 (.zip)](https://github.com/Chenboda01/Screensaver/raw/refs/heads/main/releases/ScreenBot-Screensaver-V16.zip) |
| V17 | [Download ScreenBot Screensaver V17 (.zip)](https://github.com/Chenboda01/Screensaver/raw/refs/heads/main/releases/ScreenBot-Screensaver-V17.zip) |
| V18 | [Download ScreenBot Screensaver V18 (.zip)](https://github.com/Chenboda01/Screensaver/raw/refs/heads/main/releases/ScreenBot-Screensaver-V18.zip) |

## Install V10, V11, V12, V13, V14, V15, V16, V17, or V18

1. Download the version ZIP and extract it into `~/Downloads`.
2. Open a terminal in the extracted version folder, such as `ScreenBot-Screensaver-V18`.
3. Run:

   ```bash
   bash install.sh
   ```

The installer builds the KDE Settings module and installs it to your user account without requiring `sudo`. Log out and back in once so Plasma can discover the module. Then open **System Settings → Screensaver**, choose a theme, and select **Apply**.

The installer copies the screensaver to `~/ScreenBot/screensaver` and preserves a backup of an existing installation. The existing Plasma idle trigger can invoke `~/ScreenBot/screensaver/start.sh`. Use **System Settings → Screensaver** to configure the clock and toggle each animated weather effect.

## Features

- Random, Space, Mountains, Snow, Forest, and Futuristic City themes
- Configurable 12/24-hour clock, date, nine screen positions, font size, and visibility
- Individually enabled animated rain, snow, thunderstorms, fog, and Space shooting stars
- AI agent detection with a Remember my choice prompt, persistent automatic-launch policies, and a reset option in KDE Settings
- Manual launches remain available regardless of the automatic agent policy
- Optional AI Backpack and BobOS 1.0 adventures, with a 1–30 minute screensaver-relative delay and a fictional Wi-Fi boot animation
- Animated head-only Bob; he stays still during his sleepy phase
- Optional KDE password-lock request with a 1–60 minute delay
- Optional countdown with a smooth green-to-red color transition

## Version changes

- **V10:** Added Bob's still sleeping pose and password-free user-local KDE installation; includes the themed backgrounds and configurable countdown.
- **V11:** Added a **Yes/No** notification before the screensaver starts when a terminal AI agent is detected. Yes starts the saver and leaves the agent running; No cancels that launch.
- **V12:** Fixed idle-agent false prompts. Agent UI CPU polling no longer counts as work; the notification appears when a recognized terminal agent has an active or recently started child process.
- **V13:** Added three shaded planets, including a ringed planet, to the Space theme.
- **V14:** Restored prompts during agent response processing while filtering idle terminal UI polling. Active child commands continue to trigger the prompt.
- **V15:** Checks recent Codex and OpenCode turn status so the prompt appears during an active response, even between child commands.
- **V16:** Adds clock format, date, position, size, and visibility controls, plus individually configurable animated weather effects.
- **V17:** Adds a remember-choice checkbox to the active-agent prompt, persistent Always ask / Always start / Don't start preferences in KDE Settings, a reset action, safe cancellation when detection is uncertain or the prompt times out, and a manual launch bypass.
- **V18:** Adds separate AI Backpack and BobOS switches, a 1–30 minute first-adventure delay, an optional fictional Wi-Fi sequence, and occasional follow-up adventures after a cooldown of at least five minutes. BobOS is drawn entirely inside the screensaver, and KDE's configured password lock takes priority.

## Requirements

- KDE Plasma 6 on Wayland
- Python with PyQt6
- PyQt6 for the screensaver and agent-choice dialog
- CMake, a C++ compiler, Make, and the Qt/KDE development packages required by the KCM build

## Security

A Python screensaver is not a secure lock screen. KDE Screen Locking controls whether a password is required and may lock earlier for other reasons. Keep independent KDE locking enabled where appropriate.
