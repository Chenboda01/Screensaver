# Native Plasma idle integration test

Run on Linux with Plasma 6's `kwin_wayland`, PowerDevil, `dbus-run-session`,
Qt/KDE build dependencies, and Python 3 with PyQt6/QtTest:

```sh
bash tests/test_idle_trigger_wayland.sh .omo/evidence/idle-native-run
```

Use a fresh evidence directory each time. Set `SCREENBOT_POWERDEVIL` if the daemon
is not installed at `/usr/lib/org_kde_powerdevil`; `SCREENBOT_PYTHON` follows the
normal interpreter-selection rules. Allow about three minutes including build.

The test performs a real user-prefix installation in a private HOME, starts a
software-rendered virtual KWin and the real PowerDevil daemon, and uses the
installed idle helper to select a one-minute delay. It asserts that the actual
Wayland idle event launches the installed automatic `start.sh` path and renders a
full-screen ScreenBot frame. The original agent guard remains in the path; the
sandbox preference allows detected agents to keep working. An uncertain agent
detection still cancels the launch and fails the test, as it does in production.

Two small test observers record launcher entry and the renderer's first frame,
then send Escape through the existing input handler. Neither observer dispatches
the idle event or changes the launch decision. Timing, the frame, native daemon
logs, and installed-file lifecycle logs are captured under the evidence directory.
The test then uninstalls, restarts only its private PowerDevil, and checks that no
ScreenBot launch occurs during another 65 seconds.

Both D-Bus endpoints point to the private bus, whose configuration contains no
service activation directories. The virtual desktop has its own short runtime
path and disables its locker. The test neither edits the real user's power/lock
configuration nor signals their KWin, PowerDevil, applications, or agents.
`password_lock=false` is scoped to the test HOME. The active desktop and its
password-lock settings remain independent.

This is an optional compositor integration test, not an offscreen unit test.
Failure to initialize the private desktop, missing actual idle dispatch, missing
rendered frame, timing outside 55–75 seconds, or a post-uninstall launch all return
nonzero. Do not count unsupported compositor environments as passing.
