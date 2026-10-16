# Private desktop media QA

Run from the repository root on a Plasma 6 development machine:

```sh
bash tests/test_media_desktop.sh .omo/evidence/issue-25/desktop-qa/new-attempt
```

Requires the normal KCM build dependencies, Python/PyQt6 QtDBus/QtTest,
KWin Wayland, Xwayland, kcmshell6, libX11 and libXtst. Each invocation requires
a fresh output directory. The installer builds and installs into that directory's
`home`; no system installation or active desktop input is used.

The launcher unsets inherited display endpoints, creates a private XDG runtime,
HOME/config/data/cache, and a private D-Bus with service activation disabled.
The system-bus variable also points at this private bus. KWin uses a virtual
1440×1000 display and supplies its private Xwayland DISPLAY to the driver.
XTest permission and Screenshot2 permission bypass apply only to this disposable
compositor. The private runtime is removed on exit; installed files/config are
retained as evidence. Never run the child driver directly on a real desktop.

`drive.py` opens the installed Screensaver and Colors modules in the real KDE
KCM shell. `actions.json` sends XTest pointer/Tab/Shift-Tab/Space events; it does
not call module load/save or force focus on a QML control. The desktop is captured
through private KWin Screenshot2 after a 750 ms settling delay. Each step saves
PNG, raw capture metadata, window titles and an INI receipt. Assertions verify
pending values remain unsaved, Apply persists, navigating produces the shell's
Apply Settings dialog, Discard preserves the applied value, and applying off
persists false. Two settled off-switch crops must be pixel-identical.

The recorded coordinates target the default English native shell on this fixed
virtual display. The first pointer event warms up private Xwayland's EIS input
connection. Unexpected shell geometry or translations should fail the assertions;
inspect the step capture before adapting the action fixture.

`variants.py` opens the installed production Saver on the private Wayland display,
feeds synthetic metadata without starting a reader, and captures its widget.
Both 100% and 200% runs cover every clock position, no clock, reduced-motion hide,
and a partially faded track replaced with a playing track through the old hide
deadline. At 200%, logical sizes are reduced to fit the same physical display;
PNGs and receipt device-pixel ratios retain their actual physical resolution.
`receipts.json` records each frame's state and opacity. This supplements the
separate mocked D-Bus/session tests; it does not claim live-player interoperability.

The screenshot matrix includes the existing narrow-clock text clipping limitation.
Card collision regression tests assert bounds and exclusion from Bob's motion
envelope, clock, captions and exit hint across a 250-case viewport/position grid.
When no clear slot exists, the supplemental media card is hidden. Motion captures
use the no-clock layout so the card is visible at both scales.
