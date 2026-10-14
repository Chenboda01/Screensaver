# Changelog

## V18

- Added separate AI Backpack and BobOS switches, both enabled by default; disabling the backpack disables BobOS controls without changing the saved BobOS choice.
- Added an activation delay from 1 to 30 minutes, measured from the screensaver's first visible frame, plus an optional fictional Wi-Fi connection animation.
- Added fictional BobOS adventures with a close-and-pack sequence and follow-up timing that waits at least five minutes after each adventure.
- Kept all BobOS visuals inside the screensaver and suppressed them once the configured KDE password-lock deadline is reached.

## V17

- Added a remembered-choice checkbox to the active-agent Yes/No dialog.
- Added persistent Always ask, Always start screensaver, and Don't start screensaver while agents are running settings, plus a reset action.
- Made uncertain detection and prompt timeouts cancel automatic launches safely; manual launches bypass the agent prompt.
- Kept the prompt choice separate from KDE's staged settings so the Settings module's Apply and Discard behavior remains intact.
