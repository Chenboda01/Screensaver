import os
from pathlib import Path
import subprocess
import sys
import time


def test_standalone_install_and_platform_selection(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    home = tmp_path / 'home with spaces'
    home.mkdir()
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / '.config'),
               XDG_STATE_HOME=str(home / '.state'))
    for key in ('SCREENBOT_PYTHON', 'QT_QPA_PLATFORM', 'DISPLAY', 'WAYLAND_DISPLAY', 'XDG_SESSION_TYPE'):
        env.pop(key, None)
    # A failing build tool proves standalone installation never invokes CMake.
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    cmake = bin_dir / 'cmake'
    cmake.write_text('#!/bin/sh\nexit 99\n')
    cmake.chmod(0o755)
    env['PATH'] = str(bin_dir) + os.pathsep + env['PATH']
    result = subprocess.run(['bash', str(root / 'install.sh'), '--standalone'],
                            env=env, capture_output=True, text=True, check=True)
    assert 'Standalone runtime installed' in result.stdout
    installed = home / 'ScreenBot/screensaver'
    assert (installed / 'install-mode').read_text().strip() == 'standalone'
    assert not (home / '.config/plasma-workspace').exists()
    assert not (home / 'ScreenBot/install_manifest.txt').exists()
    assert (installed / 'screenbot/app.py').is_file()
    check = subprocess.run(['bash', str(installed / 'start.sh'), '--check'],
                           env=env, capture_output=True, text=True)
    assert check.returncode == 1
    assert 'Installation: standalone' in check.stdout
    assert 'No running xidlehook/xss-lock' in check.stdout
    assert 'PowerDevil' not in check.stdout
    ready = tmp_path / 'hook-ready'
    with subprocess.Popen([sys.executable, '-c',
                           'import ctypes,pathlib,sys,time; '
                           'ctypes.CDLL(None).prctl(15,b"xidlehook",0,0,0); '
                           'pathlib.Path(sys.argv[1]).touch(); time.sleep(15)',
                           str(ready), str(installed / 'start.sh')]) as hook:
        try:
            for _ in range(100):
                if ready.exists():
                    break
                time.sleep(.02)
            assert ready.exists()
            active = subprocess.run(['bash', str(installed / 'start.sh'), '--check'],
                                    env=env, capture_output=True, text=True, check=True)
            assert 'Idle mechanism: xidlehook running' in active.stdout
        finally:
            hook.terminate()
            hook.wait(timeout=5)
    # Substitute only the animation boundary, preserving actual Python selection
    # and the installed launch script; no visible windows or agent prompts.
    (installed / 'screensaver.py').write_text('import os\nprint(os.environ["QT_QPA_PLATFORM"])\n')
    cases = [({'XDG_SESSION_TYPE': 'x11', 'WAYLAND_DISPLAY': 'wayland-1'}, 'xcb'),
             ({'DISPLAY': ':42'}, 'xcb'),
             ({'DISPLAY': ':42', 'WAYLAND_DISPLAY': 'wayland-1'}, 'wayland'),
             ({'XDG_SESSION_TYPE': 'wayland', 'WAYLAND_DISPLAY': 'wayland-1'}, 'wayland'),
             ({}, 'wayland'),
             ({'XDG_SESSION_TYPE': 'x11', 'QT_QPA_PLATFORM': 'offscreen'}, 'offscreen')]
    for overrides, expected in cases:
        launch = subprocess.run(['bash', str(installed / 'start.sh'), '--manual'],
                                env=env | overrides, capture_output=True, text=True, check=True)
        assert launch.stdout.strip() == expected
    invalid = subprocess.run(['bash', str(root / 'install.sh'), '--standalone', '--idle-minutes', '5'],
                             env=env, capture_output=True, text=True)
    assert invalid.returncode == 2
    assert 'requires Plasma' in invalid.stderr
    missing_python = subprocess.run(['bash', str(root / 'install.sh'), '--standalone'],
                                    env=env | {'SCREENBOT_PYTHON': '/missing-python'},
                                    capture_output=True, text=True)
    assert missing_python.returncode != 0
    assert 'unavailable' in missing_python.stderr
    no_qt = bin_dir / 'python-without-qt'
    no_qt.write_text('#!/bin/sh\n[ "$2" != "import PyQt6" ]\n')
    no_qt.chmod(0o755)
    missing_qt = subprocess.run(['bash', str(root / 'install.sh'), '--standalone'],
                                env=env | {'SCREENBOT_PYTHON': str(no_qt)},
                                capture_output=True, text=True)
    assert missing_qt.returncode != 0
    assert 'PyQt6 is missing' in missing_qt.stderr
    subprocess.run(['bash', str(installed / 'uninstall.sh'), '--yes'],
                   env=env, capture_output=True, text=True, check=True)
    assert not installed.exists()
