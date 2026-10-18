#!/usr/bin/env bash
# Bootstrap only inside a disposable Arch container.
set -euo pipefail
[[ "$EUID" == 0 ]] || { echo 'FAIL requires a disposable root container.' >&2; exit 2; }
mkdir -p evidence
exec > >(tee evidence/bootstrap.log) 2>&1
# Keep the whole distribution coherent, before Plasma 6.8 requires udmabuf,
# which hosted Azure kernels do not provide. Update this snapshot deliberately.
printf '%s\n' 'Server = https://archive.archlinux.org/repos/2026/10/01/$repo/os/$arch' > /etc/pacman.d/mirrorlist
pacman -Syyuu --noconfirm --needed base-devel git cmake extra-cmake-modules \
 qt6-declarative qt6-tools kcmutils kcoreaddons ki18n kconfig \
 kwin powerdevil dbus mesa python python-pyqt6 python-pip python-gobject util-linux libcap gdb
python -m venv --system-site-packages /opt/plasma-test
/opt/plasma-test/bin/pip install python-dbusmock==0.38.1
# Arch's scheduling capability is outside Docker's default bounding set.
getcap "$(command -v kwin_wayland)"
setcap -r "$(command -v kwin_wayland)"
test -z "$(getcap "$(command -v kwin_wayland)")"
useradd --create-home ci
chown -R ci:ci /src
runuser -u ci -- env QT_QPA_PLATFORM=offscreen kwin_wayland --version
pacman -Q kwin powerdevil qt6-tools python python-pyqt6 mesa > evidence/packages.txt
# Keep native crash backtraces in session.log without masking the child exit status.
cat > /usr/local/bin/kwin_wayland <<'WRAPPER'
#!/usr/bin/env bash
exec gdb --batch --return-child-result -ex run -ex 'thread apply all bt' --args /usr/bin/kwin_wayland "$@"
WRAPPER
chmod +x /usr/local/bin/kwin_wayland
result=0
runuser -u ci -- bash -o pipefail -c 'bash tests/test_installer.sh evidence/installer 2>&1 | tee evidence/installer.log' || result=1
runuser -u ci -- bash -o pipefail -c 'bash tests/test_python_runtime.sh evidence/python-runtime 2>&1 | tee evidence/python-runtime.log' || result=1
runuser -u ci -- env SCREENBOT_PYTHON=/opt/plasma-test/bin/python SCREENBOT_IDLE_MAX_SECONDS=90 \
 bash -o pipefail -c 'bash tests/test_idle_trigger_wayland.sh evidence/idle-wayland 2>&1 | tee evidence/idle-wayland.log' || result=1
exit "$result"
