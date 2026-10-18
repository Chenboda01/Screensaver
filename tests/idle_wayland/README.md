# Native Plasma idle integration test

Run on Linux with Plasma 6's `kwin_wayland`, PowerDevil, `dbus-run-session`,
Qt/KDE build dependencies, and Python 3 with PyQt6/QtTest, PyGObject, and
python-dbusmock 0.38.1. Run as a normal user:

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

The `plasma-e2e` job in `.github/workflows/ci.yml` runs the installer lifecycle,
Python runtime selection, and this real compositor test on every PR and main
push. Releases reuse the same CI workflow and cannot publish if this job fails;
`require-main-ci.sh` additionally requires green main CI for the tagged commit.
Repository administrators should require the check named
`Install → idle trigger → uninstall (KDE Plasma 6)` in branch protection.

Run the same Arch environment locally from a repository checkout (Docker required):

```sh
docker run --rm -it -v "$PWD":/source:ro archlinux:latest bash
pacman -Syu --noconfirm --needed base-devel git cmake extra-cmake-modules \
  qt6-declarative qt6-tools kcmutils kcoreaddons ki18n kconfig \
  kwin powerdevil dbus mesa python python-pyqt6 python-pip python-gobject util-linux libcap
python -m venv --system-site-packages /opt/plasma-test
/opt/plasma-test/bin/pip install python-dbusmock==0.38.1
# Inside this disposable container only: allow unprivileged virtual KWin execution.
setcap -r "$(command -v kwin_wayland)"
useradd --create-home ci
cp -a /source /home/ci/src
chown -R ci:ci /home/ci/src
su ci
cd /home/ci/src
bash tests/test_installer.sh evidence/installer
bash tests/test_python_runtime.sh evidence/python-runtime
SCREENBOT_PYTHON=/opt/plasma-test/bin/python SCREENBOT_IDLE_MAX_SECONDS=90 \
  bash tests/test_idle_trigger_wayland.sh evidence/idle-wayland
```

Arch packages KWin with `cap_sys_nice=ep`. Docker's default capability bounding
set excludes it, which makes execution fail with `Operation not permitted`.
CI removes that file capability inside the disposable container and verifies
KWin executes as the normal test user. Software-rendered virtual KWin needs no
realtime scheduling privilege. Do not apply this container setup to your host.

Copy `evidence/` out of the container before exiting if needed. Do not copy a
checkout with existing build directories; CMake caches contain absolute paths.
CI uploads `plasma-e2e-evidence` even after failure, including stage output,
package versions, install/uninstall logs, mock service logs, PowerDevil logs,
`timing.json`, and `idle-started-screenbot.png` when rendering succeeds. Failed
runs may lack later artifacts; the stage logs identify where execution stopped.

UPower (on AC) and logind are mocked on the private bus only. PowerDevil, KWin,
the idle event, installer, launcher, and renderer remain real. Missing mocks or
an unavailable AC profile fail explicitly. `SCREENBOT_IDLE_MAX_SECONDS` raises
only the upper timing bound (75 by default, 90 in CI, maximum 120); the 55-second
lower bound remains fixed. This allows shared-runner scheduling delays without
accepting early launches. The entire private session also has a hard timeout.

This is a required compositor integration test in CI.
Failure to initialize the private desktop, missing actual idle dispatch, missing
rendered frame, timing outside the configured window, or a post-uninstall launch all return
nonzero. Do not count unsupported compositor environments as passing.
