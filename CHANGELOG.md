# Changelog

## V24

V24 introduces illustrated appearance presets and a simpler first-run settings page while preserving all existing V23 preferences. It also restores reliable cross-machine visual CI and adds guarded tag-based release automation.

### Added
- Added Calm, Fun, Live Sky, Photo frame, and Battery saver presets with keyboard-accessible cards. Presets stage appearance changes, preserve lock/security/personal settings, and show Custom after manual edits.
- Added Simple and Advanced settings views. New installations open in Simple; existing configurations remain unchanged and open in Advanced. A translated settings search is available in both views and jumps to matching Advanced sections.
- Added KDE Defaults support for staged settings while keeping Reset/Discard and Preview behavior.
- Stabilized visual regression tests with bundled test-only fonts, a bounded raster tolerance, exact same-process burn-in checks, and CI diagnostic image artifacts.
- Pinned the CI Qt/PyQt versions, made V-tag publication require successful CI, and enabled strict required checks on main.
- Published as a versioned ZIP release with installation instructions.

## V23

V23 adds source-backed, theme-aware facts and optional scene-matched ambient audio, alongside the recent photo, seasonal, media-card, and BobOS improvements.

### Added
- Added an opt-in My photos theme with staged folder, recursion, interval, ordering, and fit settings; asynchronous local photo discovery/decoding, EXIF orientation, bounded cache, slow pan/zoom, cross-fades, and a friendly fallback.
- Fixed photo-folder selection in KDE Settings, kept fit-whole photos fully visible, smoothed the blurred backdrop, and moved the empty-folder notice above Bob.
- Capped photo discovery at 5,000 retained images and 1,024 folders; placed empty-folder notices below the top clock and preview banner, and constrained photo settings to the available KCM width.
- Added optional local-date seasonal decorations for New Year, Lunar New Year, Valentine's Day, hemisphere-aware Spring, Halloween, winter holidays, and personal birthdays. Event options and birthday month/day/name follow KDE Apply/Discard; only generic New Year is enabled by default, and birthday details stay in the local settings file.
- Added vector decorations across themes, including New Year countdown/fireworks, Lunar New Year lanterns, spring petals, Halloween bats/pumpkins and Bob's witch hat, winter lights/snow and Bob's Santa hat, and birthday balloons/confetti. Reduced motion keeps decorative animation static and softer; Space gets no seasonal snow or shooting-star effects.
- Added a lock-free `--preview --force-date YYYY-MM-DD[THH:MM[:SS]]` calendar preview. Forced dates are rejected in normal screensaver launches; KDE's real password lock remains authoritative.
- Added an offline, source-noted "Did you know?" card with 30 kid-friendly facts per scene category, theme/weather/full-Moon matching, original Bob quotes, no-repeat cycles, smooth fades, complete adaptive text layout, localized headings, and Spanish translations. Corrected Edison patent dates and linked claims to the patent records. KDE settings control visibility, a 2–5 minute interval, and Facts/Quotes/Both; the card avoids Bob, the clock, BobOS, captions, and other overlays while following burn-in shifts.
- Added optional scene-matched ambient audio, off by default, with a staged 0–100% volume control, Live Sky matching mode, quiet hours, a gentle fade-in, immediate shutdown, and automatic muting while MPRIS reports active playback (including titleless media while Now Playing is enabled). Live Sky rain intensity scales within the configured volume; a rain-and-rumble cue follows the shared visible-lightning event on the existing single stream, and Forest nights add occasional synthesized owl calls over crickets. Missing or broken assets are cached until their file fingerprints change, QtMultimedia remains optional, and the installed audio bundle includes provenance and license files.
- Added an opt-in primary-screen Now playing card with background MPRIS metadata updates, pause fade-out, safe title shortening, and a translated KDE Clock setting that respects Apply/Discard. Media stays hidden in previews and when the session bus is unavailable.
- Added Bob Camera with a bounded, in-memory selfie of the current theme and Live Sky, plus Bob Pet with animated snack and play scenes. Both apps respect Reduce motion and flashes. Camera photos appear in fictional Bob Files; neither app accesses devices, personal files, or external services.
- BobOS now selects 4–6 apps per adventure without repeating the same selection consecutively. Seeded schedules keep timing reproducible, the complete preview includes every app, and an adventure starts only if its full selected duration fits before KDE locks.
- Added selectable Aurora, Ocean / Beach, Desert, and Underwater adventures, available individually or through Random.
- Added Live Sky-aware Aurora visibility, underwater surface ripples for rain and snow, and Bob's scene-matched diving helmet.
- Split the screensaver and agent prompt runtimes into small entrypoints and focused settings, theme, weather, clock, BobOS, and terminal detection modules. Added exact offscreen image baselines to protect the five themes and BobOS home screen during future changes.
- Added an optional primary-screen AI agent status badge with elapsed work time and confirmed completion time. Status polling runs in a background thread, uncertain states stay hidden, and Bob celebrates once after a confirmed finish without displaying agent content.
- Added Off, Standard, and Strong OLED burn-in protection. Standard slowly shifts the scene and clock; Strong fades to black over 30–60 minutes, with input closing the screensaver.
- Suppressed rain, snow, thunderstorms, fog, and shooting-star overlays in the Space theme; manual weather and shooting-star settings remain available on landscape themes.
- Added optional Live Sky reactions for Bob: a smoothly animated umbrella, sunglasses, wool hat, scarf, fog and lightning expressions, wind tilt, moon glances, and a longer deep-night sleepy expression. Added a staged KDE toggle and deterministic weather preview overrides.
- Added staged Customize Bob settings for a display name, six color presets or a custom color picker, and seven optional accessories. Appearance choices persist through Apply/Discard; weather layers keep user headwear visible when their geometry overlaps.

## V22

- Added opt-in Live Sky mode with local time-of-day and lunar rendering, optional weather-aware animations, KDE settings, asynchronous weather updates, and an offline cache.
- Added all 896 country/city choices from `countries_and_cities.txt` to KDE Settings; the selected place is resolved and weather is fetched through Open-Meteo without IP-based location lookup.
- Added automated astronomy, weather mapping, network/cache, and offscreen rendering coverage. Existing manual weather effects remain available when Live Sky is off.
- Published as a ZIP release with an installation guide and release notes.

## V21

- Removed the relationship storyline, its character and message content, story-specific animation phases, and its KDE Settings option.
- Kept BobOS 2.0 running through the standard phone adventure, with fictional BobChat, Maps, Weather, Calendar, App Store, and game screens.
- Preserved the phone preview, staged KDE Apply/Discard behavior for remaining settings, and the real KDE password-lock priority.
- Updated offscreen tests to cover the full BobOS sequence and animated rendering for the retained phone apps.

## V20

- Expanded BobOS 2.0 with additional fictional phone apps and longer animated interactions. V21 retains the ordinary BobChat, Maps, Weather, Calendar, and App Store simulations.

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

## V16

- Adds clock format, date, position, size, and visibility controls, plus individually configurable animated weather effects.

## V15

- Checks recent Codex and OpenCode turn status so the prompt appears during an active response, even between child commands.

## V14

- Restored prompts during agent response processing while filtering idle terminal UI polling. Active child commands continue to trigger the prompt.

## V13

- Added three shaded planets, including a ringed planet, to the Space theme.

## V12

- Fixed idle-agent false prompts. Agent UI CPU polling no longer counts as work; the notification appears when a recognized terminal agent has an active or recently started child process.

## V11

- Added a **Yes/No** notification before the screensaver starts when a terminal AI agent is detected. Yes starts the saver and leaves the agent running; No cancels that launch.

## V10

- Added Bob's still sleeping pose and password-free user-local KDE installation; includes the themed backgrounds and configurable countdown.
