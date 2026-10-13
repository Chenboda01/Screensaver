# ScreenBot Screensaver

ScreenBot is a KDE Plasma 6 screensaver for Wayland. It shows an animated Bob with a clock and themed animated backgrounds. V10 and V11 are available downloads; V1 through V9 are currently unavailable.

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

## Install V10 or V11

1. Download the version ZIP and extract it into `~/Downloads`.
2. Open a terminal in the extracted version folder, such as `ScreenBot-Screensaver-V11`.
3. Run:

   ```bash
   bash install.sh
   ```

The installer builds the KDE Settings module and installs it to your user account without requiring `sudo`. Log out and back in once so Plasma can discover the module. Then open **System Settings → Screensaver**, choose a theme, and select **Apply**.

The installer copies the screensaver to `~/ScreenBot/screensaver` and preserves a backup of an existing installation. The existing Plasma idle trigger can invoke `~/ScreenBot/screensaver/start.sh`.

## Features

- Random, Space, Mountains, Snow, Forest, and Futuristic City themes
- Animated head-only Bob; he stays still during his sleepy phase
- Optional KDE password-lock request with a 1–60 minute delay
- Optional countdown with a smooth green-to-red color transition
- V11 asks whether a terminal AI agent should continue in the background before the screensaver starts. **Yes** starts the saver and leaves the agent running; **No** cancels that saver launch.

## Requirements

- KDE Plasma 6 on Wayland
- Python with PyQt6
- `notify-send` (libnotify) for the V11 agent prompt
- CMake, a C++ compiler, Make, and the Qt/KDE development packages required by the KCM build

## Security

A Python screensaver is not a secure lock screen. KDE Screen Locking controls whether a password is required and may lock earlier for other reasons. Keep independent KDE locking enabled where appropriate.
