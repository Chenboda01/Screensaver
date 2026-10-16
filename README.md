<div align="center">
  <img src="assets/screenbot-icon.svg" width="128" height="128" alt="ScreenBot floating robot head icon">
  <h1>ScreenBot Screensaver</h1>
  <p>A little robot, a lot of worlds. A playful screensaver for KDE Plasma 6 on Wayland.</p>
  <p>
    <a href="https://github.com/Chenboda01/Screensaver/releases/tag/V21"><img alt="Latest release V21" src="https://img.shields.io/badge/release-V21-168eb7"></a>
    <a href="https://github.com/Chenboda01/Screensaver/releases"><img alt="Downloads" src="https://img.shields.io/badge/downloads-V10%E2%80%93V19%20%2B%20V21-263b52"></a>
    <a href="#platform-support-and-installation"><img alt="Platform" src="https://img.shields.io/badge/platform-KDE%20Plasma%206%20%7C%20Wayland-512bd4"></a>
    <a href="LICENSE"><img alt="License MIT" src="https://img.shields.io/badge/license-MIT-4c9a70"></a>
  </p>
</div>

---

ScreenBot shows head-only animated Bob exploring themed backgrounds, optional weather, and fictional BobOS phone adventures. V10 through V19 and V21 are listed for download; V1 through V9 are unavailable.

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
| V19 | [Download ScreenBot Screensaver V19 (.zip)](https://github.com/Chenboda01/Screensaver/raw/refs/heads/main/releases/ScreenBot-Screensaver-V19.zip) |
| V21 | [Download ScreenBot Screensaver V21 (.zip)](https://github.com/Chenboda01/Screensaver/releases/download/V21/ScreenBot-Screensaver-V21.zip) |

## Platform support and installation

The full screensaver and KDE System Settings module are supported on **Linux with KDE Plasma 6 and a Wayland session**. The installer builds a KDE settings component and uses Linux-specific Plasma, Wayland, and user-install paths.

### CachyOS and other Linux distributions with KDE Plasma 6 on Wayland

1. Confirm that KDE Plasma 6 is installed and you are using its Wayland session.
2. Install your distribution's packages for Python 3 with PyQt6, CMake 3.20 or newer, a C++17 compiler, Make, ECM 6+, Qt 6.5+ (Core, Quick, and QML), and KDE Frameworks 6+ (KCMUtils, CoreAddons, and I18n). Package names vary by distribution.
3. Download the [V21 ZIP release](https://github.com/Chenboda01/Screensaver/releases/download/V21/ScreenBot-Screensaver-V21.zip) (or another available version) and extract it, for example, into `~/Downloads`.
4. Open a terminal in the extracted `ScreenBot-Screensaver-V21` folder and run:

   ```bash
   bash install.sh
   ```

5. Log out and back in so Plasma discovers the user-local settings module.
6. Open **System Settings → Screensaver**, select a theme and options, then choose **Apply**.
7. Configure Plasma's idle/screensaver trigger to run `~/ScreenBot/screensaver/start.sh` if it is not already configured.

The installer builds the KDE Settings module and installs it to your user account without `sudo`. It copies the screensaver to `~/ScreenBot/screensaver` and preserves a backup of an existing installation.

### Windows and macOS

The full ScreenBot screensaver is not currently supported on Windows or macOS. There is no native installation guide for those systems: `install.sh` requires Linux, KDE Plasma 6, and Wayland, and the settings module integrates with KDE System Settings. Running the Python animation by itself would not install the screensaver or its KDE settings.

### Other operating systems

There are no tested or supported installers for BSD or other non-Linux systems. On another Linux distribution, use the steps above only if it provides KDE Plasma 6 on Wayland and the listed Qt/KDE development dependencies.

## Features

- Random, Space, Mountains, Snow, Forest, and Futuristic City themes
- Configurable 12/24-hour clock, date, nine screen positions, font size, and visibility
- Individually enabled animated rain, snow, thunderstorms, fog, and Space shooting stars
- AI agent detection with a Remember my choice prompt, persistent automatic-launch policies, and a reset option in KDE Settings
- Manual launches remain available regardless of the automatic agent policy
- Bob's Phone and animated BobOS 2.0 with a fictional home screen, browser, files, terminal, games, settings, notifications, BobChat, Maps, Weather, Calendar, App Store, AI Wi-Fi, and an immediate preview
- Configurable BobOS delay of 1–30 minutes from the first visible screensaver frame, plus a cooldown of at least five minutes
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
- **V19:** Replaces the backpack and tiny laptop with Bob's Phone. BobOS now zooms into an animated fictional mobile interface and autonomously visits Bob Browser, Bob Files, Bob Terminal, Bob Games, and Bob Settings before shutting down and returning to the selected theme. Adds a lock-safe full-sequence preview in KDE Settings.
- **V20:** Introduced BobOS 2.0 with an expanded set of fictional phone apps and a longer sequence of animated phone interactions.
- **V21:** Removes the relationship storyline and its KDE setting. BobOS continues its normal phone adventure, including BobChat, Maps, Weather, Calendar, App Store, and games; the preview and lock-safe shutdown behavior remain available.

## Requirements

- KDE Plasma 6 on Wayland
- Python with PyQt6
- PyQt6 for the screensaver and agent-choice dialog
- CMake, a C++ compiler, Make, and the Qt/KDE development packages required by the KCM build

## Security

A Python screensaver is not a secure lock screen. KDE Screen Locking controls whether a password is required and may lock earlier for other reasons. Keep independent KDE locking enabled where appropriate.
