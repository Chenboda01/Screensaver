# Changelog

## V20

- Upgraded BobOS to 2.0 with an optional, recurring relationship story about Bob and his girlfriend of two years, Luna.
- Added fictional BobChat messages, Bob Maps destination browsing, Bob Weather, Bob Calendar scheduling, dating advice, an incoming call, a theme-specific floating robot date scene, and follow-up messages.
- Added an enabled-by-default "Enable Bob's Relationship Story" KDE setting with Apply/Discard persistence; disabling it removes every relationship scene while preserving other BobOS adventures.
- Extended the lock-safe preview to include the full story and added timeline, setting, five-theme render, and offscreen sequence tests. All relationship content is painted fiction and never uses real contacts, messaging, maps, or weather services.

## V19

- Replaced the AI Backpack and tiny laptop with Bob's Phone while keeping Bob head-only.
- Rebuilt BobOS as a scripted, animated phone experience with home, Browser, Files, Terminal, Games, Settings, notification, boot, shutdown, and camera-zoom phases. All content is painted locally; it never opens apps, files, websites, or commands.
- Renamed the KDE control to Enable Bob's Phone and added a lock-safe Preview full adventure button. Preview skips the activation delay but still yields to the configured KDE password lock.
- Added automated timeline and offscreen rendering checks for the complete preview sequence, lock priority, theme return, and app interactions.

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
